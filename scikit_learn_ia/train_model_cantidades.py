# scikit_learn_ia/train_model_cantidades.py
import pandas as pd
import numpy as np
import joblib
import json
import os, sys
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# 🛣️ Rutas unificadas (local / Railway) + banner de diagnóstico
from scikit_learn_ia.paths import (
    DATA_DIR, MODEL_DIR,
    VENTAS_CSV, DETALLES_CSV,
    MODEL_CANTIDADES, METADATA_CANT,
    print_paths_banner
)

# Forzar UTF-8 en Windows/PowerShell
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

class ModelConfig:
    RANDOM_STATE = 42
    MODEL_PATH   = MODEL_CANTIDADES          # scikit_learn_ia/model/modelo_prediccion_cantidades.joblib
    METADATA_PATH= METADATA_CANT             # scikit_learn_ia/model/metadata_cantidades.json

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
# CARGA Y PREPARACIÓN
# ================================
def cargar_y_preparar_datos():
    """Carga y prepara datos asegurando 72 meses completos (2019-01 → 2024-12)."""
    print_paths_banner("🔍 Ejecutando train_model_cantidades.py")
    print("📦 Cargando y validando datos...")

    try:
        df_ventas   = pd.read_csv(VENTAS_CSV)
        df_detalles = pd.read_csv(DETALLES_CSV)

        print(f"   ✅ Ventas cargadas: {len(df_ventas)} registros")
        print(f"   ✅ Detalles cargados: {len(df_detalles)} registros")

        df_ventas = add_periodo_fields(df_ventas)

        df = pd.merge(
            df_detalles, df_ventas,
            left_on='venta_id', right_on='id',
            how='inner', suffixes=('_det', '')
        )
        df = add_periodo_fields(df)

        if 'cantidad' not in df.columns:
            df['cantidad'] = 1

        df_mensual = (df
                      .groupby(['anio', 'mes', 'periodo'], as_index=False)
                      .agg(cantidad=('cantidad', 'sum')))

        idx = pd.period_range('2019-01', '2024-12', freq='M')
        df_idx = pd.DataFrame({'periodo': [p.strftime('%Y-%m') for p in idx]})
        df_idx['anio'] = df_idx['periodo'].str[:4].astype(int)
        df_idx['mes']  = df_idx['periodo'].str[-2:].astype(int)
        df_mensual = df_idx.merge(df_mensual, on=['anio', 'mes', 'periodo'], how='left')

        df_mensual = df_mensual.sort_values(['anio', 'mes'])
        df_mensual['cantidad'] = (df_mensual['cantidad']
                                  .interpolate(method='linear', limit_direction='both'))
        df_mensual['cantidad'] = df_mensual['cantidad'].fillna(500)

        print(f"   ✅ Meses obtenidos: {len(df_mensual)}/72")

        df_mensual['periodo_idx'] = np.arange(1, len(df_mensual) + 1)

        # FEATURES
        df_mensual['mes_sin'] = np.sin(2 * np.pi * (df_mensual['mes'] - 1) / 12)
        df_mensual['mes_cos'] = np.cos(2 * np.pi * (df_mensual['mes'] - 1) / 12)
        df_mensual['tendencia'] = df_mensual['periodo_idx']
        df_mensual['tendencia_cuad'] = df_mensual['periodo_idx'] ** 2
        df_mensual['navidad'] = (df_mensual['mes'] == 12).astype(int) * 2.0
        df_mensual['verano'] = df_mensual['mes'].isin([6, 7]).astype(int) * 1.5
        df_mensual['inicio_anio'] = df_mensual['mes'].isin([1, 2]).astype(int) * 0.5
        df_mensual['lag_1'] = df_mensual['cantidad'].shift(1)
        df_mensual['lag_12'] = df_mensual['cantidad'].shift(12)
        df_mensual['media_3m'] = df_mensual['cantidad'].rolling(3, min_periods=1).mean()

        df_mensual = df_mensual.fillna(method='bfill').fillna(method='ffill')

        print(f"✅ Dataset final: {len(df_mensual)} meses")
        print(f"   • Cantidad promedio: {df_mensual['cantidad'].mean():.0f} productos/mes")
        print(f"   • Rango: {df_mensual['cantidad'].min():.0f} - {df_mensual['cantidad'].max():.0f}")

        return df_mensual

    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        raise

