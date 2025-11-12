# scikit_learn_ia/predict_sales_panel.py
import sys
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "datasets"
MODEL_DIR = BASE_DIR / "model"

VALID_SCOPES = {"producto", "categoria", "cliente"}

def _load_scope_assets(scope: str):
    dataset = DATA_DIR / f"cantidades_por_{scope}_mensual.csv"
    model = MODEL_DIR / f"panel_{scope}_cantidades.joblib"
    meta  = MODEL_DIR / f"panel_{scope}_cantidades_metadata.json"
    if not dataset.exists():
        raise FileNotFoundError(f"No existe dataset: {dataset}")
    if not model.exists():
        raise FileNotFoundError(f"No existe modelo: {model} (entrena primero)")
    if not meta.exists():
        raise FileNotFoundError(f"No existe metadata: {meta} (entrena primero)")
    return dataset, model, meta

def _key_col(df: pd.DataFrame):
    return [c for c in df.columns if c not in ("anio", "mes", "cantidad")][0]

def _next_year_month(y, m):
    m2 = 1 if m == 12 else m + 1
    y2 = y + 1 if m == 12 else y
    return y2, m2

def predict_12(scope: str, serie_id=None, top_k: int = 10) -> pd.DataFrame:
    """Predice 12 meses futuros para una serie (o TOP N si no se pasa id). Guarda CSV(s) en datasets/."""
    if scope not in VALID_SCOPES:
        raise ValueError(f"scope inválido: {scope}. Usa: {', '.join(sorted(VALID_SCOPES))}")

    dataset_path, model_path, meta_path = _load_scope_assets(scope)
    df = pd.read_csv(dataset_path)
    key = _key_col(df)

    # Normaliza tipos
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df.dropna(subset=["anio", "mes"]).sort_values([key, "anio", "mes"])

    # Elegir series objetivo
    if serie_id is None:
        top = (
            df.groupby(key)["cantidad"].sum().sort_values(ascending=False).head(top_k).index.tolist()
        )
        target_ids = top
    else:
        # casteo flexible (categoría puede ser string)
        if key in ("producto_id", "usuario_id"):
            try:
                serie_id = int(serie_id)
            except:
                raise ValueError(f"{key} debe ser entero, recibido: {serie_id}")
        target_ids = [serie_id]

    # Cargar modelo + metadata (para respetar orden de features)
    modelo = joblib.load(model_path)
    meta = json.load(open(meta_path, encoding="utf-8"))
    features = meta.get("features", [
        "mes_sin", "mes_cos", "tendencia", "tendencia_cuad", "lag_1", "lag_12", "media_3m"
    ])

    # Salida agregada (si hay varias series)
    all_rows = []

    for sid in target_ids:
        sub = df[df[key] == sid].sort_values(["anio", "mes"]).copy()
        if sub.empty:
            # crea un registro de error y sigue
            print(f"⚠️ Serie {key}={sid} no encontrada en {dataset_path.name}")
            continue

        # construir periodo histórico y auxiliares
        sub["periodo"] = (sub["anio"] - sub["anio"].min()) * 12 + (sub["mes"] - 1) + 1
        last_year = int(sub["anio"].iloc[-1])
        last_month = int(sub["mes"].iloc[-1])
        last_periodo = int(sub["periodo"].iloc[-1])

        # buffer de cantidades para lag recursivo
        # usamos lista con históricos + iremos agregando predicciones
        q = sub["cantidad"].tolist()

        preds = []
        y, m = last_year, last_month
        p = last_periodo

        for _ in range(12):
            # siguiente mes
            y, m = _next_year_month(y, m)
            p += 1

            mes_sin = np.sin(2 * np.pi * (m - 1) / 12)
            mes_cos = np.cos(2 * np.pi * (m - 1) / 12)
            tendencia = p
            tendencia_cuad = p ** 2

            # lags recursivos sobre q (hist + preds)
            lag_1 = q[-1] if len(q) >= 1 else (q[-1] if q else 0.0)
            lag_12 = q[-12] if len(q) >= 12 else lag_1
            media_3m = float(np.mean(q[-3:])) if len(q) >= 3 else (q[-1] if q else 0.0)

            row_feat = {
                "mes_sin": mes_sin,
                "mes_cos": mes_cos,
                "tendencia": tendencia,
                "tendencia_cuad": tendencia_cuad,
                "lag_1": lag_1,
                "lag_12": lag_12,
                "media_3m": media_3m,
            }

            X_pred = pd.DataFrame([row_feat])[features]
            y_hat = float(max(0.0, modelo.predict(X_pred)[0]))
            q.append(y_hat)

            preds.append({
                "periodo": f"{y}-{m:02d}",
                "anio": y,
                "mes": m,
                "scope": scope,
                key: sid,
                "cantidad_predicha": round(y_hat, 2),
            })

        # Intervalos a partir de métrica promedio (si existe)
        mae_mean = meta.get("metricas_promedio", {}).get("mae_mean", None)
        conf = meta.get("metricas_promedio", {}).get("precision_mean", None)
        for r in preds:
            if mae_mean is not None:
                r["minimo"] = round(max(0.0, r["cantidad_predicha"] - mae_mean), 2)
                r["maximo"] = round(r["cantidad_predicha"] + mae_mean, 2)
            if conf is not None:
                r["confianza"] = round(float(conf) / 100.0, 3)

        # Guardar CSV POR SERIE
        out_ser = DATA_DIR / f"pred_{scope}_{str(sid)}.csv"
        pd.DataFrame(preds).to_csv(out_ser, index=False)
        print(f"✅ Predicciones guardadas: {out_ser.name}")

        all_rows.extend(preds)

    # Si hubo varias series, guardar agregada
    if len(all_rows) > 0 and (serie_id is None or len(target_ids) > 1):
        out_all = DATA_DIR / f"pred_{scope}_all.csv"
        pd.DataFrame(all_rows).to_csv(out_all, index=False)
        print(f"✅ Predicciones agregadas: {out_all.name}")

    return pd.DataFrame(all_rows or preds)

def _usage():
    print(
        "Uso:\n"
        "  python scikit_learn_ia/predict_sales_panel.py <scope> [serie_id]\n\n"
        "Parámetros:\n"
        "  <scope>   : producto | categoria | cliente\n"
        "  [serie_id]: opcional; si se omite, predice TOP 10 por volumen\n\n"
        "Ejemplos:\n"
        "  python scikit_learn_ia/predict_sales_panel.py categoria\n"
        "  python scikit_learn_ia/predict_sales_panel.py categoria Televisores\n"
        "  python scikit_learn_ia/predict_sales_panel.py producto 25\n"
        "  python scikit_learn_ia/predict_sales_panel.py cliente 102\n"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        _usage(); sys.exit(1)
    scope = sys.argv[1].strip().lower()
    serie = sys.argv[2] if len(sys.argv) >= 3 else None
    try:
        predict_12(scope, serie_id=serie)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(2)
