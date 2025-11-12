import pandas as pd
import numpy as np
import joblib
import json
<<<<<<< HEAD
import os
import sys
=======
import os, sys
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

<<<<<<< HEAD
=======
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
class ModelConfig:
    RANDOM_STATE = 42
    MODEL_PATH = "scikit_learn_ia/model/modelo_prediccion_cantidades.joblib"
    METADATA_PATH = "scikit_learn_ia/model/metadata_cantidades.json"

<<<<<<< HEAD
def cargar_y_preparar_datos():
    """Carga y prepara datos asegurando 72 meses completos"""
    print("📦 Cargando y validando datos...")
    
    try:
        # Cargar datos
        df_ventas = pd.read_csv("scikit_learn_ia/datasets/ventas.csv", parse_dates=['fecha'])
        df_detalles = pd.read_csv("scikit_learn_ia/datasets/detalles_venta.csv")
        
        print(f"   ✅ Ventas cargadas: {len(df_ventas)} registros")
        print(f"   ✅ Detalles cargados: {len(df_detalles)} registros")
        
        # Combinar
        df_combinado = pd.merge(df_detalles, df_ventas, left_on='venta_id', right_on='id')
        df_combinado['fecha'] = pd.to_datetime(df_combinado['fecha'])
        
        # Crear dataset mensual
        df_combinado['anio'] = df_combinado['fecha'].dt.year
        df_combinado['mes'] = df_combinado['fecha'].dt.month
        
        df_mensual = df_combinado.groupby(['anio', 'mes']).agg({
            'cantidad': 'sum'
        }).reset_index()
        
        # Validar que tenemos 72 meses
        meses_esperados = 72
        meses_obtenidos = len(df_mensual)
        
        print(f"   ✅ Meses obtenidos: {meses_obtenidos}/{meses_esperados}")
        
        if meses_obtenidos < meses_esperados:
            print(f"   ⚠️  Completando meses faltantes...")
            # Completar meses faltantes
            todos_meses = []
            for año in range(2019, 2025):
                for mes in range(1, 13):
                    todos_meses.append((año, mes))
            
            df_completo = pd.DataFrame(todos_meses, columns=['anio', 'mes'])
            df_mensual = pd.merge(df_completo, df_mensual, on=['anio', 'mes'], how='left')
            
            # Llenar valores faltantes con interpolación
            df_mensual = df_mensual.sort_values(['anio', 'mes'])
            df_mensual['cantidad'] = df_mensual['cantidad'].interpolate()
            df_mensual['cantidad'] = df_mensual['cantidad'].fillna(500)
            
            print(f"   ✅ Meses completados: {len(df_mensual)}/72")
        
        # Ordenar por tiempo
        df_mensual = df_mensual.sort_values(['anio', 'mes'])
        df_mensual['periodo'] = range(1, len(df_mensual) + 1)
        
        # ✅ CARACTERÍSTICAS OPTIMIZADAS
        # 1. Estacionalidad
        df_mensual['mes_sin'] = np.sin(2 * np.pi * (df_mensual['mes'] - 1) / 12)
        df_mensual['mes_cos'] = np.cos(2 * np.pi * (df_mensual['mes'] - 1) / 12)
        
        # 2. Tendencia
        df_mensual['tendencia'] = df_mensual['periodo']
        df_mensual['tendencia_cuad'] = df_mensual['periodo'] ** 2
        
        # 3. Eventos estacionales FUERTES
        df_mensual['navidad'] = (df_mensual['mes'] == 12).astype(int) * 2.0
        df_mensual['verano'] = df_mensual['mes'].isin([6, 7]).astype(int) * 1.5
        df_mensual['inicio_anio'] = df_mensual['mes'].isin([1, 2]).astype(int) * 0.5
        
        # 4. Lags simples
        df_mensual['lag_1'] = df_mensual['cantidad'].shift(1)
        df_mensual['lag_12'] = df_mensual['cantidad'].shift(12)
        
        # 5. Medias móviles
        df_mensual['media_3m'] = df_mensual['cantidad'].rolling(3, min_periods=1).mean()
        
        # Llenar NaN
        df_mensual = df_mensual.fillna(method='bfill').fillna(method='ffill')
        
        print(f"✅ Dataset final: {len(df_mensual)} meses")
        print(f"   • Cantidad promedio: {df_mensual['cantidad'].mean():.0f} productos/mes")
        print(f"   • Rango: {df_mensual['cantidad'].min():.0f} - {df_mensual['cantidad'].max():.0f}")
        
        return df_mensual
        
