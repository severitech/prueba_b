import pandas as pd
import numpy as np
from datetime import datetime
import os
import django
from django.db.models import Sum, Count, Avg

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tienda.models import Venta, DetalleVenta, Productos, Usuario, Categoria, SubCategoria

def cargar_datos_combinados(usar_reales=True, usar_sinteticos=True):
    """
    Carga datos combinados desde PostgreSQL (reales) y CSVs (sintéticos)
    """
    datos_combinados = []
    
    # 1. DATOS REALES desde PostgreSQL - CORREGIDO TIMEZONE
    if usar_reales:
        try:
            print("📊 Cargando datos reales desde PostgreSQL...")
            
            ventas_reales = Venta.objects.select_related(
                'usuario'
            ).prefetch_related(
                'detalles__producto__subcategoria__categoria'
            ).all()
            
            for venta in ventas_reales:
                for detalle in venta.detalles.all():
                    producto = detalle.producto
                    subcategoria = producto.subcategoria
                    categoria = subcategoria.categoria
                    
                    # ✅ CORRECCIÓN TIMEZONE: convertir fecha Django a naive
                    fecha_venta = venta.fecha
                    if fecha_venta and fecha_venta.tzinfo is not None:
                        fecha_venta = fecha_venta.replace(tzinfo=None)
                    
                    datos_combinados.append({
                        'fecha': fecha_venta,
                        'total_venta': float(venta.total),
                        'producto_id': producto.id,
                        'producto_descripcion': producto.descripcion,
                        'categoria': categoria.descripcion,
                        'subcategoria': subcategoria.descripcion,
                        'precio_unitario': float(producto.precio),
                        'cantidad': detalle.cantidad,
                        'subtotal': float(detalle.subtotal),
                        'usuario_id': venta.usuario.id,
                        'estado_venta': venta.estado,
                        'origen': 'real'
                    })
                    
            real_count = len([d for d in datos_combinados if d['origen'] == 'real'])
            print(f"✅ Cargadas {real_count} ventas reales desde PostgreSQL")
            
        except Exception as e:
            print(f"⚠️ Error cargando datos reales: {e}")
    
    # 2. DATOS SINTÉTICOS desde CSVs
    if usar_sinteticos:
        try:
            print("🤖 Cargando datos sintéticos desde CSVs...")
            ruta_base = "scikit_learn_ia/datasets/"
            
            # Cargar datasets sintéticos
            df_ventas = pd.read_csv(f"{ruta_base}ventas.csv", parse_dates=["fecha"])
            df_detalles = pd.read_csv(f"{ruta_base}detalles_venta.csv")
            df_productos = pd.read_csv(f"{ruta_base}productos.csv")
            
            # Combinar datos sintéticos
            df_sintetico = pd.merge(df_detalles, df_ventas, left_on='venta_id', right_on='id')
            df_sintetico = pd.merge(df_sintetico, df_productos, left_on='producto_id', right_on='id')
            
            for _, row in df_sintetico.iterrows():
                datos_combinados.append({
                    'fecha': row['fecha'],
                    'total_venta': float(row['total']),
                    'producto_id': row['producto_id'],
                    'producto_descripcion': row['descripcion'],
                    'categoria': row['categoria'],
                    'subcategoria': row['subcategoria'],
                    'precio_unitario': float(row['precio']),
                    'cantidad': row['cantidad'],
                    'subtotal': float(row['subtotal']),
                    'usuario_id': row['usuario_id'],
                    'estado_venta': row.get('estado', 'Pagado'),
                    'origen': 'sintetico'
                })
                
            sintetico_count = len([d for d in datos_combinados if d['origen'] == 'sintetico'])
            print(f"✅ Cargados {sintetico_count} registros sintéticos desde CSVs")
            
        except Exception as e:
            print(f"⚠️ Error cargando datos sintéticos: {e}")
    
    # Crear DataFrame combinado
    if not datos_combinados:
        raise ValueError("❌ No se pudieron cargar datos. Verifica tu configuración.")
    
    df_combinado = pd.DataFrame(datos_combinados)
    
    # ✅ NORMALIZAR FECHAS para evitar conflictos de timezone
    df_combinado = normalizar_fechas(df_combinado)
    
    # Estadísticas del dataset combinado
    real_total = len(df_combinado[df_combinado['origen'] == 'real'])
    sintetico_total = len(df_combinado[df_combinado['origen'] == 'sintetico'])
    
    print(f"\n📈 RESUMEN DATOS COMBINADOS:")
    print(f"   • Reales: {real_total} registros")
    print(f"   • Sintéticos: {sintetico_total} registros")
    print(f"   • Total: {len(df_combinado)} registros")
    
    # ✅ MANEJO SEGURO DE FECHAS
    try:
        fecha_min = df_combinado['fecha'].min()
        fecha_max = df_combinado['fecha'].max()
        print(f"   • Período: {fecha_min} a {fecha_max}")
    except Exception as e:
        print(f"   • Período: Error calculando fechas - {e}")
    
    return df_combinado

