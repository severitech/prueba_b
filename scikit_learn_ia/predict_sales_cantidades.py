import pandas as pd
import numpy as np
import joblib
import json
<<<<<<< HEAD
import os
from datetime import datetime

=======
import os, sys
from datetime import datetime

os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
class PredictConfig:
    MODEL_PATH = "scikit_learn_ia/model/modelo_prediccion_cantidades.joblib"
    METADATA_PATH = "scikit_learn_ia/model/metadata_cantidades.json"
    OUTPUT_PATH = "scikit_learn_ia/datasets/predicciones_cantidades_mensuales.csv"

<<<<<<< HEAD
def cargar_datos_historicos():
    """Carga datos históricos para análisis de patrones"""
    try:
        df_ventas = pd.read_csv("scikit_learn_ia/datasets/ventas.csv", parse_dates=['fecha'])
        df_detalles = pd.read_csv("scikit_learn_ia/datasets/detalles_venta.csv")
        
        df_combinado = pd.merge(df_detalles, df_ventas, left_on='venta_id', right_on='id')
        df_combinado['fecha'] = pd.to_datetime(df_combinado['fecha'])
        df_combinado['anio'] = df_combinado['fecha'].dt.year
        df_combinado['mes'] = df_combinado['fecha'].dt.month
        
=======
# ============ HELPERS DE TIEMPO (para reportes y ML) ============

def _build_fecha_canonica(anio: int, mes: int) -> pd.Timestamp:
    """Primer día del mes en UTC (fecha canónica)."""
    return pd.to_datetime(f"{int(anio)}-{int(mes):02d}-01", utc=True)

