import pandas as pd
<<<<<<< HEAD
import os
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Inicializar Faker
=======
import os, sys
import numpy as np
from faker import Faker
import random
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

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

    # Normalizar/parsear fecha si existe
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True)

    # Si traen 'periodo' (YYYY-MM), úsalo como fuente
    if 'periodo' in df.columns and df['periodo'].notna().any():
        base = pd.to_datetime(df['periodo'].astype(str) + "-01", errors='coerce', utc=True)
        if 'fecha' not in df.columns:
            df['fecha'] = base
        else:
            df.loc[df['fecha'].isna(), 'fecha'] = base

    # Si faltan 'anio'/'mes', intentar derivarlos de 'fecha'
    if ('anio' not in df.columns or 'mes' not in df.columns) and 'fecha' in df.columns:
        df['anio'] = df['fecha'].dt.year
        df['mes']  = df['fecha'].dt.month

    # Completar fecha para filas con NaT cuando tengamos anio/mes
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

    # Recalcular anio/mes/periodo desde fecha final
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
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
fake = Faker('es_ES')
np.random.seed(42)
random.seed(42)

<<<<<<< HEAD
# Configuración
=======
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
FECHA_INICIO_HISTORIA = datetime(2019, 1, 1)
FECHA_FIN_HISTORIA = datetime(2024, 12, 31)
NUM_USUARIOS = 500
NUM_PRODUCTOS = 150
<<<<<<< HEAD
NUM_VENTAS = 40000  # Aumentado para cubrir 72 meses
=======
NUM_VENTAS = 50000  
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f

print("🎯 GENERANDO DATOS COMPLETOS (72 MESES) CON PATRONES FUERTES")

# ================================
# GENERAR DATOS BASE
# ================================
print("👥 Generando usuarios...")
usuarios = [{"id": i, "nombre": fake.name(), "correo": fake.email()} 
           for i in range(1, NUM_USUARIOS + 1)]
df_usuarios = pd.DataFrame(usuarios)

print("📦 Generando productos de electrodomésticos...")

<<<<<<< HEAD
# Mapeo de subcategorías basado en tu archivo JSON
subcategorias_electrodomesticos = [
    # Cocina (categoria 2)
=======
subcategorias_electrodomesticos = [
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    {"id": 1, "descripcion": "Hornos", "categoria": 2},
    {"id": 2, "descripcion": "Microondas", "categoria": 2},
    {"id": 3, "descripcion": "Cocinas", "categoria": 2},
    {"id": 4, "descripcion": "Batidoras y Licuadoras", "categoria": 2},
    {"id": 5, "descripcion": "Freidoras", "categoria": 2},
<<<<<<< HEAD
    
    # Lavandería (categoria 3)
=======
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    {"id": 6, "descripcion": "Lavadoras", "categoria": 3},
    {"id": 7, "descripcion": "Secadoras", "categoria": 3},
    {"id": 8, "descripcion": "Planchas", "categoria": 3},
    {"id": 9, "descripcion": "Centros de planchado", "categoria": 3},
<<<<<<< HEAD
    
    # Entretenimiento y Tecnología (categoria 5)
    {"id": 14, "descripcion": "Televisores", "categoria": 5},
    {"id": 15, "descripcion": "Sistemas de sonido", "categoria": 5},
    
    # Cuidado personal (categoria 7)
    {"id": 20, "descripcion": "Secadores de pelo", "categoria": 7},
    {"id": 21, "descripcion": "Cepillos de dientes eléctricos", "categoria": 7},
    
    # Cocina y Preparación de Bebidas (categoria 8)
    {"id": 23, "descripcion": "Cafeteras", "categoria": 8},
    {"id": 24, "descripcion": "Teteras eléctricas", "categoria": 8},
    
    # Electrodomésticos inteligentes (categoria 9)
    {"id": 26, "descripcion": "Dispositivos inteligentes", "categoria": 9}
]

# Nombres de productos por subcategoría (ampliados)
=======
    {"id": 14, "descripcion": "Televisores", "categoria": 5},
    {"id": 15, "descripcion": "Sistemas de sonido", "categoria": 5},
    {"id": 20, "descripcion": "Secadores de pelo", "categoria": 7},
    {"id": 21, "descripcion": "Cepillos de dientes eléctricos", "categoria": 7},
    {"id": 23, "descripcion": "Cafeteras", "categoria": 8},
    {"id": 24, "descripcion": "Teteras eléctricas", "categoria": 8},
    {"id": 26, "descripcion": "Dispositivos inteligentes", "categoria": 9}
]

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
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

