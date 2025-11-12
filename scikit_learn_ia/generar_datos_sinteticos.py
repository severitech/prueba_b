# scikit_learn_ia/generar_datos_sinteticos.py
import pandas as pd
import os, sys
import numpy as np
from faker import Faker
import random
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 🛣️ Rutas unificadas (local / Railway) + banner de diagnóstico
from scikit_learn_ia.paths import (
    DATA_DIR,  # .../scikit_learn_ia/datasets (o IA_DATA_DIR)
    print_paths_banner
)

# Forzar UTF-8 en Windows/PowerShell
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ================================
# HELPERS DE TIEMPO / PERIODO
# ================================
def _build_fecha_canonica(anio: int, mes: int) -> pd.Timestamp:
    """Primer día del mes en UTC (fecha canónica)."""
    return pd.to_datetime(f"{int(anio)}-{int(mes):02d}-01", utc=True)

def add_periodo_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Asegura columnas: fecha (UTC), anio, mes, periodo (YYYY-MM).
    Soporta entradas con 'fecha' NaT y/o columnas 'anio'/'mes' o 'periodo'.
    """
    df = df.copy()

    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True)

    if 'periodo' in df.columns and df['periodo'].notna().any():
        base = pd.to_datetime(df['periodo'].astype(str) + "-01", errors='coerce', utc=True)
        if 'fecha' not in df.columns:
            df['fecha'] = base
        else:
            df.loc[df['fecha'].isna(), 'fecha'] = base

    if ('anio' not in df.columns or 'mes' not in df.columns) and 'fecha' in df.columns:
        df['anio'] = df['fecha'].dt.year
        df['mes']  = df['fecha'].dt.month

    if 'anio' in df.columns and 'mes' in df.columns:
        if 'fecha' not in df.columns:
            df['fecha'] = [
                _build_fecha_canonica(a, m) if pd.notna(a) and pd.notna(m) else pd.NaT
                for a, m in zip(df['anio'], df['mes'])
            ]
        else:
            mask = df['fecha'].isna() & df['anio'].notna() & df['mes'].notna()
            df.loc[mask, 'fecha'] = [
                _build_fecha_canonica(a, m) for a, m in zip(df.loc[mask, 'anio'], df.loc[mask, 'mes'])
            ]

    if 'fecha' in df.columns:
        df['anio']    = df['fecha'].dt.year
        df['mes']     = df['fecha'].dt.month
        df['periodo'] = df['fecha'].dt.strftime('%Y-%m')
    else:
        if 'anio' in df.columns and 'mes' in df.columns:
            df['periodo'] = df.apply(lambda r: f"{int(r['anio'])}-{int(r['mes']):02d}", axis=1)

    return df

# ================================
# CONFIGURACIÓN (SIN CAMBIOS DE LÓGICA)
# ================================
print_paths_banner("🔍 Ejecutando generar_datos_sinteticos.py")

fake = Faker('es_ES')
np.random.seed(42)
random.seed(42)

FECHA_INICIO_HISTORIA = datetime(2019, 1, 1)
FECHA_FIN_HISTORIA   = datetime(2024, 12, 31)
NUM_USUARIOS   = 500
NUM_PRODUCTOS  = 150
NUM_VENTAS     = 50000  # Aprox 2 ítems/venta → ~100k ítems

print("🎯 GENERANDO DATOS COMPLETOS (72 MESES) CON PATRONES FUERTES")

# ================================
# GENERAR DATOS BASE
# ================================
print("👥 Generando usuarios...")
usuarios = [{"id": i, "nombre": fake.name(), "correo": fake.email()}
            for i in range(1, NUM_USUARIOS + 1)]
df_usuarios = pd.DataFrame(usuarios)

print("📦 Generando productos de electrodomésticos...")
subcategorias_electrodomesticos = [
    {"id": 1, "descripcion": "Hornos", "categoria": 2},
    {"id": 2, "descripcion": "Microondas", "categoria": 2},
    {"id": 3, "descripcion": "Cocinas", "categoria": 2},
    {"id": 4, "descripcion": "Batidoras y Licuadoras", "categoria": 2},
    {"id": 5, "descripcion": "Freidoras", "categoria": 2},
    {"id": 6, "descripcion": "Lavadoras", "categoria": 3},
    {"id": 7, "descripcion": "Secadoras", "categoria": 3},
    {"id": 8, "descripcion": "Planchas", "categoria": 3},
    {"id": 9, "descripcion": "Centros de planchado", "categoria": 3},
    {"id": 14, "descripcion": "Televisores", "categoria": 5},
    {"id": 15, "descripcion": "Sistemas de sonido", "categoria": 5},
    {"id": 20, "descripcion": "Secadores de pelo", "categoria": 7},
    {"id": 21, "descripcion": "Cepillos de dientes eléctricos", "categoria": 7},
    {"id": 23, "descripcion": "Cafeteras", "categoria": 8},
    {"id": 24, "descripcion": "Teteras eléctricas", "categoria": 8},
    {"id": 26, "descripcion": "Dispositivos inteligentes", "categoria": 9}
]

nombres_productos = {
    1: ["Horno Eléctrico", "Horno a Gas", "Horno Empotrable", "Horno Convección", "Horno Multifunción"],
    2: ["Microondas Digital", "Microondas Grill", "Microondas Empotrable", "Microondas Compacto"],
    3: ["Cocina a Gas", "Cocina Eléctrica", "Cocina Mixta", "Cocina Industrial"],
    4: ["Licuadora Profesional", "Batidora de Mano", "Batidora de Pie", "Licuadora Extractora"],
    5: ["Freidora de Aire", "Freidora Profesional", "Freidora Sin Aceite", "Freidora Doble"],
    6: ["Lavadora Carga Frontal", "Lavadora Carga Superior", "Lavadora Secadora", "Lavadora Inteligente"],
    7: ["Secadora de Ropa", "Secadora Heat Pump", "Secadora Gas", "Secadora Eléctrica"],
    8: ["Plancha a Vapor", "Plancha Profesional", "Plancha Cerámica", "Plancha Inalámbrica"],
    9: ["Centro de Planchado", "Mesa de Planchar", "Sistema de Vapor"],
    14: ["Televisor LED", "Televisor 4K", "Televisor OLED", "Televisor Smart"],
    15: ["Soundbar", "Sistema Home Theater", "Altavoces Inalámbricos"],
    20: ["Secador Profesional", "Secador Iónico", "Secador Turmalina"],
    21: ["Cepillo Eléctrico Recargable", "Cepillo Sónico", "Cepillo Infantil"],
    23: ["Cafetera Express", "Cafetera Goteo", "Cafetera Cápsulas", "Cafetera Superautomática"],
    24: ["Tetera Eléctrica", "Hervidor de Agua", "Tetera Programable"],
    26: ["Aspiradora Robot", "Enchufe Inteligente", "Termostato Inteligente"]
}

rangos_precios = {
    1: (200, 800), 2: (80, 400), 3: (300, 1200), 4: (50, 300), 5: (100, 500),
    6: (300, 1500), 7: (400, 1200), 8: (30, 200), 9: (80, 300),
    14: (300, 2000), 15: (150, 800), 20: (40, 150), 21: (30, 120),
    23: (60, 600), 24: (25, 100), 26: (50, 400)
}

productos = []
for i in range(1, NUM_PRODUCTOS + 1):
    subcat = random.choice(subcategorias_electrodomesticos)
    subcat_id = subcat["id"]
    subcat_desc = subcat["descripcion"]
    cat_id = subcat["categoria"]

    nombre_base = random.choice(nombres_productos[subcat_id])
    caracteristicas = [
        f"{random.choice(['Negro', 'Blanco', 'Plateado', 'Acero Inox'])}",
        f"{random.choice(['Digital', 'Analógico', 'Touch', 'Programable'])}",
        f"{random.choice([f'{random.randint(1,10)}L', f'{random.randint(500,2000)}W', f'{random.randint(4,12)} programas'])}"
    ]
    descripcion_completa = f"{nombre_base} {caracteristicas[0]} {caracteristicas[1]} {caracteristicas[2]}"

    precio_min, precio_max = rangos_precios[subcat_id]
    precio = round(random.uniform(precio_min, precio_max), 2)

    productos.append({
        "id": i,
        "descripcion": descripcion_completa,
        "precio": precio,
        "stock": random.randint(10, 200),
        "categoria": f"Categoría {cat_id}",
        "subcategoria_id": subcat_id,
        "subcategoria": subcat_desc
    })

df_productos = pd.DataFrame(productos)

# ================================
# GENERAR VENTAS COMPLETAS (72 MESES)
# ================================
print("💰 Generando ventas para 72 meses completos...")

def generar_patron_estacional_super_fuerte(mes):
    """Patrones SUPER FUERTES y CONSISTENTES"""
    if mes in [11, 12]:      # Navidad - ALTÍSIMO
        return 2.8
    elif mes in [6, 7]:      # Verano - ALTO
        return 1.9
    elif mes in [1, 2]:      # Post-navidad - MUY BAJO
        return 0.3
    elif mes == 9:           # Vuelta al cole - ALTO
        return 1.7
    else:
        return 1.0

def generar_tendencia_crecimiento_fuerte(anio, mes):
    """Crecimiento MENSUAL constante y fuerte"""
    meses_totales = (anio - 2019) * 12 + (mes - 1)
    return 1.0 + (meses_totales * 0.012)  # 1.2% mensual

ventas_mensuales = []
venta_id = 1

for anio in range(2019, 2025):
    for mes in range(1, 13):
        base_mensual = 500
        factor_estacional = generar_patron_estacional_super_fuerte(mes)
        factor_crecimiento = generar_tendencia_crecimiento_fuerte(anio, mes)
        cantidad_mensual = int(base_mensual * factor_estacional * factor_crecimiento)

        # Aprox 2 productos por venta → asegurar suficientes ventas por mes
        ventas_por_mes = max(250, cantidad_mensual // 2)

        for _ in range(ventas_por_mes):
            try:
                fecha = fake.date_time_between(
                    start_date=datetime(anio, mes, 1),
                    end_date=datetime(anio, mes, 28)
                )
            except Exception:
                fecha = datetime(anio, mes, 15)

            ventas_mensuales.append({
                "id": venta_id,
                "usuario_id": random.randint(1, NUM_USUARIOS),
                "fecha": fecha,
                "total": round(random.uniform(100, 500), 2),
                "estado": "Pagado",
                "anio": anio,   # por conveniencia
                "mes": mes
            })
            venta_id += 1

            if venta_id > NUM_VENTAS:
                break
        if venta_id > NUM_VENTAS:
            break
    if venta_id > NUM_VENTAS:
        break

df_ventas = pd.DataFrame(ventas_mensuales)
df_ventas = add_periodo_fields(df_ventas)

# ================================
# GENERAR DETALLES DE VENTA
# ================================
print("🧾 Generando detalles de venta...")
detalles = []

max_venta_id = int(df_ventas['id'].max()) if not df_ventas.empty else 0

for vid in range(1, max_venta_id + 1):
    num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
    productos_random = random.sample(range(1, NUM_PRODUCTOS + 1), num_items)

    for prod_id in productos_random:
        cantidad = random.choices([1, 2], weights=[0.8, 0.2])[0]
        precio = df_productos.loc[df_productos["id"] == prod_id, "precio"].values[0]
        subtotal = round(precio * cantidad, 2)

        detalles.append({
            "venta_id": vid,
            "producto_id": prod_id,
            "cantidad": cantidad,
            "subtotal": subtotal
        })

df_detalles = pd.DataFrame(detalles)

# ================================
# SERIES PARA PANEL (producto / categoría / cliente)
# ================================
print("📊 Generando series por producto, categoría y cliente...")

df_join = df_detalles.merge(
    df_ventas[['id', 'usuario_id', 'fecha']],
    left_on='venta_id', right_on='id', how='left'
).merge(
    df_productos[['id', 'categoria', 'subcategoria']],
    left_on='producto_id', right_on='id', how='left'
)

df_join['fecha'] = pd.to_datetime(df_join['fecha'], errors='coerce', utc=True)
df_join['anio']  = df_join['fecha'].dt.year
df_join['mes']   = df_join['fecha'].dt.month

df_producto  = df_join.groupby(['producto_id', 'anio', 'mes'])['cantidad'].sum().reset_index()
df_categoria = df_join.groupby(['categoria',   'anio', 'mes'])['cantidad'].sum().reset_index()
df_cliente   = df_join.groupby(['usuario_id',  'anio', 'mes'])['cantidad'].sum().reset_index()

(df_producto).to_csv( DATA_DIR / "cantidades_por_producto_mensual.csv",  index=False)
(df_categoria).to_csv(DATA_DIR / "cantidades_por_categoria_mensual.csv", index=False)
(df_cliente).to_csv(  DATA_DIR / "cantidades_por_cliente_mensual.csv",   index=False)

print("✅ Series temporales generadas correctamente (producto, categoría y cliente).")

# ================================
# GUARDAR ARCHIVOS BASE
# ================================
print("💾 Guardando archivos base...")
DATA_DIR.mkdir(parents=True, exist_ok=True)

(df_usuarios).to_csv( DATA_DIR / "usuarios.csv",        index=False)
(df_productos).to_csv(DATA_DIR / "productos.csv",       index=False)
(df_ventas).to_csv(   DATA_DIR / "ventas.csv",          index=False)
(df_detalles).to_csv( DATA_DIR / "detalles_venta.csv",  index=False)

# ================================
# VALIDACIÓN COMPLETA
# ================================
print("\n" + "="*60)
print("📊 VALIDACIÓN DE DATOS - 72 MESES COMPLETOS")
print("="*60)

df_combinado = pd.merge(
    df_detalles, df_ventas, left_on='venta_id', right_on='id', how='inner', suffixes=('_det', '')
)
df_combinado = add_periodo_fields(df_combinado)

df_mensual = (df_combinado
              .groupby(['anio', 'mes', 'periodo'], as_index=False)
              .agg(cantidad=('cantidad', 'sum')))

idx_mes   = pd.period_range('2019-01', '2024-12', freq='M')
esperados = set([p.strftime('%Y-%m') for p in idx_mes])
presentes = set(df_mensual['periodo'].unique().tolist())
faltantes = sorted(list(esperados - presentes))
cobertura = len(presentes & esperados)

print(f"✅ MESES GENERADOS: {cobertura}/72")
print(f"✅ CANTIDAD TOTAL: {df_mensual['cantidad'].sum():,} productos")
print(f"✅ PROMEDIO MENSUAL: {df_mensual['cantidad'].mean():.0f} productos")

if faltantes:
    print("\n⚠️ Meses faltantes (revisar NUM_VENTAS si cortó temprano):")
    print(", ".join(faltantes))

print("\n📈 EVOLUCIÓN ANUAL:")
for anio in range(2019, 2025):
    datos_anio = df_mensual[df_mensual['anio'] == anio]
    if len(datos_anio) > 0:
        total_anio = int(datos_anio['cantidad'].sum())
        promedio_anio = float(datos_anio['cantidad'].mean())
        print(f"   • {anio}: {total_anio:,} productos (avg: {promedio_anio:.0f})")

print(f"\n🎯 PATRONES ESTACIONALES CONFIRMADOS:")
navidad_avg = df_mensual[df_mensual['mes'].isin([11, 12])]['cantidad'].mean()
verano_avg  = df_mensual[df_mensual['mes'].isin([6, 7])]['cantidad'].mean()
inicio_avg  = df_mensual[df_mensual['mes'].isin([1, 2])]['cantidad'].mean()
print(f"   • Navidad (nov-dic): {navidad_avg:.0f} productos")
print(f"   • Verano (jun-jul): {verano_avg:.0f} productos")
print(f"   • Inicio año (ene-feb): {inicio_avg:.0f} productos")

print("\n📂 Archivos generados en:", DATA_DIR)
print("✅ ¡DATOS LISTOS PARA ML CON PATRONES SUPER FUERTES!\n")