def cargar_datos():
    """
    Función compatible con tu código actual - usa datos combinados por defecto
    """
    return cargar_datos_combinados(usar_reales=True, usar_sinteticos=True)

def preparar_datos(df):
    """
    Preparar los datos para el entrenamiento del modelo (compatible con tu código actual)
    
    Args:
        df (pd.DataFrame): DataFrame de entrada
    
    Returns:
        tuple: (X, y) características y variable objetivo
    """
    # Asegurar que fecha es datetime
    df['fecha'] = pd.to_datetime(df['fecha'])
    
    # ✅ Características temporales (tu enfoque actual)
    df["dia_del_anio"] = df["fecha"].dt.dayofyear
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.dayofweek
    df["trimestre"] = df["fecha"].dt.quarter
    
    # ✅ Nuevas características enriquecidas
    df['es_fin_semana'] = df['dia_semana'].isin([5, 6]).astype(int)
    df['es_inicio_mes'] = (df['fecha'].dt.day <= 7).astype(int)
    df['es_fin_mes'] = (df['fecha'].dt.day > 23).astype(int)
    
    # Características de productos
    df['precio_categoria'] = pd.cut(df['precio_unitario'], 
                                   bins=[0, 100, 500, 1000, 5000], 
                                   labels=[0, 1, 2, 3])
    
    # Eliminar filas con nulos
    df = df.dropna(subset=["subtotal"])
    
    # ✅ VARIABLES PARA MODELO DE INGRESOS (total_venta)
    features_ingresos = [
        "dia_del_anio", "mes", "anio", "dia_semana", "trimestre",
        "es_fin_semana", "es_inicio_mes", "es_fin_mes",
        "precio_unitario", "cantidad", "precio_categoria"
    ]
    
    # Codificar variables categóricas para categorías
    if 'categoria' in df.columns:
        df = pd.get_dummies(df, columns=['categoria'], prefix='cat')
        cat_features = [col for col in df.columns if col.startswith('cat_')]
        features_ingresos.extend(cat_features)
    
    X = df[features_ingresos]
    y = df["total_venta"]  # Variable objetivo para modelo de ingresos
    
    print(f"🎯 Datos preparados para ML:")
    print(f"   • Muestras: {X.shape[0]}")
    print(f"   • Características: {X.shape[1]}")
    print(f"   • Características usadas: {features_ingresos}")
    
    return X, y

def preparar_datos_cantidades(df):
    """
    Preparar datos específicamente para el modelo de cantidades (train_model_cantidades.py)
    
    Returns:
        tuple: (X_cantidades, y_cantidades) para modelo de unidades vendidas
    """
    # Agrupar por mes y producto para obtener cantidades
    df_agrupado = df.groupby(['anio', 'mes', 'producto_id']).agg({
        'cantidad': 'sum',
        'precio_unitario': 'mean',
        'categoria': 'first',
        'subcategoria': 'first'
    }).reset_index()
    
    # Características para modelo de cantidades
    features_cantidades = ['anio', 'mes', 'precio_unitario']
    
    # Codificar categorías
    if 'categoria' in df_agrupado.columns:
        df_agrupado = pd.get_dummies(df_agrupado, columns=['categoria'], prefix='cat')
        cat_features = [col for col in df_agrupado.columns if col.startswith('cat_')]
        features_cantidades.extend(cat_features)
    
    X_cantidades = df_agrupado[features_cantidades]
    y_cantidades = df_agrupado['cantidad']
    
    print(f"📦 Datos preparados para modelo de cantidades:")
    print(f"   • Muestras: {X_cantidades.shape[0]}")
    print(f"   • Características: {X_cantidades.shape[1]}")
    
    return X_cantidades, y_cantidades

# Función de compatibilidad para tus scripts existentes
def cargar_datos_solo_sinteticos():
    """
    Versión que solo usa datos sintéticos (para compatibilidad con scripts antiguos)
    """
    return cargar_datos_combinados(usar_reales=False, usar_sinteticos=True)

# Agrega esta función en tu data_preprocessing.py
def normalizar_fechas(df):
    """
    Normaliza todas las fechas a timezone-naive para evitar conflictos
    """
    if 'fecha' in df.columns:
        # Convertir a datetime si no lo está
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Si hay timezone info, removerla
        if df['fecha'].dt.tz is not None:
            df['fecha'] = df['fecha'].dt.tz_localize(None)
    
    return df

