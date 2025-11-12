# scikit_learn_ia/predict_sales_panel.py
import sys
import json
import re
import unicodedata
import joblib
import numpy as np
import pandas as pd

from scikit_learn_ia.paths import (
    DATA_DIR, MODEL_DIR,
    panel_model, panel_pred_file,
    print_paths_banner, panel_series_summary
)

VALID_SCOPES = {"producto", "categoria", "cliente"}

def _slug(value: str) -> str:
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join([c for c in value if not unicodedata.combining(c)])
    value = re.sub(r"[^A-Za-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "serie"

def _scope_key(scope: str) -> str:
    if scope == "producto":
        return "producto_id"
    if scope == "cliente":
        return "usuario_id"
    return "categoria"  # categoria es texto

def _next_year_month(y, m):
    m2 = 1 if m == 12 else m + 1
    y2 = y + 1 if m == 12 else y
    return y2, m2

def _ensure_key_dtype(df: pd.DataFrame, scope: str, key: str) -> pd.DataFrame:
    """Normaliza el tipo de la clave: Int64 para producto/cliente; string para categoria."""
    df = df.copy()
    if scope in {"producto", "cliente"}:
        # a entero 'Int64' (soporta NaN), luego dropear NaN
        df[key] = pd.to_numeric(df[key], errors="coerce").astype("Int64")
        df = df.dropna(subset=[key])
        df[key] = df[key].astype(int)  # a int puro para agrupar/filtrar y nombrar archivos 25 (no 25.0)
    else:
        df[key] = df[key].astype(str)
    return df

def _predict_one_series(scope: str, key: str, sid, modelo, meta, hist_df: pd.DataFrame) -> pd.DataFrame:
    """Genera 12 meses para una serie específica dada por sid (id o texto)."""
    sub = hist_df[hist_df[key] == sid].sort_values(["anio", "mes"]).copy()
    if sub.empty:
        return pd.DataFrame(columns=["periodo","anio","mes","scope",key,"cantidad_predicha","minimo","maximo","confianza"])

    # periodo histórico
    sub["periodo_idx"] = (sub["anio"] - sub["anio"].min()) * 12 + (sub["mes"] - 1) + 1
    last_year = int(sub["anio"].iloc[-1])
    last_month = int(sub["mes"].iloc[-1])
    last_periodo = int(sub["periodo_idx"].iloc[-1])

    q = sub["cantidad"].tolist()
    preds = []
    y, m = last_year, last_month
    p = last_periodo

    features = meta.get("features", ["mes_sin","mes_cos","tendencia","tendencia_cuad","lag_1","lag_12","media_3m"])
    mae_mean = meta.get("metricas_promedio", {}).get("mae_mean", None)
    conf = meta.get("metricas_promedio", {}).get("precision_mean", None)

    for _ in range(12):
        y, m = _next_year_month(y, m)
        p += 1

        mes_sin = np.sin(2 * np.pi * (m - 1) / 12)
        mes_cos = np.cos(2 * np.pi * (m - 1) / 12)
        tendencia = p
        tendencia_cuad = p ** 2

        lag_1 = q[-1] if len(q) >= 1 else (q[-1] if q else 0.0)
        lag_12 = q[-12] if len(q) >= 12 else lag_1
        media_3m = float(np.mean(q[-3:])) if len(q) >= 3 else (q[-1] if q else 0.0)

        row_feat = {
            "mes_sin": mes_sin, "mes_cos": mes_cos,
            "tendencia": tendencia, "tendencia_cuad": tendencia_cuad,
            "lag_1": lag_1, "lag_12": lag_12, "media_3m": media_3m,
        }
        X_pred = pd.DataFrame([row_feat])[features]
        y_hat = float(max(0.0, modelo.predict(X_pred)[0]))
        q.append(y_hat)

        rec = {
            "periodo": f"{y}-{m:02d}",
            "anio": y, "mes": m,
            "scope": scope, key: sid,
            "cantidad_predicha": round(y_hat, 2),
        }
        if mae_mean is not None:
            rec["minimo"] = round(max(0.0, rec["cantidad_predicha"] - mae_mean), 2)
            rec["maximo"] = round(rec["cantidad_predicha"] + mae_mean, 2)
        if conf is not None:
            rec["confianza"] = round(float(conf) / 100.0, 3)
        preds.append(rec)

    return pd.DataFrame(preds)

def predict_12(scope: str, serie_id=None, top_k: int = 50) -> pd.DataFrame:
    """
    Predice 12 meses futuros para:
      - Una serie concreta (si pasas serie_id)
      - O para TOP N series por volumen (si no pasas serie_id)
    Guarda CSV(s) en DATA_DIR con nombres seguros.
    """
    if scope not in VALID_SCOPES:
        raise ValueError(f"scope inválido: {scope}. Usa: {', '.join(sorted(VALID_SCOPES))}")

    dataset_path = DATA_DIR / f"cantidades_por_{scope}_mensual.csv"
    model_path = panel_model(scope)
    meta_path = MODEL_DIR / f"panel_{scope}_cantidades_metadata.json"

    if not dataset_path.exists():
        raise FileNotFoundError(f"No existe dataset: {dataset_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"No existe modelo: {model_path} (entrena primero)")
    if not meta_path.exists():
        raise FileNotFoundError(f"No existe metadata: {meta_path} (entrena primero)")

    df = pd.read_csv(dataset_path)
    # columnas base
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df.dropna(subset=["anio", "mes"]).copy()
    df["anio"] = df["anio"].astype(int)
    df["mes"] = df["mes"].astype(int)

    key = _scope_key(scope)
    if key not in df.columns:
        # fallback por si el CSV trae otro orden/nombres
        # usa el primer campo que no sea anio/mes/cantidad
        cand = [c for c in df.columns if c not in ("anio", "mes", "cantidad")]
        if not cand:
            raise ValueError("No se encontró columna identificadora (key).")
        key = cand[0]

    df = _ensure_key_dtype(df, scope, key)
    df = df.sort_values([key, "anio", "mes"])

    # Elegir series objetivo
    if serie_id is None:
        top = (
            df.groupby(key)["cantidad"].sum().sort_values(ascending=False).head(top_k).index.tolist()
        )
        target_ids = top
    else:
        if scope in {"producto", "cliente"}:
            try:
                serie_id = int(serie_id)
            except:
                raise ValueError(f"{key} debe ser entero, recibido: {serie_id}")
        else:
            serie_id = str(serie_id)
        target_ids = [serie_id]

    # Cargar modelo + metadata
    modelo = joblib.load(model_path)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    all_rows = []

    # Predicción por serie y guardado por-serie
    for sid in target_ids:
        df_s = _predict_one_series(scope, key, sid, modelo, meta, df)
        if df_s.empty:
            print(f"⚠️ Serie {key}={sid} sin datos históricos. Saltando.")
            continue

        # Nombre de archivo por serie:
        if scope in {"producto", "cliente"}:
            out_ser = panel_pred_file(scope, int(sid))
        else:
            out_ser = panel_pred_file(scope, _slug(sid))
        df_s.to_csv(out_ser, index=False, encoding="utf-8")
        print(f"✅ Predicciones guardadas: {out_ser.name}")

        all_rows.append(df_s)

    # Escribir AGREGADO SIEMPRE (aunque esté vacío) para que la vista no falle
    out_all = panel_pred_file(scope, None)
    if all_rows:
        df_all = pd.concat(all_rows, ignore_index=True)
    else:
        df_all = pd.DataFrame(columns=["periodo","anio","mes","scope",key,"cantidad_predicha","minimo","maximo","confianza"])
    df_all.to_csv(out_all, index=False, encoding="utf-8")
    print(f"✅ Predicciones agregadas: {out_all.name} (rows={len(df_all)})")

    return df_all

def _usage():
    print(
        "Uso:\n"
        "  python scikit_learn_ia/predict_sales_panel.py <scope> [serie_id]\n\n"
        "Parámetros:\n"
        "  <scope>   : producto | categoria | cliente\n"
        "  [serie_id]: opcional; si se omite, predice TOP 50 por volumen\n\n"
        "Ejemplos:\n"
        "  python scikit_learn_ia/predict_sales_panel.py categoria\n"
        "  python scikit_learn_ia/predict_sales_panel.py categoria 'Categoría 2'\n"
        "  python scikit_learn_ia/predict_sales_panel.py producto 25\n"
        "  python scikit_learn_ia/predict_sales_panel.py cliente 102\n"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        _usage(); sys.exit(1)

    print_paths_banner("🔮 Predicción panel (12 meses)")
    scope = sys.argv[1].strip().lower()
    serie = sys.argv[2] if len(sys.argv) >= 3 else None

    try:
        predict_12(scope, serie_id=serie)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(2)
