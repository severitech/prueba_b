# scikit_learn_ia/paths.py
from __future__ import annotations
import os, sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

# ================================
# 🔍 DETECCIÓN DE ENTORNO
# ================================
def _detect_env() -> str:
    if os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("RAILWAY_ENVIRONMENT"):
        return "railway"
    if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"):
        return "render"
    if os.environ.get("DYNO"):  
        return "heroku"
    return "local"

ENV_NAME = _detect_env()

# ================================
# 📂 BASES Y RUTAS PRINCIPALES
# ================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR  = Path(os.getenv("IA_DATA_DIR", BASE_DIR / "scikit_learn_ia" / "datasets"))
MODEL_DIR = Path(os.getenv("IA_MODEL_DIR", BASE_DIR / "scikit_learn_ia" / "model"))

# Crear carpetas si no existen
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ================================
# 🧩 RUTAS GLOBALES DE ARCHIVOS
# ================================
VENTAS_CSV        = DATA_DIR / "ventas.csv"
DETALLES_CSV      = DATA_DIR / "detalles_venta.csv"
PRED_TOTALES_CSV  = DATA_DIR / "predicciones_cantidades_mensuales.csv"
MODEL_CANTIDADES  = MODEL_DIR / "modelo_prediccion_cantidades.joblib"
METADATA_CANT     = MODEL_DIR / "metadata_cantidades.json"

# Reportes
PDF_PATH  = DATA_DIR / "reporte_predicciones.pdf"
XLSX_PATH = DATA_DIR / "reporte_predicciones.xlsx"

# ================================
# 📊 RUTAS PARA PANELES IA
# ================================
def panel_series_summary(scope: str):
    return DATA_DIR / f"panel_{scope}_series_summary.csv"

def panel_metrics(scope: str):
    return DATA_DIR / f"panel_{scope}_metrics.csv"

def panel_model(scope: str):
    return MODEL_DIR / f"panel_{scope}_cantidades.joblib"

def panel_pred_file(scope: str, serie: str | int | None):
    if serie is None:
        return DATA_DIR / f"pred_{scope}_all.csv"
    return DATA_DIR / f"pred_{scope}_{str(serie)}.csv"

# ================================
# 🧭 UTILIDADES Y BANNER
# ================================
def print_paths_banner(note: str | None = None) -> None:
    """Muestra en consola las rutas activas (local o Railway)."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def ok(path: Path) -> str:
        return "✅" if path.exists() else "⚠️"

    print("\n" + "=" * 75)
    print(f"🔧 RUTAS ACTIVAS [{ENV_NAME.upper()}] — {now}")
    print("-" * 75)
    print(f"Python:   {sys.executable}")
    print(f"CWD:      {Path.cwd()}")
    print(f"BASE_DIR: {BASE_DIR} ({ok(BASE_DIR)})")
    print(f"DATA_DIR: {DATA_DIR} ({ok(DATA_DIR)})")
    print(f"MODEL_DIR:{MODEL_DIR} ({ok(MODEL_DIR)})")
    print(f"VENTAS_CSV:       {VENTAS_CSV} ({ok(VENTAS_CSV)})")
    print(f"PRED_TOTALES_CSV: {PRED_TOTALES_CSV} ({ok(PRED_TOTALES_CSV)})")
    print(f"MODEL_CANTIDADES: {MODEL_CANTIDADES} ({ok(MODEL_CANTIDADES)})")
    print(f"METADATA_CANT:    {METADATA_CANT} ({ok(METADATA_CANT)})")
    print(f"PDF_PATH:         {PDF_PATH} ({ok(PDF_PATH)})")
    print(f"XLSX_PATH:        {XLSX_PATH} ({ok(XLSX_PATH)})")
    if note:
        print(f"Nota: {note}")
    print("=" * 75 + "\n")