=======
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
# CARGA Y PREPARACIÓN
# ================================
def cargar_y_preparar_datos():
    """Carga y prepara datos asegurando 72 meses completos (2019-01 → 2024-12)."""
    print("📦 Cargando y validando datos...")

    try:
        # Cargar CSVs (ventas puede traer NaT por sintéticos)
        df_ventas = pd.read_csv("scikit_learn_ia/datasets/ventas.csv")
        df_detalles = pd.read_csv("scikit_learn_ia/datasets/detalles_venta.csv")

        print(f"   ✅ Ventas cargadas: {len(df_ventas)} registros")
        print(f"   ✅ Detalles cargados: {len(df_detalles)} registros")

        # Normalizar tiempo en ventas (fecha/anio/mes/periodo)
        df_ventas = add_periodo_fields(df_ventas)

        # Merge con detalles (inner asegura consistencia)
        df = pd.merge(
            df_detalles, df_ventas,
            left_on='venta_id', right_on='id',
            how='inner', suffixes=('_det', '')
        )

        # Normalizar post-merge por si se mezclan columnas
        df = add_periodo_fields(df)

        # Si detalles no trae 'cantidad', asumir 1
        if 'cantidad' not in df.columns:
            df['cantidad'] = 1

        # Agregado mensual: suma de ítems vendidos por mes (target = cantidad)
        df_mensual = (df
                      .groupby(['anio', 'mes', 'periodo'], as_index=False)
                      .agg(cantidad=('cantidad', 'sum')))

        # Asegurar índice mensual completo 2019-01 → 2024-12
        idx = pd.period_range('2019-01', '2024-12', freq='M')
        df_idx = pd.DataFrame({'periodo': [p.strftime('%Y-%m') for p in idx]})
        df_idx['anio'] = df_idx['periodo'].str[:4].astype(int)
        df_idx['mes']  = df_idx['periodo'].str[-2:].astype(int)

        df_mensual = df_idx.merge(df_mensual, on=['anio', 'mes', 'periodo'], how='left')

        # Interpolación segura + relleno si hubiera huecos
        df_mensual = df_mensual.sort_values(['anio', 'mes'])
        df_mensual['cantidad'] = (df_mensual['cantidad']
                                  .interpolate(method='linear', limit_direction='both'))
        # Si aún quedara NaN (todo vacío), poner base 500
        df_mensual['cantidad'] = df_mensual['cantidad'].fillna(500)

        # Validación 72/72
        print(f"   ✅ Meses obtenidos: {len(df_mensual)}/72")

        # Periodo numérico (1..72) para tendencia
        df_mensual['periodo_idx'] = np.arange(1, len(df_mensual) + 1)

        # ========= FEATURES OPTIMIZADAS =========
        # Estacionalidad (Fourier)
        df_mensual['mes_sin'] = np.sin(2 * np.pi * (df_mensual['mes'] - 1) / 12)
        df_mensual['mes_cos'] = np.cos(2 * np.pi * (df_mensual['mes'] - 1) / 12)

        # Tendencia
        df_mensual['tendencia'] = df_mensual['periodo_idx']
        df_mensual['tendencia_cuad'] = df_mensual['periodo_idx'] ** 2

        # Eventos estacionales fuertes
        df_mensual['navidad'] = (df_mensual['mes'] == 12).astype(int) * 2.0
        df_mensual['verano'] = df_mensual['mes'].isin([6, 7]).astype(int) * 1.5
        df_mensual['inicio_anio'] = df_mensual['mes'].isin([1, 2]).astype(int) * 0.5

        # Lags
        df_mensual['lag_1'] = df_mensual['cantidad'].shift(1)
        df_mensual['lag_12'] = df_mensual['cantidad'].shift(12)

        # Media móvil corta
        df_mensual['media_3m'] = df_mensual['cantidad'].rolling(3, min_periods=1).mean()

        # Relleno de NaN (bfill/ffill garantiza primeras filas)
        df_mensual = df_mensual.fillna(method='bfill').fillna(method='ffill')

        # Resumen dataset
        print(f"✅ Dataset final: {len(df_mensual)} meses")
        print(f"   • Cantidad promedio: {df_mensual['cantidad'].mean():.0f} productos/mes")
        print(f"   • Rango: {df_mensual['cantidad'].min():.0f} - {df_mensual['cantidad'].max():.0f}")

        return df_mensual

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        raise