<<<<<<< HEAD
# Rangos de precios por subcategoría
rangos_precios = {
    1: (200, 800),    # Hornos
    2: (80, 400),     # Microondas
    3: (300, 1200),   # Cocinas
    4: (50, 300),     # Batidoras/Licuadoras
    5: (100, 500),    # Freidoras
    6: (300, 1500),   # Lavadoras
    7: (400, 1200),   # Secadoras
    8: (30, 200),     # Planchas
    9: (80, 300),     # Centros planchado
    14: (300, 2000),  # Televisores
    15: (150, 800),   # Sistemas sonido
    20: (40, 150),    # Secadores
    21: (30, 120),    # Cepillos dentales
    23: (60, 600),    # Cafeteras
    24: (25, 100),    # Teteras
    26: (50, 400)     # Dispositivos inteligentes
=======
rangos_precios = {
    1: (200, 800), 2: (80, 400), 3: (300, 1200), 4: (50, 300), 5: (100, 500),
    6: (300, 1500), 7: (400, 1200), 8: (30, 200), 9: (80, 300),
    14: (300, 2000), 15: (150, 800), 20: (40, 150), 21: (30, 120),
    23: (60, 600), 24: (25, 100), 26: (50, 400)
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
}

productos = []
for i in range(1, NUM_PRODUCTOS + 1):
    subcat = random.choice(subcategorias_electrodomesticos)
    subcat_id = subcat["id"]
    subcat_desc = subcat["descripcion"]
    cat_id = subcat["categoria"]
<<<<<<< HEAD
    
    # Seleccionar nombre base y añadir características
    nombre_base = random.choice(nombres_productos[subcat_id])
    caracteristicas = [f"{random.choice(['Negro', 'Blanco', 'Plateado', 'Acero Inox'])}",
                      f"{random.choice(['Digital', 'Analógico', 'Touch', 'Programable'])}",
                      f"{random.choice([f'{random.randint(1,10)}L', f'{random.randint(500,2000)}W', f'{random.randint(4,12)} programas'])}"]
    
    descripcion_completa = f"{nombre_base} {caracteristicas[0]} {caracteristicas[1]} {caracteristicas[2]}"
    
    # Precio según rango de subcategoría
    precio_min, precio_max = rangos_precios[subcat_id]
    precio = round(random.uniform(precio_min, precio_max), 2)
    
=======

    nombre_base = random.choice(nombres_productos[subcat_id])
    caracteristicas = [
        f"{random.choice(['Negro', 'Blanco', 'Plateado', 'Acero Inox'])}",
        f"{random.choice(['Digital', 'Analógico', 'Touch', 'Programable'])}",
        f"{random.choice([f'{random.randint(1,10)}L', f'{random.randint(500,2000)}W', f'{random.randint(4,12)} programas'])}"
    ]
    descripcion_completa = f"{nombre_base} {caracteristicas[0]} {caracteristicas[1]} {caracteristicas[2]}"

    precio_min, precio_max = rangos_precios[subcat_id]
    precio = round(random.uniform(precio_min, precio_max), 2)

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
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
<<<<<<< HEAD
    if mes in [11, 12]:  # Navidad - ALTÍSIMO
        return 2.8  # 180% más
    elif mes in [6, 7]:  # Verano - ALTO
        return 1.9  # 90% más  
    elif mes in [1, 2]:  # Post-navidad - MUY BAJO
        return 0.3  # 70% menos
    elif mes in [9]:     # Vuelta al cole - ALTO
        return 1.7  # 70% más
    else:               # Normal
        return 1.0

def generar_tendencia_crecimiento_fuerte(año, mes):
    """Crecimiento MENSUAL constante y fuerte"""
    meses_totales = (año - 2019) * 12 + (mes - 1)
    return 1.0 + (meses_totales * 0.012)  # 1.2% mensual

# Generar ventas para los 72 meses COMPLETOS
ventas_mensuales = []
venta_id = 1

for año in range(2019, 2025):
    for mes in range(1, 13):
        # Calcular cantidad base con patrones SUPER FUERTES
        base_mensual = 500  # Base constante
        
        # Aplicar patrones
        factor_estacional = generar_patron_estacional_super_fuerte(mes)
        factor_crecimiento = generar_tendencia_crecimiento_fuerte(año, mes)
        
        cantidad_mensual = int(base_mensual * factor_estacional * factor_crecimiento)
        
        # Generar múltiples ventas para este mes (asegurar suficientes)
        ventas_por_mes = max(250, cantidad_mensual // 2)  # Aprox 2 productos por venta
        
        for _ in range(ventas_por_mes):
            # Generar fecha dentro del mes específico
            try:
                fecha = fake.date_time_between(
                    start_date=datetime(año, mes, 1),
                    end_date=datetime(año, mes, 28) if mes != 2 else datetime(año, mes, 25)
                )
            except:
                fecha = datetime(año, mes, 15)  # Fallback
                
=======
    if mes in [11, 12]:      # Navidad - ALTÍSIMO
        return 2.8           # +180%
    elif mes in [6, 7]:      # Verano - ALTO
        return 1.9           # +90%
    elif mes in [1, 2]:      # Post-navidad - MUY BAJO
        return 0.3           # -70%
    elif mes == 9:           # Vuelta al cole - ALTO
        return 1.7           # +70%
    else:                    # Normal
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
            # Fecha aleatoria dentro del mes (se normaliza a UTC en add_periodo_fields)
            try:
                fecha = fake.date_time_between(
                    start_date=datetime(anio, mes, 1),
                    end_date=datetime(anio, mes, 28)
                )
            except Exception:
                fecha = datetime(anio, mes, 15)

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
            ventas_mensuales.append({
                "id": venta_id,
                "usuario_id": random.randint(1, NUM_USUARIOS),
                "fecha": fecha,
                "total": round(random.uniform(100, 500), 2),
<<<<<<< HEAD
                "estado": "Pagado"
            })
            venta_id += 1
            
=======
                "estado": "Pagado",
                "anio": anio,   # por conveniencia
                "mes": mes
            })
            venta_id += 1

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
            if venta_id > NUM_VENTAS:
                break
        if venta_id > NUM_VENTAS:
            break
    if venta_id > NUM_VENTAS:
        break

