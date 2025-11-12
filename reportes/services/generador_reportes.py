# services/generador_reportes.py
import logging
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import re

from .ia_processor import SmartSalesIAProcessor
from .interpretador_comandos import InterpretadorComandosVoz

logger = logging.getLogger(__name__)


class GeneradorReportes:
    """
    Fachada de reportes. Orquesta:
    - Interpretación de comandos (voz/texto) -> filtros estructurados
    - Obtención de datos combinados (reales + sintéticos) con SmartSalesIAProcessor
    - KPIs por tipo de reporte
    """

    def __init__(self, usar_datos_reales: bool = True):
        # Mantener compatibilidad con tu status view:
        self.procesador_ia = SmartSalesIAProcessor(usar_datos_reales=usar_datos_reales)
        self._interpretador = InterpretadorComandosVoz()

    # ----------------------- Utilidades -----------------------
    @staticmethod
    def _num(series, default=0.0):
        """Convierte una Serie a numérico de forma segura (evita Decimal + float)."""
        try:
            return pd.to_numeric(series, errors='coerce').fillna(default)
        except Exception:
            return pd.Series([], dtype=float)

    @staticmethod
    def _sanitize_numeric(df: Optional[pd.DataFrame], tipo: str) -> Optional[pd.DataFrame]:
        """
        Normaliza tipos numéricos para evitar mezclas Decimal/float entre BD y CSV.
        - ventas: total -> float
        - productos/inventario: precio -> float, stock -> int
        - fecha -> datetime
        """
        if df is None or df.empty:
            return df
        df = df.copy()

        if tipo == "ventas":
            if "total" in df.columns:
                df["total"] = pd.to_numeric(df["total"], errors="coerce").astype(float)

        if tipo in ("productos", "inventario"):
            if "precio" in df.columns:
                df["precio"] = pd.to_numeric(df["precio"], errors="coerce").astype(float)
            if "stock" in df.columns:
                df["stock"] = pd.to_numeric(df["stock"], errors="coerce").fillna(0).astype(int)

        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

        return df

    # --------- Inferencia/rescate de montos desde el texto del comando ---------
    @staticmethod
    def _to_number(txt: str) -> Optional[float]:
        if not txt:
            return None
        # tolerar puntos/comas/espacios de miles
        clean = txt.replace('\xa0', ' ')
        clean = re.sub(r'\s+', '', clean)
        clean = clean.replace('.', '').replace(',', '')
        try:
            return float(clean)
        except Exception:
            return None

    @staticmethod
    def _parse_montos_desde_texto(comando: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Extrae (monto_minimo, monto_maximo, razon) desde el texto.
        Soporta: 'mayor a/que', 'más de/mas de', '>=', '>', 'desde',
                 'menor a/que', 'menos de', '<=', '<', 'hasta'.
        Si no encuentra comparadores pero ve un número con 'bolivianos' o 'bs',
        decide min/max según palabras ('menor/menos/hasta' => max; 'mayor/mas' => min).
        """
        t = (comando or "").lower()
        # normalizar espacios y NBSP
        t = t.replace('\u00a0', ' ')
        t = re.sub(r'\s+', ' ', t).strip()

        # Flags de intención
        has_menor = re.search(r'(?:\bmenor(?:es)?\b|\bmenos\b|<=|<|\bhasta\b)', t, re.IGNORECASE) is not None
        has_mayor = re.search(r'(?:\bmayor(?:es)?\b|>=|>|\bm[aá]s\s+de\b|\bmas\s+de\b|superior(?:es)?\s+a)', t, re.IGNORECASE) is not None

        # 1) Con comparadores (mínimo)
        for p in [
            r'(?:mayor(?:es)?\s+(?:a|que)|m[aá]s\s+de|mas\s+de|superior(?:es)?\s+a|>=|>\s*)(\d[\d\.,\s]*)',
            r'(?:desde)\s+(\d[\d\.,\s]*)',
        ]:
            m = re.search(p, t, re.IGNORECASE)
            if m:
                n = GeneradorReportes._to_number(m.group(1))
                if n is not None:
                    return n, None, "comparador_min"

        # 2) Con comparadores (máximo)
        for p in [
            r'(?:menor(?:es)?\s+(?:a|que)|menos\s+de|inferior(?:es)?\s+a|<=|<\s*)(\d[\d\.,\s]*)',
            r'(?:hasta)\s+(\d[\d\.,\s]*)',
        ]:
            m = re.search(p, t, re.IGNORECASE)
            if m:
                n = GeneradorReportes._to_number(m.group(1))
                if n is not None:
                    return None, n, "comparador_max"

        # 3) Fallback con moneda: número + bolivianos/bs
        mnum_mon = re.search(r'(\d[\d\.,\s]*)\s*(?:bolivianos?|bs|bss|bob)\b', t, re.IGNORECASE)
        if mnum_mon:
            n = GeneradorReportes._to_number(mnum_mon.group(1))
            if n is not None:
                if has_menor and not has_mayor:
                    return None, n, "fallback_moneda_max"
                if has_mayor and not has_menor:
                    return n, None, "fallback_moneda_min"
                # sin pistas claras: asumir mínimo por compatibilidad histórica
                return n, None, "fallback_moneda_min_default"

        # 4) Súper fallback: si hay “menor/menos” y un número suelto
        if has_menor:
            msolo = re.search(r'(\d[\d\.,\s]*)', t)
            if msolo:
                n = GeneradorReportes._to_number(msolo.group(1))
                if n is not None:
                    return None, n, "fallback_menor_numero"

        # 5) Súper fallback: si hay “mayor/más de” y un número suelto
        if has_mayor:
            msolo = re.search(r'(\d[\d\.,\s]*)', t)
            if msolo:
                n = GeneradorReportes._to_number(msolo.group(1))
                if n is not None:
                    return n, None, "fallback_mayor_numero"

        return None, None, None

    @staticmethod
    def _inferir_montos_por_texto(comando: str, filtros: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Inyecta en 'filtros' los montos detectados si no existen.
        Devuelve (filtros, meta_inferencia).
        """
        min_txt, max_txt, razon = GeneradorReportes._parse_montos_desde_texto(comando)
        meta = {"monto_min_inferido": min_txt, "monto_max_inferido": max_txt, "razon_inferencia": razon}

        # Sólo setear si no vienen desde el interpretador
        if filtros.get("monto_minimo") is None and min_txt is not None:
            filtros["monto_minimo"] = min_txt
        if filtros.get("monto_maximo") is None and max_txt is not None:
            filtros["monto_maximo"] = max_txt
        return filtros, meta

    @staticmethod
    def _aplicar_filtros_en_memoria(df: Optional[pd.DataFrame], filtros: Dict[str, Any], tipo: str) -> Optional[pd.DataFrame]:
        """
        Refuerzo de filtros en memoria:
        - ventas: monto_minimo / monto_maximo
        - productos/inventario: stock_minimo / stock_maximo, estado_producto, búsqueda 'q', orden y limite
        """
        if df is None or df.empty:
            return df

        df = df.copy()

        if tipo == "ventas":
            s_total = pd.to_numeric(df.get("total", []), errors="coerce")
            mask = pd.Series(True, index=df.index)

            mmin = filtros.get("monto_minimo")
            mmax = filtros.get("monto_maximo")

            if mmin is not None:
                try:
                    mmin = float(mmin)
                    mask &= (s_total >= mmin)
                except Exception:
                    pass

            if mmax is not None:
                try:
                    mmax = float(mmax)
                    mask &= (s_total <= mmax)
                except Exception:
                    pass

            df = df[mask]

        elif tipo in ("productos", "inventario"):
            # Stock
            if filtros.get("stock_minimo") is not None and "stock" in df.columns:
                try:
                    df = df[pd.to_numeric(df["stock"], errors="coerce").fillna(0) >= int(filtros["stock_minimo"])]
                except Exception:
                    pass
            if filtros.get("stock_maximo") is not None and "stock" in df.columns:
                try:
                    df = df[pd.to_numeric(df["stock"], errors="coerce").fillna(0) <= int(filtros["stock_maximo"])]
                except Exception:
                    pass

            # Estado producto
            if filtros.get("estado_producto") and "estado" in df.columns:
                df = df[df["estado"].fillna("").str.lower() == str(filtros["estado_producto"]).lower()]

            # Búsqueda por texto
            q = filtros.get("q")
            if q:
                qlow = str(q).strip().lower()
                posibles = [c for c in df.columns if c in ("descripcion", "nombre", "categoria", "subcategoria")]
                if posibles:
                    m = pd.Series(False, index=df.index)
                    for c in posibles:
                        m = m | df[c].astype(str).str.lower().str.contains(qlow, na=False)
                    df = df[m]

            # Orden
            ordenar = filtros.get("ordenar")
            if ordenar == "precio_asc" and "precio" in df.columns:
                df = df.sort_values("precio", ascending=True)
            elif ordenar == "precio_desc" and "precio" in df.columns:
                df = df.sort_values("precio", ascending=False)
            elif ordenar == "stock_asc" and "stock" in df.columns:
                df = df.sort_values("stock", ascending=True)
            elif ordenar == "stock_desc" and "stock" in df.columns:
                df = df.sort_values("stock", ascending=False)

            # Límite
            if filtros.get("limite"):
                try:
                    df = df.head(int(filtros["limite"]))
                except Exception:
                    pass

        return df

    @staticmethod
    def _kpis_ventas(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        if df is None or df.empty:
            return {"cantidad_ventas": 0, "total_ventas": 0.0, "promedio_venta": 0.0}
        s_total = GeneradorReportes._num(df.get("total", []), 0.0)
        return {
            "cantidad_ventas": int(len(df)),
            "total_ventas": float(s_total.sum()),
            "promedio_venta": float(s_total.mean() if len(s_total) else 0.0),
        }

    @staticmethod
    def _kpis_productos(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        if df is None or df.empty:
            return {"total_productos": 0, "stock_total": 0, "valor_inventario": 0.0, "activos": 0}
        stock = GeneradorReportes._num(df.get("stock", []), 0).astype(int) if "stock" in df.columns else pd.Series([], dtype=int)
        precio = GeneradorReportes._num(df.get("precio", []), 0.0)
        valor_inv = float((precio * stock).sum()) if len(precio) and len(stock) else 0.0
        activos = int((df.get("estado", pd.Series(dtype=object)).fillna("") == "Activo").sum()) if "estado" in df.columns else 0
        return {
            "total_productos": int(len(df)),
            "stock_total": int(stock.sum()) if len(stock) else 0,
            "valor_inventario": valor_inv,
            "activos": activos
        }

    # ----------------------- API primaria -----------------------
    def reporte_por_comando(self, comando: str, usar_ia: bool = False, usar_datos_reales: bool = True) -> Dict[str, Any]:
        """
        Flujo principal para /api/reportes/voz/:
        1) Interpretar el comando -> filtros (tipo_reporte incluido)
        2) Inferir montos desde el texto (por si el interpretador no los trae)
        3) Obtener datos en el processor (reales + sintéticos)
        4) Normalizar y aplicar filtros en memoria (refuerzo)
        5) Devolver KPIs + datos (capado a 500 filas)
        """
        # Instanciar processor con el flag por si viene diferente desde la view
        self.procesador_ia = SmartSalesIAProcessor(usar_datos_reales=usar_datos_reales)

        # 1) Interpretar
        filtros = self._interpretador.interpretar(comando)

        # 2) Inferir montos desde texto (no depende del interpretador)
        filtros, meta_inf = self._inferir_montos_por_texto(comando, filtros)

        tipo = filtros.get("tipo_reporte") or "ventas"

        # 3) Datos combinados
        df = self.procesador_ia._obtener_datos_combinados(filtros, tipo)

        # 4) Normalizar + filtrar en memoria
        df = self._sanitize_numeric(df, tipo)
        pre_count = 0 if df is None else len(df)

        # Si la inferencia detectó montos, refuérzalos en filtros (por si el interpretador no lo hizo)
        if tipo == "ventas":
            if meta_inf.get("monto_min_inferido") is not None and "monto_minimo" not in filtros:
                filtros["monto_minimo"] = meta_inf["monto_min_inferido"]
            if meta_inf.get("monto_max_inferido") is not None and "monto_maximo" not in filtros:
                filtros["monto_maximo"] = meta_inf["monto_max_inferido"]

        df = self._aplicar_filtros_en_memoria(df, filtros, tipo)
        post_count = 0 if df is None else len(df)

        logger.debug(f"[ReporteVoz] before/after: {pre_count} -> {post_count}; filtros={filtros}; meta={meta_inf}")

        if df is None or df.empty:
            return {
                "success": False,
                "tipo_reporte": tipo,
                "filtros": filtros,
                "total_registros": 0,
                "kpis": {},
                "datos": [],
                "metadata": {
                    "fuente_datos": "REAL + SINTÉTICOS"
                    if self.procesador_ia.usar_datos_reales and self.procesador_ia.datos_sinteticos
                    else "REAL" if self.procesador_ia.usar_datos_reales else "SINTÉTICOS",
                    "conteo_antes": pre_count,
                    "conteo_despues": post_count,
                    **meta_inf
                }
            }

        # 5) KPIs + datos
        if tipo in ("productos", "inventario"):
            kpis = self._kpis_productos(df)
        elif tipo == "ventas":
            kpis = self._kpis_ventas(df)
        else:
            kpis = {"total": int(len(df))}

        return {
            "success": True,
            "tipo_reporte": tipo,
            "filtros": filtros,
            "total_registros": int(len(df)),
            "kpis": kpis,
            "datos": df.to_dict(orient="records")[:500],
            "metadata": {
                "fuente_datos": "REAL + SINTÉTICOS"
                if self.procesador_ia.usar_datos_reales and self.procesador_ia.datos_sinteticos
                else "REAL" if self.procesador_ia.usar_datos_reales else "SINTÉTICOS",
                "conteo_antes": pre_count,
                "conteo_despues": post_count,
                **meta_inf
            }
        }

    # ----- Rutas GET/POST específicas ya usadas en tus views -----
    def reporte_ventas_general(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        filtros = (filtros or {}).copy()
        filtros["tipo_reporte"] = "ventas"

        df = self.procesador_ia._obtener_datos_combinados(filtros, "ventas")
        df = self._sanitize_numeric(df, "ventas")
        df = self._aplicar_filtros_en_memoria(df, filtros, "ventas")

        return {
            "tipo_reporte": "ventas",
            "total_registros": int(len(df)) if df is not None else 0,
            "kpis": self._kpis_ventas(df),
            "datos": df.to_dict(orient="records")[:500] if df is not None else []
        }

    def reporte_productos_rendimiento(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Soporta: q, categoria/subcategoria (nombre o id), estado_producto, stock_minimo/stock_maximo, ordenar, limite.
        """
        filtros = (filtros or {}).copy()
        filtros["tipo_reporte"] = "productos"

        df = self.procesador_ia._obtener_datos_combinados(filtros, "productos")
        df = self._sanitize_numeric(df, "productos")
        df = self._aplicar_filtros_en_memoria(df, filtros, "productos")

        return {
            "tipo_reporte": "productos",
            "total_registros": int(len(df)) if df is not None else 0,
            "kpis": self._kpis_productos(df),
            "datos": df.to_dict(orient="records")[:500] if df is not None else []
        }

    def reporte_clientes_detallado(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        # En este ejemplo, todavía no tenemos clientes reales/sintéticos en processor.
        # Puedes extender processor para clientes cuando lo necesites.
        return {
            "tipo_reporte": "clientes",
            "total_registros": 0,
            "kpis": {},
            "datos": []
        }

    def reporte_inventario_analitico(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Igual que productos, pero semánticamente inventario (reusa pipeline).
        """
        filtros = (filtros or {}).copy()
        filtros["tipo_reporte"] = "inventario"

        df = self.procesador_ia._obtener_datos_combinados(filtros, "inventario")
        df = self._sanitize_numeric(df, "inventario")
        df = self._aplicar_filtros_en_memoria(df, filtros, "inventario")

        return {
            "tipo_reporte": "inventario",
            "total_registros": int(len(df)) if df is not None else 0,
            "kpis": self._kpis_productos(df),
            "datos": df.to_dict(orient="records")[:500] if df is not None else []
        }