<<<<<<< HEAD
def entrenar_modelo_definitivo():
    """Entrena modelo con configuración OPTIMIZADA"""
    print("🚀 ENTRENANDO MODELO DEFINITIVO")
    print("🎯 OBJETIVO: R² > 0.9")
    print("=" * 50)
    
    # 1. Cargar datos
    df_mensual = cargar_y_preparar_datos()
    
    # 2. Características OPTIMIZADAS
    features = [
        'mes_sin', 'mes_cos',           # Estacionalidad
        'tendencia', 'tendencia_cuad',  # Tendencia
        'navidad', 'verano', 'inicio_anio', # Eventos FUERTES
        'lag_1', 'lag_12',              # Patrones temporales
        'media_3m'                      # Tendencia corta
    ]
    
    X = df_mensual[features]
    y = df_mensual['cantidad']
    
=======
# ================================
# ENTRENAMIENTO
# ================================
def entrenar_modelo_definitivo():
    """Entrena modelo con configuración OPTIMIZADA."""
    print("🚀 ENTRENANDO MODELO DEFINITIVO")
    print("🎯 OBJETIVO: R² > 0.9")
    print("=" * 50)

    # 1) Cargar datos
    df_mensual = cargar_y_preparar_datos()

    # 2) Features
    features = [
        'mes_sin', 'mes_cos',            # Estacionalidad
        'tendencia', 'tendencia_cuad',   # Tendencia
        'navidad', 'verano', 'inicio_anio',  # Eventos
        'lag_1', 'lag_12',               # Lags
        'media_3m'                       # Media móvil
    ]
    X = df_mensual[features]
    y = df_mensual['cantidad']

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    print(f"🎯 CONFIGURACIÓN OPTIMIZADA:")
    print(f"   • Muestras: {len(X)} meses")
    print(f"   • Características: {len(features)}")
    print(f"   • Target: {y.mean():.0f} ± {y.std():.0f} productos/mes")
<<<<<<< HEAD
    
    # 3. División temporal (último año para test)
    X_train = X.iloc[:-12]
    X_test = X.iloc[-12:]
    y_train = y.iloc[:-12]
    y_test = y.iloc[-12:]
    
    print(f"   • Entrenamiento: {len(X_train)} meses")
    print(f"   • Prueba: {len(X_test)} meses (2024)")
    
    # 4. Modelo OPTIMIZADO
    print("🤖 Entrenando modelo optimizado...")
    
=======

    # 3) Split temporal: 2024 para test (últimos 12)
    X_train, X_test = X.iloc[:-12], X.iloc[-12:]
    y_train, y_test = y.iloc[:-12], y.iloc[-12:]

    # 4) Modelo
    print("🤖 Entrenando modelo optimizado...")
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    modelo = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=3,
        min_samples_leaf=1,
<<<<<<< HEAD
        random_state=42,
        n_jobs=-1
    )
    
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)
    
    # 5. Evaluación
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    error_porcentual = (mae / y_test.mean()) * 100
    precision = max(0, 100 - error_porcentual)
    
=======
        random_state=ModelConfig.RANDOM_STATE,
        n_jobs=-1
    )
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)

    # 5) Evaluación
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    error_porcentual = (mae / max(1e-9, y_test.mean())) * 100
    precision = max(0.0, 100.0 - error_porcentual)

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    print(f"\n📊 RESULTADOS DEFINITIVOS:")
    print(f"   • R² Score: {r2:.4f} ({r2*100:.1f}%)")
    print(f"   • MAE: {mae:.1f} productos ({error_porcentual:.1f}% error)")
    print(f"   • Precisión: {precision:.1f}%")