df_ventas = pd.DataFrame(ventas_mensuales)
<<<<<<< HEAD
=======
# Normalización temporal completa (fecha UTC, anio, mes, periodo)
df_ventas = add_periodo_fields(df_ventas)
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f

# ================================
# GENERAR DETALLES DE VENTA
# ================================
print("🧾 Generando detalles de venta...")
detalles = []

<<<<<<< HEAD
for venta_id in range(1, NUM_VENTAS + 1):
    num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
    productos_random = random.sample(range(1, NUM_PRODUCTOS + 1), num_items)
    
=======
# Generar detalles solo para ventas realmente creadas
max_venta_id = int(df_ventas['id'].max()) if not df_ventas.empty else 0

for vid in range(1, max_venta_id + 1):
    num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
    productos_random = random.sample(range(1, NUM_PRODUCTOS + 1), num_items)

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    for prod_id in productos_random:
        cantidad = random.choices([1, 2], weights=[0.8, 0.2])[0]
        precio = df_productos.loc[df_productos["id"] == prod_id, "precio"].values[0]
        subtotal = round(precio * cantidad, 2)
<<<<<<< HEAD
        
        detalles.append({
            "venta_id": venta_id,
=======

        detalles.append({
            "venta_id": vid,
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
            "producto_id": prod_id,
            "cantidad": cantidad,
            "subtotal": subtotal
        })

df_detalles = pd.DataFrame(detalles)

<<<<<<< HEAD
=======
##### ---------para clientes y categorias (train model panel)

# ================================
# GENERAR SERIES POR PRODUCTO, CATEGORIA Y CLIENTE
# ================================
print("📊 Generando series por producto, categoría y cliente...")

# Mezclar detalles con productos y ventas para obtener contexto completo
df_join = df_detalles.merge(df_ventas[['id', 'usuario_id', 'fecha']], left_on='venta_id', right_on='id', how='left')
df_join = df_join.merge(df_productos[['id', 'categoria', 'subcategoria']], left_on='producto_id', right_on='id', how='left')

# Extraer año y mes
df_join['fecha'] = pd.to_datetime(df_join['fecha'])
df_join['anio'] = df_join['fecha'].dt.year
df_join['mes'] = df_join['fecha'].dt.month

# === Por PRODUCTO ===
df_producto = df_join.groupby(['producto_id', 'anio', 'mes'])['cantidad'].sum().reset_index()
df_producto.to_csv("scikit_learn_ia/datasets/cantidades_por_producto_mensual.csv", index=False)

# === Por CATEGORÍA ===
df_categoria = df_join.groupby(['categoria', 'anio', 'mes'])['cantidad'].sum().reset_index()
df_categoria.to_csv("scikit_learn_ia/datasets/cantidades_por_categoria_mensual.csv", index=False)

# === Por CLIENTE ===
df_cliente = df_join.groupby(['usuario_id', 'anio', 'mes'])['cantidad'].sum().reset_index()
df_cliente.to_csv("scikit_learn_ia/datasets/cantidades_por_cliente_mensual.csv", index=False)

print("✅ Series temporales generadas correctamente (producto, categoría y cliente).")

#########

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
# ================================
# GUARDAR ARCHIVOS
# ================================
print("💾 Guardando archivos...")
output_dir = "scikit_learn_ia/datasets"
os.makedirs(output_dir, exist_ok=True)

df_usuarios.to_csv(f"{output_dir}/usuarios.csv", index=False)
df_productos.to_csv(f"{output_dir}/productos.csv", index=False)
<<<<<<< HEAD
=======

# Ventas ahora incluye: fecha (UTC), anio, mes, periodo
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
df_ventas.to_csv(f"{output_dir}/ventas.csv", index=False)
df_detalles.to_csv(f"{output_dir}/detalles_venta.csv", index=False)

# ================================
# VALIDACIÓN COMPLETA
# ================================
print("\n" + "="*60)
print("📊 VALIDACIÓN DE DATOS - 72 MESES COMPLETOS")
print("="*60)

<<<<<<< HEAD
# Crear dataset mensual para validación
df_combinado = pd.merge(df_detalles, df_ventas, left_on='venta_id', right_on='id')
df_combinado['fecha'] = pd.to_datetime(df_combinado['fecha'])
df_combinado['anio'] = df_combinado['fecha'].dt.year
df_combinado['mes'] = df_combinado['fecha'].dt.month

df_mensual = df_combinado.groupby(['anio', 'mes']).agg({
    'cantidad': 'sum'
}).reset_index()

print(f"✅ MESES GENERADOS: {len(df_mensual)}/72")
print(f"✅ CANTIDAD TOTAL: {df_mensual['cantidad'].sum():,} productos")
print(f"✅ PROMEDIO MENSUAL: {df_mensual['cantidad'].mean():.0f} productos")

print("\n📈 EVOLUCIÓN ANUAL:")
for año in range(2019, 2025):
    datos_año = df_mensual[df_mensual['anio'] == año]
    if len(datos_año) > 0:
        total_año = datos_año['cantidad'].sum()
        promedio_año = datos_año['cantidad'].mean()
        print(f"   • {año}: {total_año:,} productos (avg: {promedio_año:.0f})")

print(f"\n🎯 PATRONES ESTACIONALES CONFIRMADOS:")
# Verificar patrones
navidad_avg = df_mensual[df_mensual['mes'].isin([11, 12])]['cantidad'].mean()
verano_avg = df_mensual[df_mensual['mes'].isin([6, 7])]['cantidad'].mean()
inicio_avg = df_mensual[df_mensual['mes'].isin([1, 2])]['cantidad'].mean()

print(f"   • Navidad (nov-dic): {navidad_avg:.0f} productos")
print(f"   • Verano (jun-jul): {verano_avg:.0f} productos") 
print(f"   • Inicio año (ene-feb): {inicio_avg:.0f} productos")

print(f"\n✅ ¡DATOS LISTOS PARA ML CON PATRONES SUPER FUERTES!")
=======
# Combinar, normalizar y validar cobertura mensual
df_combinado = pd.merge(df_detalles, df_ventas, left_on='venta_id', right_on='id', how='inner', suffixes=('_det', ''))
df_combinado = add_periodo_fields(df_combinado)  # asegura anio/mes/periodo aunque haya NaT

# Agregado mensual por cantidad de ítems vendidos (campo 'cantidad' de detalles)
df_mensual = (df_combinado
              .groupby(['anio', 'mes', 'periodo'], as_index=False)
              .agg(cantidad=('cantidad', 'sum')))

# Validar cobertura de 2019-01 a 2024-12 (72 meses)
idx_mes = pd.period_range('2019-01', '2024-12', freq='M')
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
verano_avg = df_mensual[df_mensual['mes'].isin([6, 7])]['cantidad'].mean()
inicio_avg = df_mensual[df_mensual['mes'].isin([1, 2])]['cantidad'].mean()
print(f"   • Navidad (nov-dic): {navidad_avg:.0f} productos")
print(f"   • Verano (jun-jul): {verano_avg:.0f} productos")
print(f"   • Inicio año (ene-feb): {inicio_avg:.0f} productos")

print(f"\n✅ ¡DATOS LISTOS PARA ML CON PATRONES SUPER FUERTES!")
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