def cargar_datos_combinados(usar_reales=True, usar_sinteticos=True):
    """
    Carga datos combinados desde PostgreSQL (reales) y CSVs (sintéticos)
    INCLUYE datos reales del 2025 si existen
    """
    datos_combinados = []
    
    # 1. DATOS SINTÉTICOS desde CSVs (2019-2024)
    if usar_sinteticos:
        try:
            print("🤖 Cargando datos sintéticos 2019-2024...")
            ruta_base = "scikit_learn_ia/datasets/"
            
            # Cargar datasets sintéticos
            df_ventas = pd.read_csv(f"{ruta_base}ventas.csv", parse_dates=["fecha"])
            df_detalles = pd.read_csv(f"{ruta_base}detalles_venta.csv")
            df_productos = pd.read_csv(f"{ruta_base}productos.csv")
            
            # Combinar datos sintéticos
            df_sintetico = pd.merge(df_detalles, df_ventas, left_on='venta_id', right_on='id')
            df_sintetico = pd.merge(df_sintetico, df_productos, left_on='producto_id', right_on='id')
            
            for _, row in df_sintetico.iterrows():
                # ✅ FILTRAR: Solo datos hasta 2024 (histórico)
                if row['fecha'].year <= 2024:
                    datos_combinados.append({
                        'fecha': row['fecha'],
                        'total_venta': float(row['total']),
                        'producto_id': row['producto_id'],
                        'producto_descripcion': row['descripcion'],
                        'categoria': row['categoria'],
                        'subcategoria': row['subcategoria'],
                        'precio_unitario': float(row['precio']),
                        'cantidad': row['cantidad'],
                        'subtotal': float(row['subtotal']),
                        'usuario_id': row['usuario_id'],
                        'estado_venta': row.get('estado', 'Pagado'),
                        'origen': 'sintetico_2019_2024'  # ✅ Especificar período
                    })
                
            sintetico_count = len([d for d in datos_combinados if 'sintetico' in d['origen']])
            print(f"✅ Cargados {sintetico_count} registros sintéticos 2019-2024")
            
        except Exception as e:
            print(f"⚠️ Error cargando datos sintéticos: {e}")
    
    # 2. DATOS REALES desde PostgreSQL (2025+)
    if usar_reales:
        try:
            print("📊 Cargando datos reales 2025...")
            from tienda.models import Venta, DetalleVenta, Productos
            
            # Obtener ventas reales del 2025 en adelante
            fecha_inicio_2025 = datetime(2025, 1, 1)
            fecha_hoy = datetime.now()  # Esto sería 22/10/2025
            
            ventas_reales = Venta.objects.filter(
                fecha__gte=fecha_inicio_2025  # Solo 2025 en adelante
            ).select_related('usuario').prefetch_related('detalles__producto__subcategoria__categoria')
            
            ventas_2025_count = 0
            for venta in ventas_reales:
                for detalle in venta.detalles.all():
                    producto = detalle.producto
                    subcategoria = producto.subcategoria
                    categoria = subcategoria.categoria
                    
                    # ✅ Normalizar fecha (remover timezone si existe)
                    fecha_venta = venta.fecha
                    if fecha_venta and fecha_venta.tzinfo is not None:
                        fecha_venta = fecha_venta.replace(tzinfo=None)
                    
                    datos_combinados.append({
                        'fecha': fecha_venta,
                        'total_venta': float(venta.total),
                        'producto_id': producto.id,
                        'producto_descripcion': producto.descripcion,
                        'categoria': categoria.descripcion,
                        'subcategoria': subcategoria.descripcion,
                        'precio_unitario': float(producto.precio),
                        'cantidad': detalle.cantidad,
                        'subtotal': float(detalle.subtotal),
                        'usuario_id': venta.usuario.id,
                        'estado_venta': venta.estado,
                        'origen': 'real_2025',  # ✅ Especificar que es dato real 2025
                        'es_dato_reciente': True  # ✅ Marcar como dato actual
                    })
                    ventas_2025_count += 1
            
            print(f"✅ Cargadas {ventas_2025_count} ventas reales 2025")
            
        except Exception as e:
            print(f"⚠️ Error cargando datos reales 2025: {e}")
            print("   💡 ¿No hay ventas reales registradas en 2025?")
    
    # Crear DataFrame combinado
    if not datos_combinados:
        raise ValueError("❌ No se pudieron cargar datos. Verifica tu configuración.")
    
    df_combinado = pd.DataFrame(datos_combinados)
    
    # ✅ NORMALIZAR FECHAS para evitar conflictos de timezone
    df_combinado = normalizar_fechas(df_combinado)
    
    # Estadísticas del dataset combinado
    real_2025 = len(df_combinado[df_combinado['origen'] == 'real_2025'])
    sintetico_2019_2024 = len(df_combinado[df_combinado['origen'] == 'sintetico_2019_2024'])
    
    print(f"\n📈 RESUMEN DATOS COMBINADOS:")
    print(f"   • Sintéticos 2019-2024: {sintetico_2019_2024} registros")
    print(f"   • Reales 2025: {real_2025} registros")
    print(f"   • Total: {len(df_combinado)} registros")
    
    # ✅ MANEJO SEGURO DE FECHAS
    try:
        fecha_min = df_combinado['fecha'].min()
        fecha_max = df_combinado['fecha'].max()
        print(f"   • Período: {fecha_min} a {fecha_max}")
        
        # Mostrar distribución por año
        print(f"   • Distribución por año:")
        for año in sorted(df_combinado['fecha'].dt.year.unique()):
            count = len(df_combinado[df_combinado['fecha'].dt.year == año])
            origen = "REAL" if año >= 2025 else "SINTÉTICO"
            print(f"     - {año}: {count} registros ({origen})")
            
    except Exception as e:
        print(f"   • Período: Error calculando fechas - {e}")
    
    return df_combinado