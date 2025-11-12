# scikit_learn_ia/predict_sales_cantidades.py
import pandas as pd
import numpy as np
import joblib
import json
import os, sys
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# 🛣️ Rutas unificadas + banner (local/Railway)
from scikit_learn_ia.paths import (
    DATA_DIR, MODEL_DIR,
    VENTAS_CSV, DETALLES_CSV,
    MODEL_CANTIDADES, METADATA_CANT, PRED_TOTALES_CSV,
    print_paths_banner
)

# Forzar UTF-8 para Windows/PowerShell
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ===================== Helpers de tiempo =====================
def _build_fecha_canonica(anio: int, mes: int) -> pd.Timestamp:
    """Primer día del mes en UTC (fecha canónica)."""
    return pd.to_datetime(f"{int(anio)}-{int(mes):02d}-01", utc=True)

def add_periodo_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Asegura: fecha (UTC), anio, mes y periodo (YYYY-MM).
    Tolera NaT y/o entradas con 'periodo'.
    """
    df = df.copy()

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", utc=True)

    if "periodo" in df.columns and df["periodo"].notna().any():
        base = pd.to_datetime(df["periodo"].astype(str) + "-01", errors="coerce", utc=True)
        if "fecha" not in df.columns:
            df["fecha"] = base
        else:
            df.loc[df["fecha"].isna(), "fecha"] = base

    if ("anio" not in df.columns or "mes" not in df.columns) and "fecha" in df.columns:
        df["anio"] = df["fecha"].dt.year
        df["mes"]  = df["fecha"].dt.month

    if "anio" in df.columns and "mes" in df.columns:
        if "fecha" not in df.columns:
            df["fecha"] = [
                _build_fecha_canonica(a, m) if pd.notna(a) and pd.notna(m) else pd.NaT
                for a, m in zip(df["anio"], df["mes"])
            ]
        else:
            mask = df["fecha"].isna() & df["anio"].notna() & df["mes"].notna()
            df.loc[mask, "fecha"] = [
                _build_fecha_canonica(a, m) for a, m in zip(df.loc[mask, "anio"], df.loc[mask, "mes"])
            ]

    if "fecha" in df.columns:
        df["anio"]    = df["fecha"].dt.year
        df["mes"]     = df["fecha"].dt.month
        df["periodo"] = df["fecha"].dt.strftime("%Y-%m")
    else:
        if "anio" in df.columns and "mes" in df.columns:
            df["periodo"] = df.apply(lambda r: f"{int(r['anio'])}-{int(r['mes']):02d}", axis=1)

    return df


# ===================== Carga histórica =====================
def cargar_datos_historicos():
    """Carga ventas/detalles y normaliza tiempo."""
    try:
        df_ventas   = pd.read_csv(VENTAS_CSV)
        df_detalles = pd.read_csv(DETALLES_CSV)

        df_ventas = add_periodo_fields(df_ventas)

        df = pd.merge(
            df_detalles, df_ventas,
            left_on="venta_id", right_on="id",
            how="inner", suffixes=("_det", "")
        )
        df = add_periodo_fields(df)

        if "cantidad" not in df.columns:
            df["cantidad"] = 1

        return df
    except Exception as e:
        print(f"⚠️  Error cargando datos históricos: {e}")
        return None

def calcular_patrones_historicos(df_combinado):
    """Promedios mensuales históricos (fallback robusto)."""
    fallback = {1:450, 2:450, 3:617, 4:800, 5:850, 6:1208, 7:1244, 8:900, 9:950, 10:920, 11:1865, 12:1885}
    if df_combinado is None:
        return fallback
    try:
        df_m = df_combinado.groupby(["anio","mes"], as_index=False)["cantidad"].sum()
        proms = df_m.groupby("mes")["cantidad"].mean().round(0)
        return {int(m): int(v) for m, v in proms.items()}
    except Exception:
        return fallback


# ===================== Predicción principal =====================
def generar_predicciones_perfeccionadas():
    print_paths_banner("🔮 Ejecutando predict_sales_cantidades.py")
    print("🔮 GENERANDO PREDICCIONES 2025 (modelo general)")
    print("=" * 60)

    try:
        # Cargar modelo + metadata desde MODEL_DIR
        modelo = joblib.load(MODEL_CANTIDADES)
        with open(METADATA_CANT, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        metricas = metadata["metricas"]
        features = metadata["caracteristicas"]
        config   = metadata["configuracion"]

        print("📊 Calidad del modelo:")
        print(f"   • R²: {metricas['r2']:.4f} ({metricas['r2']*100:.1f}%)")
        print(f"   • MAE: {metricas['mae']:.0f}")
        print(f"   • Precisión: {metricas['precision']:.1f}%")

        # Patrones históricos (para construir lags razonables)
        print("\n📈 Analizando patrones históricos…")
        df_hist = cargar_datos_historicos()
        patrones = calcular_patrones_historicos(df_hist)

        # Supuesto de crecimiento anual (ajusta si quieres)
        factor_crecimiento_2025 = 1.08  # 8%
        print(f"   • Crecimiento anual supuesto: {int((factor_crecimiento_2025-1)*100)}%")

        # Generar insumos 2025
        pred = []
        periodo_base = 72 + 1  # enero 2019 = 1 → dic 2024 = 72 → enero 2025 = 73
        mae = metricas["mae"]

        for mes in range(1, 13):
            mes_sin = np.sin(2 * np.pi * (mes - 1) / 12)
            mes_cos = np.cos(2 * np.pi * (mes - 1) / 12)
            tendencia = periodo_base + mes - 1
            tendencia_cuad = tendencia ** 2

            navidad = 2.0 if mes == 12 else (1.8 if mes == 11 else 0.0)
            verano = 1.5 if mes in (6, 7) else 0.0
            inicio_anio = 0.5 if mes in (1, 2) else 0.0

            base_mes = patrones.get(mes, 800) * factor_crecimiento_2025
            lag_12  = base_mes
            lag_1   = base_mes * 0.98
            media_3 = base_mes * 1.02

            X_pred = pd.DataFrame([{
                "mes_sin": mes_sin,
                "mes_cos": mes_cos,
                "tendencia": tendencia,
                "tendencia_cuad": tendencia_cuad,
                "navidad": navidad,
                "verano": verano,
                "inicio_anio": inicio_anio,
                "lag_1": lag_1,
                "lag_12": lag_12,
                "media_3m": media_3
            }])[features]

            y_hat = int(max(0, modelo.predict(X_pred)[0]))
            pred.append({"anio": 2025, "mes": mes, "cantidad_predicha": y_hat})

        df_pred = pd.DataFrame(pred)
        df_pred = add_periodo_fields(df_pred)
        df_pred["minimo"]    = (df_pred["cantidad_predicha"] - metricas["mae"]).clip(lower=0).astype(int)
        df_pred["maximo"]    = (df_pred["cantidad_predicha"] + metricas["mae"]).astype(int)
        df_pred["confianza"] = float(metricas["precision"]) / 100.0

        # Orden y guardado
        df_pred = df_pred.sort_values(["anio","mes"])[
            ["periodo","anio","mes","cantidad_predicha","minimo","maximo","confianza"]
        ]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df_pred.to_csv(PRED_TOTALES_CSV, index=False, encoding="utf-8")
        print(f"\n💾 Predicciones guardadas en: {PRED_TOTALES_CSV}")

        # Resumen ejecutivo
        total_2025    = int(df_pred["cantidad_predicha"].sum())
        promedio_2025 = float(df_pred["cantidad_predicha"].mean())
        prom_hist     = float(config.get("cantidad_promedio", promedio_2025))
        crecimiento   = ((promedio_2025 - prom_hist) / max(prom_hist, 1e-9)) * 100

        mes_max = df_pred.loc[df_pred["cantidad_predicha"].idxmax()]
        mes_min = df_pred.loc[df_pred["cantidad_predicha"].idxmin()]

        print("\n📊 RESUMEN 2025")
        print(f"   • Total anual: {total_2025:,}")
        print(f"   • Promedio mensual: {promedio_2025:.0f}")
        print(f"   • Crecimiento vs histórico: {crecimiento:+.1f}%")
        print(f"   • Pico de demanda: mes {int(mes_max['mes'])} ({int(mes_max['cantidad_predicha'])})")
        print(f"   • Valle de demanda: mes {int(mes_min['mes'])} ({int(mes_min['cantidad_predicha'])})")

        return df_pred

    except Exception as e:
        print(f"❌ Error en predicciones: {e}")
        import traceback; traceback.print_exc()
        return generar_predicciones_conservadoras()


# ===================== Fallback conservador =====================
def generar_predicciones_conservadoras():
    print_paths_banner("🔄 Fallback predict_sales_cantidades.py")
    print("🔄 Generando predicciones conservadoras…")

    patrones_2025 = {
        1: 500, 2: 550, 3: 800, 4: 850, 5: 900, 6: 1500,
        7: 1600, 8: 950, 9: 1000, 10: 900, 11: 1800, 12: 2000
    }
    df = pd.DataFrame([{"anio": 2025, "mes": m, "cantidad_predicha": c} for m, c in patrones_2025.items()])
    df = add_periodo_fields(df)
    df["minimo"]    = (df["cantidad_predicha"] * 0.85).astype(int)
    df["maximo"]    = (df["cantidad_predicha"] * 1.15).astype(int)
    df["confianza"] = 0.85

    df = df.sort_values(["anio","mes"])[
        ["periodo","anio","mes","cantidad_predicha","minimo","maximo","confianza"]
    ]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PRED_TOTALES_CSV, index=False, encoding="utf-8")
    print(f"💾 Guardadas en: {PRED_TOTALES_CSV}")
    return df


# ===================== Main =====================
if __name__ == "__main__":
    generar_predicciones_perfeccionadas()