<<<<<<< HEAD
    
    # 6. Análisis de importancia
=======

    # 6) Importancias
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    importancia = pd.DataFrame({
        'feature': features,
        'importancia': modelo.feature_importances_
    }).sort_values('importancia', ascending=False)
<<<<<<< HEAD
    
    print(f"\n🎯 CARACTERÍSTICAS MÁS IMPORTANTES:")
    for i, row in importancia.iterrows():
        print(f"   {i+1:2d}. {row['feature']}: {row['importancia']:.3f}")
    
    # 7. Predicciones de ejemplo
    print(f"\n🔮 EJEMPLOS REAL vs PREDICHO:")
    for i in range(min(6, len(y_test))):
        real = y_test.iloc[i]
        pred = y_pred[i]
        error_pct = abs(real - pred) / real * 100
        
        mes = int(df_mensual.iloc[-12 + i]['mes'])
        anio = int(df_mensual.iloc[-12 + i]['anio'])
        
        print(f"   • {anio}-{mes:02d}: Real: {real:.0f} | Pred: {pred:.0f} | Error: {error_pct:.1f}%")
    
    # 8. Guardar SIEMPRE
    guardar_modelo(modelo, features, {
        'r2': r2, 
        'mae': mae, 
        'precision': precision,
        'error_porcentual': error_porcentual
    }, df_mensual)
    
=======

    print(f"\n🎯 CARACTERÍSTICAS MÁS IMPORTANTES:")
    for rank, (_, row) in enumerate(importancia.iterrows(), start=1):
        print(f"   {rank:2d}. {row['feature']}: {row['importancia']:.3f}")

    # 7) Ejemplos 2024: real vs predicho
    print(f"\n🔮 EJEMPLOS REAL vs PREDICHO (2024):")
    # Tomamos las últimas 12 filas en df_mensual para mostrar mes/año correctos
    tail = df_mensual.iloc[-12:].reset_index(drop=True)
    for i in range(len(tail)):
        real = float(y_test.iloc[i])
        pred = float(y_pred[i])
        error_pct = abs(real - pred) / max(1e-9, real) * 100
        anio_i = int(tail.loc[i, 'anio'])
        mes_i = int(tail.loc[i, 'mes'])
        print(f"   • {anio_i}-{mes_i:02d}: Real: {real:.0f} | Pred: {pred:.0f} | Error: {error_pct:.1f}%")

    # 8) Guardar
    guardar_modelo(modelo, features, {
        'r2': float(r2),
        'mae': float(mae),
        'precision': float(precision),
        'error_porcentual': float(error_porcentual)
    }, df_mensual)

    # Mensajes
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    if r2 > 0.9:
        print(f"\n🎉 ¡OBJETIVO SUPERADO! R² = {r2:.4f} (> 0.9)")
    elif r2 > 0.8:
        print(f"\n✅ Modelo de ALTA CALIDAD. R² = {r2:.4f}")
    else:
        print(f"\n⚠️  Modelo ACEPTABLE. R² = {r2:.4f}")
<<<<<<< HEAD
    
    print(f"🎯 Precisión del modelo: {precision:.1f}%")
    
    return modelo, r2, precision

def guardar_modelo(modelo, features, metricas, df_mensual):
    """Guarda el modelo y metadata"""
    print("💾 Guardando modelo...")
    
    os.makedirs(os.path.dirname(ModelConfig.MODEL_PATH), exist_ok=True)
    
    # Guardar modelo
    joblib.dump(modelo, ModelConfig.MODEL_PATH)
    
    # Calcular estadísticas adicionales
=======

    print(f"🎯 Precisión del modelo: {precision:.1f}%")

    return modelo, r2, precision