# ================================
# ENTRENAMIENTO
# ================================
def entrenar_modelo_definitivo():
    """Entrena modelo con configuración OPTIMIZADA."""
    print("🚀 ENTRENANDO MODELO DEFINITIVO")
    print("🎯 OBJETIVO: R² > 0.9")
    print("=" * 50)

    df_mensual = cargar_y_preparar_datos()

    features = [
        'mes_sin', 'mes_cos',
        'tendencia', 'tendencia_cuad',
        'navidad', 'verano', 'inicio_anio',
        'lag_1', 'lag_12',
        'media_3m'
    ]
    X = df_mensual[features]
    y = df_mensual['cantidad']

    print(f"🎯 CONFIGURACIÓN OPTIMIZADA:")
    print(f"   • Muestras: {len(X)} meses")
    print(f"   • Características: {len(features)}")
    print(f"   • Target: {y.mean():.0f} ± {y.std():.0f} productos/mes")

    X_train, X_test = X.iloc[:-12], X.iloc[-12:]
    y_train, y_test = y.iloc[:-12], y.iloc[-12:]

    print("🤖 Entrenando modelo optimizado...")
    modelo = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=3,
        min_samples_leaf=1,
        random_state=ModelConfig.RANDOM_STATE,
        n_jobs=-1
    )
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    error_porcentual = (mae / max(1e-9, y_test.mean())) * 100
    precision = max(0.0, 100.0 - error_porcentual)

    print(f"\n📊 RESULTADOS DEFINITIVOS:")
    print(f"   • R² Score: {r2:.4f} ({r2*100:.1f}%)")
    print(f"   • MAE: {mae:.1f} productos ({error_porcentual:.1f}% error)")
    print(f"   • Precisión: {precision:.1f}%")

    importancia = pd.DataFrame({
        'feature': features,
        'importancia': modelo.feature_importances_
    }).sort_values('importancia', ascending=False)

    print(f"\n🎯 CARACTERÍSTICAS MÁS IMPORTANTES:")
    for rank, (_, row) in enumerate(importancia.iterrows(), start=1):
        print(f"   {rank:2d}. {row['feature']}: {row['importancia']:.3f}")

    print(f"\n🔮 EJEMPLOS REAL vs PREDICHO (2024):")
    tail = df_mensual.iloc[-12:].reset_index(drop=True)
    for i in range(len(tail)):
        real = float(y_test.iloc[i])
        pred = float(y_pred[i])
        error_pct = abs(real - pred) / max(1e-9, real) * 100
        anio_i = int(tail.loc[i, 'anio'])
        mes_i = int(tail.loc[i, 'mes'])
        print(f"   • {anio_i}-{mes_i:02d}: Real: {real:.0f} | Pred: {pred:.0f} | Error: {error_pct:.1f}%")

    guardar_modelo(modelo, features, {
        'r2': float(r2),
        'mae': float(mae),
        'precision': float(precision),
        'error_porcentual': float(error_porcentual)
    }, df_mensual)

    if r2 > 0.9:
        print(f"\n🎉 ¡OBJETIVO SUPERADO! R² = {r2:.4f} (> 0.9)")
    elif r2 > 0.8:
        print(f"\n✅ Modelo de ALTA CALIDAD. R² = {r2:.4f}")
    else:
        print(f"\n⚠️  Modelo ACEPTABLE. R² = {r2:.4f}")

    print(f"🎯 Precisión del modelo: {precision:.1f}%")
    return modelo, r2, precision

# ================================
# GUARDADO
# ================================
def guardar_modelo(modelo, features, metricas, df_mensual):
    """Guarda el modelo y metadata en MODEL_DIR (sobrescribe)."""
    print("💾 Guardando modelo...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)  # asegura carpeta

    joblib.dump(modelo, ModelConfig.MODEL_PATH)

    estadisticas_mensuales = df_mensual.groupby('mes')['cantidad'].agg(['mean', 'std']).round(0)
    patrones_estacionales = {
        int(mes): {
            'promedio': int(estadisticas_mensuales.loc[mes, 'mean']),
            'desviacion': int(estadisticas_mensuales.loc[mes, 'std'])
        }
        for mes in estadisticas_mensuales.index
    }

    rango_fechas = f"{int(df_mensual['anio'].min())}-{int(df_mensual['mes'].min()):02d} a " \
                   f"{int(df_mensual['anio'].max())}-{int(df_mensual['mes'].max()):02d}"

    metadata = {
        'fecha_entrenamiento': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S UTC'),
        'metricas': metricas,
        'caracteristicas': features,
        'configuracion': {
            'muestras': int(len(df_mensual)),
            'rango_fechas': rango_fechas,
            'cantidad_promedio': float(df_mensual['cantidad'].mean()),
            'cantidad_min': float(df_mensual['cantidad'].min()),
            'cantidad_max': float(df_mensual['cantidad'].max()),
            'desviacion_estandar': float(df_mensual['cantidad'].std()),
            'patrones_estacionales': patrones_estacionales
        },
        'version': '8.0_funcional'
    }

    with open(ModelConfig.METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"   ✅ Modelo guardado: {ModelConfig.MODEL_PATH}")
    print(f"   ✅ Metadata guardada: {ModelConfig.METADATA_PATH}")

    print(f"\n🎯 PATRONES ESTACIONALES DETECTADOS:")
    meses_altos = df_mensual.groupby('mes')['cantidad'].mean().nlargest(3)
    meses_bajos = df_mensual.groupby('mes')['cantidad'].mean().nsmallest(3)
    print(f"   • Meses ALTOS: {', '.join([f'{int(m)}° ({int(v)})' for m, v in meses_altos.items()])}")
    print(f"   • Meses BAJOS: {', '.join([f'{int(m)}° ({int(v)})' for m, v in meses_bajos.items()])}")

# ================================
# MAIN
# ================================
if __name__ == "__main__":
    print("🎯 INICIANDO SISTEMA DE ENTRENAMIENTO")
    print("🎯 OBJETIVO: R² > 0.9 (90%+ confianza)")
    print("=" * 60)
    try:
        modelo, r2, precision = entrenar_modelo_definitivo()
        if modelo is not None:
            print("\n✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
            print("🎯 Modelo listo para predicciones")
        else:
            print("\n⚠️  Entrenamiento completado con advertencias")
    except Exception as e:
        print("\n❌ ERROR DURANTE EL ENTRENAMIENTO:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
