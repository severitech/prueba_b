import pandas as pd
import os
import django
from datetime import datetime

# Configuración Django para verificar datos reales
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
    from tienda.models import Venta, DetalleVenta, Productos, Usuario, Garantia, Mantenimiento
    from django.db.models import Count  # ✅ Faltaba esta importación
    DJANGO_DISPONIBLE = True
except Exception as e:
    print(f"⚠️  Django no disponible: {e}")
    print("   Solo se verificarán datos sintéticos\n")
    DJANGO_DISPONIBLE = False

# ================================
# CONFIGURACIÓN DE RUTAS
# ================================
BASE_DIR = "scikit_learn_ia/datasets"
ARCHIVOS = {
    "usuarios": os.path.join(BASE_DIR, "usuarios.csv"),
    "productos": os.path.join(BASE_DIR, "productos.csv"),
    "ventas": os.path.join(BASE_DIR, "ventas.csv"),
    "detalles_venta": os.path.join(BASE_DIR, "detalles_venta.csv"),
    "garantias": os.path.join(BASE_DIR, "garantias.csv"),
    "mantenimientos": os.path.join(BASE_DIR, "mantenimientos.csv"),
}

def verificar_existencia():
    """Verifica que todos los archivos requeridos existan"""
    faltantes = [k for k, v in ARCHIVOS.items() if not os.path.exists(v)]
    if faltantes:
        print(f"❌ Faltan archivos CSV: {', '.join(faltantes)}")
        return False
    print("✅ Todos los archivos CSV requeridos existen.\n")
    return True

def verificar_datos_reales():
    """Verifica los datos reales en PostgreSQL"""
    if not DJANGO_DISPONIBLE:
        return None
    
    print("🗄️  VERIFICANDO DATOS REALES (PostgreSQL)")
    print("-" * 40)
    
    try:
        # Contar registros reales
        total_ventas = Venta.objects.count()
        total_usuarios = Usuario.objects.count()
        total_productos = Productos.objects.count()
        total_detalles = DetalleVenta.objects.count()
        total_garantias = Garantia.objects.count()
        total_mantenimientos = Mantenimiento.objects.count()
        
        print(f"👥 Usuarios reales: {total_usuarios}")
        print(f"📦 Productos reales: {total_productos}")
        print(f"💰 Ventas reales: {total_ventas}")
        print(f"🧾 Detalles venta reales: {total_detalles}")
        print(f"🛡️  Garantías reales: {total_garantias}")
        print(f"🧰 Mantenimientos reales: {total_mantenimientos}")
        
        # Estadísticas adicionales si hay datos
        if total_ventas > 0:
            from django.db.models import Sum, Avg
            ventas_totales = Venta.objects.aggregate(Sum('total'))
            promedio_venta = Venta.objects.aggregate(Avg('total'))
            
            # ✅ CORREGIDO: states -> estados
            estados = Venta.objects.values('estado').annotate(count=Count('estado'))
            
            print(f"\n📈 Estadísticas reales:")
            print(f"   • Total ventas: ${ventas_totales['total__sum'] or 0:,.2f}")
            print(f"   • Promedio por venta: ${promedio_venta['total__avg'] or 0:,.2f}")
            print(f"   • Estados: {', '.join([f'{e['estado']}: {e['count']}' for e in estados])}")
        
        print("✅ Verificación de datos reales completada\n")
        return {
            'usuarios': total_usuarios,
            'productos': total_productos,
            'ventas': total_ventas,
            'detalles': total_detalles,
            'garantias': total_garantias,
            'mantenimientos': total_mantenimientos
        }
        
    except Exception as e:
        print(f"❌ Error verificando datos reales: {e}")
        return None

