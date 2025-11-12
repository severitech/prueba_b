"""
Procesador de comandos de voz/texto con IA para generación de reportes en SmartSales365.
Soporta: Datos sintéticos + PostgreSQL (Railway) + SQLite3 (Local).
Enfoque en FILTROS de PRODUCTOS (q, categoría, subcategoría, stock, estado, orden, límite).
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd
from django.utils import timezone
from django.conf import settings
from django.db import models  # ← NECESARIO para Q y F

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Imports de modelos (coherentes con tu esquema)
# ---------------------------------------------------------
MODELOS_DISPONIBLES = False
ProductoModel = None
SubcategoriaModel = None

try:
    from tienda.models import (
        Venta,
        Categoria,
        SubCategoria as SubcategoriaModel,
        Productos as ProductoModel,
        DetalleVenta,
    )
    MODELOS_DISPONIBLES = True
except Exception as exc:
    logger.warning("Modelos no disponibles en IA Processor: %s", exc)
    MODELOS_DISPONIBLES = False


# ---------------------------------------------------------
# Utilidades
# ---------------------------------------------------------
def _ensure_aware(dt: datetime) -> datetime:
    if dt is None:
        return dt
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def _to_date(s: str) -> Optional[datetime]:
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return _ensure_aware(dt)
    except Exception:
        return None


def _normalize_cols(df: Optional[pd.DataFrame], tipo: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    ren = {'monto': 'total', 'estado_venta': 'estado', 'name': 'descripcion'}
    df = df.rename(columns=ren)

    columnas_minimas = {
        'ventas': ['id', 'fecha', 'total', 'estado'],
        'productos': ['id', 'descripcion', 'precio', 'stock', 'estado', 'categoria_nombre', 'subcategoria_nombre'],
        'clientes': ['id', 'nombre', 'email', 'created_at'],
        'inventario': ['id', 'descripcion', 'stock', 'precio', 'estado', 'categoria_nombre', 'subcategoria_nombre'],
    }.get(tipo, list(df.columns))

    for c in columnas_minimas:
        if c not in df.columns:
            df[c] = None
    return df[columnas_minimas]


# ---------------------------------------------------------
# Procesador
# ---------------------------------------------------------
class SmartSalesIAProcessor:
    """
    Procesa comandos para generar reportes usando IA (opcional) o lógica local.
    Enfocado a e-commerce de electrodomésticos. Soporta filtros de productos reales.
    """

    def __init__(self, usar_datos_reales: bool = True):
        self.usar_datos_reales = usar_datos_reales and MODELOS_DISPONIBLES
        self.datos_sinteticos = False
        self.client = None
        self.ia_disponible = False

        # Cargar sintéticos
        self._cargar_datos_sinteticos()

        # OpenAI opcional
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                self.ia_disponible = True
                logger.info("OpenAI configurado")
            except Exception as exc:
                logger.warning("OpenAI no disponible: %s", exc)

        logger.info("IA Processor - Reales: %s | Sintéticos: %s", self.usar_datos_reales, self.datos_sinteticos)

    # -------------------- SINTÉTICOS --------------------
    def _cargar_datos_sinteticos(self) -> None:
        base_dir = "scikit_learn_ia/datasets"
        try:
            if os.path.exists(base_dir):
                self.df_usuarios = pd.read_csv(f"{base_dir}/usuarios.csv")
                self.df_productos = pd.read_csv(f"{base_dir}/productos.csv")
                self.df_ventas = pd.read_csv(f"{base_dir}/ventas.csv")
                self.df_detalles = pd.read_csv(f"{base_dir}/detalles_venta.csv")
                if 'fecha' in self.df_ventas.columns:
                    self.df_ventas['fecha'] = pd.to_datetime(self.df_ventas['fecha'])

                # Normalizar nombres esperados en productos sintéticos
                for col in ['categoria_nombre', 'subcategoria_nombre', 'descripcion', 'precio', 'stock', 'estado']:
                    if col not in self.df_productos.columns:
                        self.df_productos[col] = None

                self.datos_sinteticos = True
            else:
                self.datos_sinteticos = False
        except Exception as exc:
            logger.error("Error cargando sintéticos: %s", exc)
            self.datos_sinteticos = False

    # -------------------- DATOS REALES --------------------
    def _resolver_categoria_subcategoria(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Acepta en filtros: 'categoria_id', 'subcategoria_id', 'categoria_nombre', 'subcategoria_nombre'
        o 'categoria'/'subcategoria' (texto libre). Devuelve IDs si hay coincidencias.
        """
        if not MODELOS_DISPONIBLES:
            return filtros

        categoria_text = filtros.get('categoria') or filtros.get('categoria_nombre')
        subcat_text = filtros.get('subcategoria') or filtros.get('subcategoria_nombre')

        if categoria_text and 'categoria_id' not in filtros:
            cat = Categoria.objects.filter(descripcion__icontains=str(categoria_text).strip()).first()
            if cat:
                filtros['categoria_id'] = cat.id
                filtros['categoria_nombre'] = cat.descripcion

        if subcat_text and 'subcategoria_id' not in filtros:
            subc = SubcategoriaModel.objects.select_related('categoria') \
                .filter(descripcion__icontains=str(subcat_text).strip())
            if filtros.get('categoria_id'):
                subc = subc.filter(categoria_id=filtros['categoria_id'])
            sub = subc.first()
            if sub:
                filtros['subcategoria_id'] = sub.id
                filtros['subcategoria_nombre'] = sub.descripcion
                if 'categoria_id' not in filtros:
                    filtros['categoria_id'] = sub.categoria_id
                    filtros['categoria_nombre'] = sub.categoria.descripcion
        return filtros

    def _aplicar_filtros_productos_queryset(self, qs, filtros: Dict[str, Any]):
        """
        Filtros reales para Productos:
        q (texto), estado, categoria_id, subcategoria_id, stock_min/max, ordenar, limite
        """
        # Estado por defecto: Activo (si no se especifica)
        estado = filtros.get('estado_producto') or filtros.get('estado') or 'Activo'
        if estado:
            qs = qs.filter(estado=estado)

        # Texto libre (q) sobre descripción y nombres de cat/subcat
        qtext = (filtros.get('q') or '').strip()
        if qtext:
            qs = qs.filter(
                models.Q(descripcion__icontains=qtext) |
                models.Q(subcategoria__descripcion__icontains=qtext) |
                models.Q(subcategoria__categoria__descripcion__icontains=qtext)
            )

        # Categoría y subcategoría
        if filtros.get('categoria_id'):
            qs = qs.filter(subcategoria__categoria_id=filtros['categoria_id'])
        if filtros.get('subcategoria_id'):
            qs = qs.filter(subcategoria_id=filtros['subcategoria_id'])

        # Stock
        if filtros.get('stock_minimo') is not None:
            qs = qs.filter(stock__gte=int(filtros['stock_minimo']))
        if filtros.get('stock_maximo') is not None:
            qs = qs.filter(stock__lte=int(filtros['stock_maximo']))

        # Orden
        ordenar = filtros.get('ordenar')  # 'precio_asc', 'precio_desc', 'stock_desc', etc.
        if ordenar == 'precio_asc':
            qs = qs.order_by('precio')
        elif ordenar == 'precio_desc':
            qs = qs.order_by('-precio')
        elif ordenar == 'stock_asc':
            qs = qs.order_by('stock')
        elif ordenar == 'stock_desc':
            qs = qs.order_by('-stock')
        else:
            qs = qs.order_by('descripcion')

        # Límite
        limite = filtros.get('limite')
        if isinstance(limite, int) and limite > 0:
            qs = qs[:limite]

        return qs

    def _obtener_productos_reales(self, filtros: Dict[str, Any]) -> pd.DataFrame:
        if not (self.usar_datos_reales and MODELOS_DISPONIBLES and ProductoModel):
            return pd.DataFrame()

        try:
            filtros = self._resolver_categoria_subcategoria(filtros)
            qs = ProductoModel.objects.select_related('subcategoria', 'subcategoria__categoria')
            qs = self._aplicar_filtros_productos_queryset(qs, filtros)
            datos = list(qs.values(
                'id', 'descripcion', 'precio', 'stock', 'estado',
                categoria_nombre=models.F('subcategoria__categoria__descripcion'),
                subcategoria_nombre=models.F('subcategoria__descripcion'),
            ))
            return _normalize_cols(pd.DataFrame(datos), 'productos')
        except Exception as exc:
            logger.error("Error obteniendo productos reales: %s", exc)
            return pd.DataFrame()

    def _obtener_ventas_reales(self, filtros: Dict[str, Any]) -> pd.DataFrame:
        if not (self.usar_datos_reales and MODELOS_DISPONIBLES):
            return pd.DataFrame()
        try:
            qs = Venta.objects.all()

            fi = filtros.get('fecha_inicio')
            ff = filtros.get('fecha_fin')
            if isinstance(fi, str):
                fi = _to_date(fi)
            if isinstance(ff, str):
                ff = _to_date(ff)
            if fi:
                qs = qs.filter(fecha__gte=fi)
            if ff:
                if isinstance(ff, datetime):
                    ff = ff.replace(hour=23, minute=59, second=59, microsecond=999999)
                qs = qs.filter(fecha__lte=ff)
            if filtros.get('estado'):
                qs = qs.filter(estado=filtros['estado'])

            limite = filtros.get('limite')
            if isinstance(limite, int) and limite > 0:
                qs = qs[:limite]

            datos = list(qs.values('id', 'fecha', 'total', 'estado'))
            df = pd.DataFrame(datos)
            if not df.empty and 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'])
            return _normalize_cols(df, 'ventas')
        except Exception as exc:
            logger.error("Error obteniendo ventas reales: %s", exc)
            return pd.DataFrame()

    def _obtener_datos_reales(self, filtros: Dict[str, Any], tipo: str) -> Optional[pd.DataFrame]:
        if tipo == 'ventas':
            return self._obtener_ventas_reales(filtros)
        if tipo in ('productos', 'inventario'):
            return self._obtener_productos_reales(filtros)
        return None

    # -------------------- SINTÉTICOS (filtros) --------------------
    def _filtrar_productos_sinteticos(self, filtros: Dict[str, Any]) -> pd.DataFrame:
        if not self.datos_sinteticos:
            return pd.DataFrame()
        df = self.df_productos.copy()

        qtext = (filtros.get('q') or '').strip().lower()
        if qtext:
            df = df[
                df['descripcion'].str.lower().str.contains(qtext, na=False) |
                df['categoria_nombre'].str.lower().str.contains(qtext, na=False) |
                df['subcategoria_nombre'].str.lower().str.contains(qtext, na=False)
            ]

        estado = filtros.get('estado_producto') or filtros.get('estado') or 'Activo'
        if estado:
            df = df[df['estado'].fillna('').str.lower() == estado.lower()]

        if filtros.get('categoria_nombre'):
            cn = filtros['categoria_nombre'].lower()
            df = df[df['categoria_nombre'].str.lower().str.contains(cn, na=False)]
        if filtros.get('subcategoria_nombre'):
            sn = filtros['subcategoria_nombre'].lower()
            df = df[df['subcategoria_nombre'].str.lower().str.contains(sn, na=False)]

        if filtros.get('stock_minimo') is not None:
            df = df[df['stock'] >= int(filtros['stock_minimo'])]
        if filtros.get('stock_maximo') is not None:
            df = df[df['stock'] <= int(filtros['stock_maximo'])]

        ordenar = filtros.get('ordenar')
        if ordenar == 'precio_asc':
            df = df.sort_values('precio', ascending=True)
        elif ordenar == 'precio_desc':
            df = df.sort_values('precio', ascending=False)
        elif ordenar == 'stock_asc':
            df = df.sort_values('stock', ascending=True)
        elif ordenar == 'stock_desc':
            df = df.sort_values('stock', ascending=False)
        else:
            df = df.sort_values('descripcion', ascending=True)

        limite = filtros.get('limite')
        if isinstance(limite, int) and limite > 0:
            df = df.head(limite)

        return _normalize_cols(df, 'productos')

    def _obtener_datos_sinteticos(self, filtros: Dict[str, Any], tipo: str) -> Optional[pd.DataFrame]:
        if not self.datos_sinteticos:
            return None
        try:
            if tipo == 'ventas':
                df = self.df_ventas.copy()
                if filtros.get('fecha_inicio'):
                    fi = pd.to_datetime(filtros['fecha_inicio'])
                    df = df[df['fecha'] >= fi]
                if filtros.get('fecha_fin'):
                    ff = pd.to_datetime(filtros['fecha_fin'])
                    df = df[df['fecha'] <= ff]
                if filtros.get('estado'):
                    df = df[df['estado'] == filtros['estado']]
                limite = filtros.get('limite')
                if isinstance(limite, int) and limite > 0:
                    df = df.head(limite)
                return _normalize_cols(df, 'ventas')

            if tipo in ('productos', 'inventario'):
                return self._filtrar_productos_sinteticos(filtros)
        except Exception as exc:
            logger.error("Error en sintéticos: %s", exc)
        return None

    # -------------------- COMBINACIÓN --------------------
    def _obtener_datos_combinados(self, filtros: Dict[str, Any], tipo: str) -> pd.DataFrame:
        reales = self._obtener_datos_reales(filtros, tipo) if self.usar_datos_reales else None
        sintet = self._obtener_datos_sinteticos(filtros, tipo) if self.datos_sinteticos else None
        if reales is not None and sintet is not None:
            return pd.concat([_normalize_cols(reales, tipo), _normalize_cols(sintet, tipo)], ignore_index=True)
        if reales is not None:
            return _normalize_cols(reales, tipo)
        if sintet is not None:
            return _normalize_cols(sintet, tipo)
        return pd.DataFrame()

    # -------------------- API PÚBLICA --------------------
    def generar_reporte(self, comando: Dict[str, Any]) -> Dict[str, Any]:
        """
        comando={'tipo_reporte': 'productos'|'ventas'|..., 'filtros': {...}}
        Filtros de productos: q, categoria/subcategoria (id/nombre), estado, stock, ordenar, limite.
        """
        tipo = comando.get('tipo_reporte') or 'ventas'
        filtros = (comando.get('filtros') or {}).copy()

        datos = self._obtener_datos_combinados(filtros, tipo)
        if datos.empty:
            return {'success': False, 'error': 'No hay datos con los filtros indicados', 'total': 0}

        # KPIs básicos
        if tipo in ('productos', 'inventario'):
            kpis = {
                'total_productos': len(datos),
                'stock_total': int(datos['stock'].fillna(0).sum()),
                'valor_inventario': float((datos['precio'].fillna(0) * datos['stock'].fillna(0)).sum()),
                'activos': int((datos['estado'].fillna('') == 'Activo').sum()),
            }
        elif tipo == 'ventas':
            kpis = {
                'cantidad_ventas': len(datos),
                'total_ventas': float(datos['total'].fillna(0).sum()),
                'promedio_venta': float(datos['total'].fillna(0).mean() or 0),
            }
        else:
            kpis = {'total': len(datos)}

        return {'success': True, 'total': len(datos), 'kpis': kpis, 'datos': datos}