# ================================
# GUARDADO
# ================================
def guardar_modelo(modelo, features, metricas, df_mensual):
    """Guarda el modelo y metadata."""
    print("💾 Guardando modelo...")

    os.makedirs(os.path.dirname(ModelConfig.MODEL_PATH), exist_ok=True)

    # Guardar modelo
    joblib.dump(modelo, ModelConfig.MODEL_PATH)

    # Patrones estacionales (prom/SD por mes)
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    estadisticas_mensuales = df_mensual.groupby('mes')['cantidad'].agg(['mean', 'std']).round(0)
    patrones_estacionales = {
        int(mes): {
            'promedio': int(estadisticas_mensuales.loc[mes, 'mean']),
            'desviacion': int(estadisticas_mensuales.loc[mes, 'std'])
        }
        for mes in estadisticas_mensuales.index
    }
<<<<<<< HEAD
    
    metadata = {
        'fecha_entrenamiento': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
        'metricas': metricas,
        'caracteristicas': features,
        'configuracion': {
            'muestras': len(df_mensual),
            'rango_fechas': f"{df_mensual['anio'].min()}-{df_mensual['mes'].min():02d} a {df_mensual['anio'].max()}-{df_mensual['mes'].max():02d}",
=======

    # Rango de fechas amigable
    rango_fechas = f"{int(df_mensual['anio'].min())}-{int(df_mensual['mes'].min()):02d} a " \
                   f"{int(df_mensual['anio'].max())}-{int(df_mensual['mes'].max()):02d}"

    metadata = {
        'fecha_entrenamiento': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S UTC'),
        'metricas': metricas,
        'caracteristicas': features,
        'configuracion': {
            'muestras': int(len(df_mensual)),
            'rango_fechas': rango_fechas,
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
            'cantidad_promedio': float(df_mensual['cantidad'].mean()),
            'cantidad_min': float(df_mensual['cantidad'].min()),
            'cantidad_max': float(df_mensual['cantidad'].max()),
            'desviacion_estandar': float(df_mensual['cantidad'].std()),
            'patrones_estacionales': patrones_estacionales
        },
        'version': '8.0_funcional'
    }
<<<<<<< HEAD
    
    with open(ModelConfig.METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Modelo guardado: {ModelConfig.MODEL_PATH}")
    print(f"   ✅ Metadata guardada: {ModelConfig.METADATA_PATH}")
    
=======

    with open(ModelConfig.METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"   ✅ Modelo guardado: {ModelConfig.MODEL_PATH}")
    print(f"   ✅ Metadata guardada: {ModelConfig.METADATA_PATH}")

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    # Mostrar resumen de patrones
    print(f"\n🎯 PATRONES ESTACIONALES DETECTADOS:")
    meses_altos = df_mensual.groupby('mes')['cantidad'].mean().nlargest(3)
    meses_bajos = df_mensual.groupby('mes')['cantidad'].mean().nsmallest(3)
<<<<<<< HEAD
    
    print(f"   • Meses ALTOS: {', '.join([f'{int(m)}° ({int(v)})' for m, v in meses_altos.items()])}")
    print(f"   • Meses BAJOS: {', '.join([f'{int(m)}° ({int(v)})' for m, v in meses_bajos.items()])}")

# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================
=======
    print(f"   • Meses ALTOS: {', '.join([f'{int(m)}° ({int(v)})' for m, v in meses_altos.items()])}")
    print(f"   • Meses BAJOS: {', '.join([f'{int(m)}° ({int(v)})' for m, v in meses_bajos.items()])}")

# ================================
# MAIN
# ================================
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
if __name__ == "__main__":
    print("🎯 INICIANDO SISTEMA DE ENTRENAMIENTO")
    print("🎯 OBJETIVO: R² > 0.9 (90%+ confianza)")
    print("=" * 60)
<<<<<<< HEAD
    
    try:
        modelo, r2, precision = entrenar_modelo_definitivo()
        
=======

    try:
        modelo, r2, precision = entrenar_modelo_definitivo()

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        if modelo is not None:
            print(f"\n✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
            print(f"🎯 Modelo listo para predicciones")
        else:
            print(f"\n⚠️  Entrenamiento completado con advertencias")
<<<<<<< HEAD
            
=======

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    except Exception as e:
        print(f"\n❌ ERROR DURANTE EL ENTRENAMIENTO:")
        print(f"   {e}")
        import traceback
<<<<<<< HEAD
        traceback.print_exc()
=======
        traceback.print_exc()
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