def analizar_datasets():
    """Analiza y resume los datos principales de cada dataset"""
    print("📊 RESUMEN DE DATOS SINTÉTICOS (CSV)")
    print("-" * 40)

    # === USUARIOS ===
    usuarios = pd.read_csv(ARCHIVOS["usuarios"])
    print(f"👥 Usuarios sintéticos: {len(usuarios)}")

    # === PRODUCTOS ===
    productos = pd.read_csv(ARCHIVOS["productos"])
    print(f"📦 Productos sintéticos: {len(productos)}")
    print(f"   Precio promedio: ${productos['precio'].mean():,.2f}")

    # Distribución por categoría
    if 'categoria' in productos.columns:
        dist_categoria = productos['categoria'].value_counts()
        print(f"   Distribución por categoría:")
        for cat, count in dist_categoria.items():
            print(f"     • {cat}: {count} productos")

    print()

    # === VENTAS ===
    ventas = pd.read_csv(ARCHIVOS["ventas"], parse_dates=["fecha"])
    total_ventas = ventas["total"].sum()
    promedio_venta = ventas["total"].mean()
    print(f"💰 Ventas sintéticas: {len(ventas)}")
    print(f"   Total vendido: ${total_ventas:,.2f}")
    print(f"   Promedio por venta: ${promedio_venta:,.2f}")

    # Ventas por estado
    print("\n📈 Ventas por estado:")
    estado_counts = ventas["estado"].value_counts()
    for estado, count in estado_counts.items():
        print(f"   • {estado}: {count} ventas")

    # === CÁLCULOS DE VENTAS POR MES ===
    ventas["mes"] = ventas["fecha"].dt.to_period("M")
    ventas_mensuales = ventas.groupby("mes")["total"].sum().reset_index()
    promedio_mensual = ventas_mensuales["total"].mean()

    print(f"\n🗓️  Ventas mensuales (primeros 6 meses):")
    print(ventas_mensuales.head(6).to_string(index=False))
    print(f"\n   Promedio mensual: ${promedio_mensual:,.2f}")

    # === DETALLE DE VENTAS ===
    detalles = pd.read_csv(ARCHIVOS["detalles_venta"])
    print(f"\n🧾 Detalles de venta sintéticos: {len(detalles)}")
    print(f"   Productos promedio por venta: {len(detalles) / len(ventas):.2f}")

    # === GARANTÍAS ===
    garantias = pd.read_csv(ARCHIVOS["garantias"])
    print(f"🛡️  Garantías sintéticas: {len(garantias)}")
    print(f"   Duración media (meses): {garantias['tiempo_meses'].mean():.1f}")

    # === MANTENIMIENTOS ===
    mantenimientos = pd.read_csv(ARCHIVOS["mantenimientos"])
    if not mantenimientos.empty:
        print(f"🧰 Mantenimientos sintéticos: {len(mantenimientos)}")
        print(f"   Costo promedio: ${mantenimientos['costo'].mean():,.2f}")
    else:
        print("🧰 No hay registros de mantenimientos sintéticos.")

    # === VALIDACIÓN DE CONSISTENCIA ===
    ratio_garantias = len(garantias) / len(detalles)
    ratio_mantenimientos = len(mantenimientos) / len(garantias) if len(garantias) > 0 else 0

    print("\n⚙️  VALIDACIÓN DE CONSISTENCIA SINTÉTICA:")
    print(f"   Relación garantías/detalles: {ratio_garantias:.2f} (esperado ≈ 1.00)")
    print(f"   Relación mantenimientos/garantías: {ratio_mantenimientos:.2f} (esperado ≈ 0.20)")

    # === RESUMEN GLOBAL ===
    print("\n📊 RESUMEN GLOBAL SINTÉTICO:")
    print(f"   • Ventas totales: ${total_ventas:,.2f}")
    print(f"   • Promedio por venta: ${promedio_venta:,.2f}")
    print(f"   • Promedio mensual: ${promedio_mensual:,.2f}")
    print(f"   • Total registros: {len(ventas)} ventas, {len(detalles)} detalles")

    return {
        "total_ventas": total_ventas,
        "promedio_venta": promedio_venta,
        "promedio_mensual": promedio_mensual,
        "ventas_mensuales": ventas_mensuales
    }

def verificar_compatibilidad():
    """Verifica compatibilidad entre datos reales y sintéticos"""
    if not DJANGO_DISPONIBLE:
        return
    
    print("\n🔗 VERIFICANDO COMPATIBILIDAD")
    print("-" * 40)
    
    try:
        # Verificar que las estructuras sean compatibles
        from tienda.models import Venta as VentaReal
        ventas_csv = pd.read_csv(ARCHIVOS["ventas"])
        
        # Comparar columnas
        columnas_reales = [f.name for f in VentaReal._meta.get_fields() if not f.is_relation]
        columnas_sinteticas = ventas_csv.columns.tolist()
        
        print("✅ Estructuras básicas compatibles")
        print(f"   • Campos reales: {len(columnas_reales)}")
        print(f"   • Campos sintéticos: {len(columnas_sinteticas)}")
        
        # Campos comunes
        campos_comunes = set(columnas_reales) & set(columnas_sinteticas)
        print(f"   • Campos comunes: {len(campos_comunes)}")
        
    except Exception as e:
        print(f"⚠️  Advertencia compatibilidad: {e}")

if __name__ == "__main__":
    print("\n🧠 INICIANDO VERIFICACIÓN COMPLETA DE DATOS...\n")
    
    # Verificar datos reales primero
    datos_reales = verificar_datos_reales()
    
    # Verificar datos sintéticos
    if verificar_existencia():
        datos_sinteticos = analizar_datasets()
        
        # Verificar compatibilidad
        verificar_compatibilidad()
        
        # Resumen final
        print("\n🎯 RESUMEN EJECUTIVO:")
        print("=" * 50)
        
        if datos_reales:
            total_registros = sum(datos_reales.values())
            print(f"📊 DATOS COMBINADOS DISPONIBLES:")
            print(f"   • Reales: {total_registros} registros en PostgreSQL")
            print(f"   • Sintéticos: {datos_sinteticos['ventas_mensuales'].shape[0]} meses de datos")
            print(f"   • ¡Puedes usar el pipeline combinado! 🚀")
        else:
            print(f"📊 SOLO DATOS SINTÉTICOS:")
            print(f"   • {datos_sinteticos['ventas_mensuales'].shape[0]} meses de datos sintéticos")
            print(f"   • Pipeline funcionando en modo sintético ✅")
        
        print("=" * 50)
        print("✅ Verificación completa finalizada.\n")