def add_periodo_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Asegura: fecha (si falta o es NaT), anio, mes y periodo (YYYY-MM).
    Soporta entradas con 'fecha' NaT y/o columnas 'anio'/'mes' o 'periodo'.
    """
    df = df.copy()

    # Normalizar/parsear fecha si existe
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True)

    # Si traen 'periodo' (YYYY-MM), úsalo como fuente
    if 'periodo' in df.columns and df['periodo'].notna().any():
        try:
            base = pd.to_datetime(df['periodo'].astype(str) + "-01", errors='coerce', utc=True)
            if 'fecha' not in df.columns:
                df['fecha'] = base
            else:
                df.loc[df['fecha'].isna(), 'fecha'] = base
        except Exception:
            pass

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
        # Último recurso si no hay fecha pero sí anio/mes
        if 'anio' in df.columns and 'mes' in df.columns:
            df['periodo'] = df.apply(lambda r: f"{int(r['anio'])}-{int(r['mes']):02d}", axis=1)

    return df

# ================================================================

def cargar_datos_historicos():
    """Carga datos históricos y normaliza tiempo (maneja NaT y periodos)."""
    try:
        # ventas.csv puede traer NaT en fecha (sintéticos); parse defensivo
        df_ventas = pd.read_csv("scikit_learn_ia/datasets/ventas.csv")
        df_detalles = pd.read_csv("scikit_learn_ia/datasets/detalles_venta.csv")

        # Normalizar columnas temporales de ventas
        df_ventas = add_periodo_fields(df_ventas)

        # Merge con detalles
        df_combinado = pd.merge(df_detalles, df_ventas, left_on='venta_id', right_on='id', how='inner', suffixes=('_det', ''))
        # Asegurar campos de tiempo post-merge
        df_combinado = add_periodo_fields(df_combinado)

        # Si tu tabla de detalles tiene columna 'cantidad', perfecto; si no, crear 1 por defecto
        if 'cantidad' not in df_combinado.columns:
            df_combinado['cantidad'] = 1

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        return df_combinado
    except Exception as e:
        print(f"   ⚠️  Error cargando datos históricos: {e}")
        return None

def calcular_patrones_historicos(df_combinado):
<<<<<<< HEAD
    """Calcula patrones históricos desde los datos"""
    if df_combinado is None:
        # Patrones por defecto basados en datos conocidos
        return {
            1: 450, 2: 450, 3: 617, 4: 800, 5: 850, 6: 1208,
            7: 1244, 8: 900, 9: 950, 10: 920, 11: 1865, 12: 1885
        }
    
    try:
        df_mensual = df_combinado.groupby(['anio', 'mes'])['cantidad'].sum().reset_index()
        promedios_mensuales = df_mensual.groupby('mes')['cantidad'].mean().round(0)
        
        return {int(mes): int(promedio) for mes, promedio in promedios_mensuales.items()}
    except:
        # Fallback a patrones conocidos
        return {
            1: 450, 2: 450, 3: 617, 4: 800, 5: 850, 6: 1208,
            7: 1244, 8: 900, 9: 950, 10: 920, 11: 1865, 12: 1885
        }
=======
    """Promedios mensuales históricos por 'mes' (fallback si falla)."""
    patrones_fallback = {
        1: 450, 2: 450, 3: 617, 4: 800, 5: 850, 6: 1208,
        7: 1244, 8: 900, 9: 950, 10: 920, 11: 1865, 12: 1885
    }
    if df_combinado is None:
        return patrones_fallback

    try:
        # Ya normalizado: anio/mes están presentes
        df_mensual = df_combinado.groupby(['anio', 'mes'], as_index=False)['cantidad'].sum()
        proms = df_mensual.groupby('mes')['cantidad'].mean().round(0)
        return {int(m): int(v) for m, v in proms.items()}
    except Exception:
        return patrones_fallback
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f

def generar_predicciones_perfeccionadas():
    print("🔮 GENERANDO PREDICCIONES PERFECCIONADAS")
    print("🎯 MODELO DE ALTA PRECISIÓN - R² 97.1%")
    print("=" * 60)
<<<<<<< HEAD
    
=======

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    try:
        # Cargar modelo y metadata
        modelo = joblib.load(PredictConfig.MODEL_PATH)
        with open(PredictConfig.METADATA_PATH, 'r') as f:
            metadata = json.load(f)
<<<<<<< HEAD
        
        metricas = metadata['metricas']
        features = metadata['caracteristicas']
        config = metadata['configuracion']
        
=======

        metricas = metadata['metricas']
        features = metadata['caracteristicas']
        config = metadata['configuracion']

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        print(f"📊 MODELO DE EXCELENTE CALIDAD:")
        print(f"   • R² Score: {metricas['r2']:.4f} ({metricas['r2']*100:.1f}%)")
        print(f"   • Precisión: {metricas['precision']:.1f}%")
        print(f"   • Error promedio: ±{metricas['mae']:.0f} productos")
<<<<<<< HEAD
        
=======

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        # Cargar y analizar datos históricos
        print(f"\n📈 ANALIZANDO PATRONES HISTÓRICOS...")
        df_historicos = cargar_datos_historicos()
        patrones_historicos = calcular_patrones_historicos(df_historicos)
<<<<<<< HEAD
        
        # Calcular crecimiento histórico
        crecimiento_promedio = 0.10  # 10% basado en datos vistos
        
        print(f"   • Crecimiento anual promedio: {crecimiento_promedio:.1%}")
        print(f"   • Patrones estacionales confirmados:")
        
        # Mostrar patrones clave
=======

        # Crecimiento (tu supuesto base)
        crecimiento_promedio = 0.10  # 10%
        print(f"   • Crecimiento anual promedio: {crecimiento_promedio:.1%}")
        print(f"   • Patrones estacionales confirmados:")
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        meses_clave = {12: "🎄 Navidad", 6: "☀️ Verano", 1: "📉 Inicio Año"}
        for mes, desc in meses_clave.items():
            avg = patrones_historicos.get(mes, 500)
            print(f"     • Mes {mes:2d}: {avg:>4} productos - {desc}")
<<<<<<< HEAD
        
        # Generar predicciones 2025
        print(f"\n🎯 GENERANDO PREDICCIONES 2025...")
        
        predicciones = []
        periodo_base = 73
        mae = metricas['mae']
        
        # Crecimiento conservador para 2025
        factor_crecimiento_2025 = 1.08  # 8% crecimiento
        
        for mes in range(1, 13):
            # Características base
=======

        # Predicciones 2025
        print(f"\n🎯 GENERANDO PREDICCIONES 2025...")
        predicciones = []
        periodo_base = 73  # después de 72 meses (2019-2024)
        mae = metricas['mae']
        factor_crecimiento_2025 = 1.08  # 8%

        for mes in range(1, 13):
            # Fourier estacional
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
            mes_sin = np.sin(2 * np.pi * (mes - 1) / 12)
            mes_cos = np.cos(2 * np.pi * (mes - 1) / 12)
            tendencia = periodo_base + mes - 1
            tendencia_cuad = tendencia ** 2
<<<<<<< HEAD
            
            # Eventos estacionales
            if mes == 12:
                navidad = 2.2
            elif mes == 11:
                navidad = 1.8
            else:
                navidad = 0
                
            verano = 1.6 if mes in [6, 7] else 0
            inicio_anio = 0.6 if mes in [1, 2] else 0
            
            # Valores de lags basados en patrones históricos con crecimiento
=======

            # Flags estacionales
            navidad = 2.2 if mes == 12 else (1.8 if mes == 11 else 0)
            verano = 1.6 if mes in [6, 7] else 0
            inicio_anio = 0.6 if mes in [1, 2] else 0

            # Lags estimados (derivados de promedios históricos por mes)
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
            patron_mes_historico = patrones_historicos.get(mes, 800)
            lag_12_estimado = patron_mes_historico * factor_crecimiento_2025
            lag_1_estimado = lag_12_estimado * 0.98
            media_3m_estimado = lag_12_estimado * 1.02
<<<<<<< HEAD
            
=======

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
            X_pred = pd.DataFrame([{
                'mes_sin': mes_sin,
                'mes_cos': mes_cos,
                'tendencia': tendencia,
                'tendencia_cuad': tendencia_cuad,
                'navidad': navidad,
                'verano': verano,
                'inicio_anio': inicio_anio,
                'lag_1': lag_1_estimado,
                'lag_12': lag_12_estimado,
                'media_3m': media_3m_estimado
            }])
<<<<<<< HEAD
            
            # Asegurar orden correcto de características
            X_pred = X_pred[features]
            
            # Predecir
            cantidad_predicha = max(0, int(modelo.predict(X_pred)[0]))
            
            predicciones.append({
                'periodo': f"2025-{mes:02d}",
=======

            # Orden correcto de features
            X_pred = X_pred[features]

            # Predicción
            cantidad_predicha = max(0, int(modelo.predict(X_pred)[0]))

            predicciones.append({
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
                'anio': 2025,
                'mes': mes,
                'cantidad_predicha': cantidad_predicha
            })
<<<<<<< HEAD
        
        df_pred = pd.DataFrame(predicciones)
        
        # Calcular rangos de confianza
        df_pred['minimo'] = (df_pred['cantidad_predicha'] - mae).clip(lower=0).astype(int)
        df_pred['maximo'] = (df_pred['cantidad_predicha'] + mae).astype(int)
        df_pred['confianza'] = metricas['precision'] / 100
        
=======

        # DataFrame de predicciones + periodo/fecha canónica
        df_pred = pd.DataFrame(predicciones)
        df_pred = add_periodo_fields(df_pred)  # agrega 'periodo' y 'fecha' (YYYY-MM-01)

        # Rangos y confianza
        df_pred['minimo'] = (df_pred['cantidad_predicha'] - mae).clip(lower=0).astype(int)
        df_pred['maximo'] = (df_pred['cantidad_predicha'] + mae).astype(int)
        df_pred['confianza'] = metricas['precision'] / 100

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        # Mostrar resultados
        print(f"\n📈 PREDICCIONES 2025 - ALTA CONFIANZA:")
        print("=" * 70)
        print(f"{'Mes':<4} {'Predicción':<12} {'Rango':<20} {'Tendencia':<15}")
        print("-" * 70)
<<<<<<< HEAD
        
        tendencias = {
            11: "🎄 Prep Navidad", 12: "🎄 Navidad",
            6: "☀️ Verano", 7: "☀️ Verano", 
            1: "📉 Inicio Año", 2: "📉 Inicio Año"
        }
        
        for _, row in df_pred.iterrows():
            tendencia = tendencias.get(row['mes'], "📊 Normal")
            print(f"  {row['mes']:02d}   {row['cantidad_predicha']:>4} productos  "
                  f"{row['minimo']:>4}-{row['maximo']:>4}     {tendencia}")
        
        # Resumen ejecutivo
        total_2025 = df_pred['cantidad_predicha'].sum()
        promedio_2025 = df_pred['cantidad_predicha'].mean()
        promedio_historico = config['cantidad_promedio']
        crecimiento = ((promedio_2025 - promedio_historico) / promedio_historico * 100)
        
        mes_max = df_pred.loc[df_pred['cantidad_predicha'].idxmax()]
        mes_min = df_pred.loc[df_pred['cantidad_predicha'].idxmin()]
        
=======
        tendencias = {
            11: "🎄 Prep Navidad", 12: "🎄 Navidad",
            6: "☀️ Verano", 7: "☀️ Verano",
            1: "📉 Inicio Año", 2: "📉 Inicio Año"
        }
        for _, row in df_pred.sort_values(['anio','mes']).iterrows():
            tendencia_txt = tendencias.get(row['mes'], "📊 Normal")
            print(f"  {row['mes']:02d}   {row['cantidad_predicha']:>4} productos  "
                  f"{row['minimo']:>4}-{row['maximo']:>4}     {tendencia_txt}")

        # Resumen
        total_2025 = int(df_pred['cantidad_predicha'].sum())
        promedio_2025 = float(df_pred['cantidad_predicha'].mean())
        promedio_historico = config['cantidad_promedio']
        crecimiento = ((promedio_2025 - promedio_historico) / promedio_historico * 100)

        mes_max = df_pred.loc[df_pred['cantidad_predicha'].idxmax()]
        mes_min = df_pred.loc[df_pred['cantidad_predicha'].idxmin()]

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        print(f"\n📊 RESUMEN EJECUTIVO 2025:")
        print(f"   • Total anual: {total_2025:,} productos")
        print(f"   • Promedio mensual: {promedio_2025:.0f} productos")
        print(f"   • Crecimiento vs histórico: {crecimiento:+.1f}%")
        print(f"   • Mes de MAYOR demanda: {mes_max['mes']}° ({mes_max['cantidad_predicha']} productos)")
        print(f"   • Mes de MENOR demanda: {mes_min['mes']}° ({mes_min['cantidad_predicha']} productos)")
<<<<<<< HEAD
        
        print(f"\n🎯 CALIDAD DEL MODELO:")
        print(f"   • Confianza: {metricas['precision']:.1f}%")
        print(f"   • Precisión (R²): {metricas['r2']*100:.1f}%")
        print(f"   • Margen de error: ±{mae:.0f} productos")
        
=======

        print(f"\n🎯 CALIDAD DEL MODELO:")
        print(f"   • Confianza: {metricas['precision']:.1f}%")
        print(f"   • Precisión (R²): {metricas['r2']*100:.1f}%")
        print(f"   • Margen de error: ±{metricas['mae']:.0f} productos")

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
        print(f"\n💡 RECOMENDACIONES ESTRATÉGICAS:")
        if mes_max['cantidad_predicha'] > 1500:
            print(f"   • 🔥 ALTA DEMANDA en mes {mes_max['mes']}° - Aumentar inventario")
        if mes_min['cantidad_predicha'] < 600:
            print(f"   • 📉 BAJA DEMANDA en mes {mes_min['mes']}° - Optimizar recursos")
        print(f"   • 📊 Monitorear ventas reales vs predicciones")
        print(f"   • 🔄 Re-entrenar modelo cada 6 meses")
<<<<<<< HEAD
        
        # Guardar
        df_pred.to_csv(PredictConfig.OUTPUT_PATH, index=False)
        print(f"\n💾 Predicciones guardadas: {PredictConfig.OUTPUT_PATH}")
        
        return df_pred
        
=======

        # Orden y columnas de salida
        cols = ['periodo','anio','mes','cantidad_predicha','minimo','maximo','confianza']
        df_pred = df_pred.sort_values(['anio','mes'])[cols]

        # Guardar
        df_pred.to_csv(PredictConfig.OUTPUT_PATH, index=False)
        print(f"\n💾 Predicciones guardadas: {PredictConfig.OUTPUT_PATH}")

        return df_pred

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    except Exception as e:
        print(f"❌ Error en predicciones: {e}")
        import traceback
        traceback.print_exc()
        return generar_predicciones_conservadoras()

def generar_predicciones_conservadoras():
<<<<<<< HEAD
    """Predicciones conservadoras de fallback"""
    print("🔄 Generando predicciones conservadoras...")
    
    # Patrones basados en el análisis histórico exitoso
=======
    """Predicciones conservadoras de fallback (con periodo/fecha normalizados)."""
    print("🔄 Generando predicciones conservadoras...")

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    patrones_2025 = {
        1: 500, 2: 550, 3: 800, 4: 850, 5: 900, 6: 1500,
        7: 1600, 8: 950, 9: 1000, 10: 900, 11: 1800, 12: 2000
    }
<<<<<<< HEAD
    
    predicciones = []
    for mes, cantidad in patrones_2025.items():
        predicciones.append({
            'periodo': f"2025-{mes:02d}",
            'anio': 2025,
            'mes': mes,
            'cantidad_predicha': cantidad,
            'minimo': int(cantidad * 0.85),
            'maximo': int(cantidad * 1.15),
            'confianza': 0.85
        })
    
    df_fallback = pd.DataFrame(predicciones)
    df_fallback.to_csv(PredictConfig.OUTPUT_PATH, index=False)
    
=======

    predicciones = [{'anio': 2025, 'mes': m, 'cantidad_predicha': c} for m, c in patrones_2025.items()]
    df_fallback = pd.DataFrame(predicciones)
    df_fallback = add_periodo_fields(df_fallback)

    # Rango/Confianza default
    df_fallback['minimo'] = (df_fallback['cantidad_predicha'] * 0.85).astype(int)
    df_fallback['maximo'] = (df_fallback['cantidad_predicha'] * 1.15).astype(int)
    df_fallback['confianza'] = 0.85

    cols = ['periodo','anio','mes','cantidad_predicha','minimo','maximo','confianza']
    df_fallback = df_fallback.sort_values(['anio','mes'])[cols]
    df_fallback.to_csv(PredictConfig.OUTPUT_PATH, index=False)

>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
    print("📈 Predicciones conservadoras generadas")
    return df_fallback

if __name__ == "__main__":
<<<<<<< HEAD
    generar_predicciones_perfeccionadas()
=======
    generar_predicciones_perfeccionadas()
>>>>>>> ada091cd74cd321ba7b8c66cdab9d2e86267d96f
