# scikit_learn_ia/train_model_panel.py
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings("ignore")

# 🛣️ Rutas unificadas (local / Railway) + helpers
from scikit_learn_ia.paths import (
    DATA_DIR, MODEL_DIR,
    panel_series_summary, panel_metrics, panel_model,
    print_paths_banner
)

# ====== Parámetros de control ======
TOP_K_SERIES = 50        # cuántas series evaluar para métricas promedio
MIN_ACTIVE_MONTHS = 18   # meses con cantidad > 0
MIN_TOTAL_POINTS  = 24   # puntos mínimos por serie

# ====== Archivos de entrada por scope ======
PANEL_FILES = {
    "producto": DATA_DIR / "cantidades_por_producto_mensual.csv",
    "categoria": DATA_DIR / "cantidades_por_categoria_mensual.csv",
    "cliente":   DATA_DIR / "cantidades_por_cliente_mensual.csv",
}

def _ensure_numeric(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _time_split_index(n_points: int) -> int:
    """Split temporal: ideal últimos 12 meses si hay >=36 puntos; caso contrario 85%."""
    if n_points >= 36:
        return n_points - 12
    return max(1, int(n_points * 0.85))

def entrenar_panel(scope: str, file_path):
    print(f"\n🚀 Entrenando panel '{scope}' desde {file_path.name}")
    if not file_path.exists():
        print(f"❌ Archivo no encontrado: {file_path}")
        return None

    # Carga y saneo básico
    df = pd.read_csv(file_path)
    df = _ensure_numeric(df, ["anio", "mes", "cantidad"])
    df = df.dropna(subset=["anio", "mes", "cantidad"])
    df = df.sort_values(["anio", "mes"], kind="stable")

    # Columna identificadora (la que NO es anio/mes/cantidad)
    posibles = [c for c in df.columns if c not in ["anio", "mes", "cantidad"]]
    if not posibles:
        raise ValueError("No se encontró columna identificadora de serie (key).")
    key = posibles[0]
    print(f"🔑 Campo identificador: {key}")

    # ====== Features globales ======
    df["periodo"] = (df["anio"] - df["anio"].min()) * 12 + (df["mes"] - 1) + 1
    df["mes_sin"] = np.sin(2 * np.pi * (df["mes"] - 1) / 12)
    df["mes_cos"] = np.cos(2 * np.pi * (df["mes"] - 1) / 12)
    df["tendencia"] = df["periodo"]
    df["tendencia_cuad"] = df["periodo"] ** 2

    # Orden correcto por grupo/tiempo para lags/rolling
    df = df.sort_values([key, "anio", "mes"], kind="stable")

    # Lags y rolling por grupo
    df["lag_1"]    = df.groupby(key)["cantidad"].transform(lambda s: s.shift(1))
    df["lag_12"]   = df.groupby(key)["cantidad"].transform(lambda s: s.shift(12))
    df["media_3m"] = df.groupby(key)["cantidad"].transform(lambda s: s.rolling(3, min_periods=1).mean())

    # Rellenos seguros por grupo (alineados)
    df["lag_1"]    = df.groupby(key)["lag_1"].transform(lambda s: s.bfill().ffill())
    df["lag_12"]   = df.groupby(key)["lag_12"].transform(lambda s: s.bfill().ffill())
    df["media_3m"] = df.groupby(key)["media_3m"].transform(lambda s: s.bfill().ffill())

    features = ["mes_sin", "mes_cos", "tendencia", "tendencia_cuad", "lag_1", "lag_12", "media_3m"]
    X_all = df[features]
    y_all = df["cantidad"].fillna(0)

    # ====== Modelo GLOBAL (uno por scope) ======
    modelo_global = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=3,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1
    )
    modelo_global.fit(X_all, y_all)

    # Guardar modelo global (siempre sobrescribe)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    job_path = panel_model(scope)
    joblib.dump(modelo_global, job_path)

    # ====== Selección y evaluación de series (rápido) ======
    series_stats = df.groupby(key).agg(
        puntos=("cantidad", "size"),
        activos=("cantidad", lambda s: int((s > 0).sum())),
        total=("cantidad", "sum"),
        media=("cantidad", "mean"),
        std=("cantidad", "std"),
    ).reset_index()

    series_stats = series_stats.fillna({"std": 0.0})
    mask_valid = (
        (series_stats["puntos"] >= MIN_TOTAL_POINTS) &
        (series_stats["activos"] >= MIN_ACTIVE_MONTHS) &
        (series_stats["std"] > 0.0)
    )
    series_validas = series_stats[mask_valid].sort_values("total", ascending=False)
    series_eval = series_validas[key].head(TOP_K_SERIES).tolist()

    r2_list, mae_list, prec_list = [], [], []
    rows_eval = []
    modelos_evaluados = 0

    for serie_id in series_eval:
        sub = df[df[key] == serie_id].sort_values(["anio", "mes"], kind="stable").copy()
        Xs, ys = sub[features], sub["cantidad"]

        split = _time_split_index(len(Xs))
        X_train, X_test = Xs.iloc[:split], Xs.iloc[split:]
        y_train, y_test = ys.iloc[:split], ys.iloc[split:]
        if len(X_test) == 0 or y_test.mean() == 0:
            continue

        m = RandomForestRegressor(
            n_estimators=60,
            max_depth=10,
            random_state=42,
            n_jobs=1
        )
        m.fit(X_train, y_train)
        y_pred = m.predict(X_test)

        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        precision = max(0.0, 100.0 - (mae / max(1.0, y_test.mean()) * 100.0))

        r2_list.append(r2)
        mae_list.append(mae)
        prec_list.append(precision)
        modelos_evaluados += 1

        rows_eval.append({
            key: serie_id,
            "n_total": int(len(sub)),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "y_test_mean": float(y_test.mean()),
            "mae": float(mae),
            "r2": float(r2),
            "precision": float(precision),
        })

    # ====== Salidas auxiliares (siempre sobrescriben) ======
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    metrics_csv = panel_metrics(scope)
    pd.DataFrame(rows_eval).to_csv(metrics_csv, index=False)

    series_summary_csv = panel_series_summary(scope)
    series_stats.to_csv(series_summary_csv, index=False)

    meta_path = MODEL_DIR / f"panel_{scope}_cantidades_metadata.json"
    meta = {
        "scope": scope,
        "fecha_entrenamiento": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "features": features,
        "muestras_totales": int(len(df)),
        "series_total": int(df[key].nunique()),
        "series_evaluadas": int(modelos_evaluados),
        "metricas_promedio": {
            "r2_mean": float(np.mean(r2_list)) if r2_list else None,
            "mae_mean": float(np.mean(mae_list)) if mae_list else None,
            "precision_mean": float(np.mean(prec_list)) if prec_list else None,
        },
        "archivos_auxiliares": {
            "metrics_csv": str(metrics_csv),
            "series_summary_csv": str(series_summary_csv),
        },
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Entrenado panel {scope} -> {job_path.name}")
    print(f"ℹ️ Métricas promedio (TOP {min(TOP_K_SERIES, len(series_eval))}): {meta['metricas_promedio']}")
    return meta

def main():
    print_paths_banner("🎯 Entrenando paneles de demanda (producto/categoría/cliente)")
    for scope, path in PANEL_FILES.items():
        try:
            entrenar_panel(scope, path)
        except Exception as e:
            print(f"⚠️ {scope}: {e}")

if __name__ == "__main__":
    main()
