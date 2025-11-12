import os
import json
import subprocess, sys
from pathlib import Path
from datetime import datetime
from scikit_learn_ia.reportes.generar_reporte_pdf import crear_reporte_pdf
from scikit_learn_ia.reportes.generar_reporte_excel import crear_reporte_excel

import pandas as pd
from django.conf import settings
from django.utils.http import http_date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.http import FileResponse, HttpResponseNotFound

# Rutas base
BASE_DIR = Path(settings.BASE_DIR) if hasattr(settings, "BASE_DIR") else Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "scikit_learn_ia" / "datasets"
MODEL_DIR = BASE_DIR / "scikit_learn_ia" / "model"
VENTAS_CSV = DATA_DIR / "ventas.csv"
DETALLES_CSV = DATA_DIR / "detalles_venta.csv"
PREDICCIONES_CSV = DATA_DIR / "predicciones_cantidades_mensuales.csv"
METADATA_JSON = MODEL_DIR / "metadata_cantidades.json"
PDF_PATH = DATA_DIR / "reporte_predicciones.pdf"
XLSX_PATH = DATA_DIR / "reporte_predicciones.xlsx"

VALID_SCOPES = {"categoria", "producto", "cliente"}
# ---------- Helpers ----------
def _build_fecha_canonica(anio: int, mes: int):
    return pd.to_datetime(f"{int(anio)}-{int(mes):02d}-01", utc=True)

def add_periodo_fields(df: pd.DataFrame) -> pd.DataFrame:
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
        df["mes"] = df["fecha"].dt.month
    if "anio" in df.columns and "mes" in df.columns:
        if "fecha" not in df.columns:
            df["fecha"] = [_build_fecha_canonica(a, m) if pd.notna(a) and pd.notna(m) else pd.NaT
                           for a, m in zip(df["anio"], df["mes"])]
        else:
            mask = df["fecha"].isna() & df["anio"].notna() & df["mes"].notna()
            df.loc[mask, "fecha"] = [
                _build_fecha_canonica(a, m) for a, m in zip(df.loc[mask, "anio"], df.loc[mask, "mes"])
            ]
    if "fecha" in df.columns:
        df["anio"] = df["fecha"].dt.year
        df["mes"] = df["fecha"].dt.month
        df["periodo"] = df["fecha"].dt.strftime("%Y-%m")
    else:
        if "anio" in df.columns and "mes" in df.columns:
            df["periodo"] = df.apply(lambda r: f"{int(r['anio'])}-{int(r['mes']):02d}", axis=1)
    return df

import sys, os, subprocess, io

def _run_script(rel_path: str) -> tuple[bool, str]:
    """Ejecuta un script Python usando el mismo intérprete que Django, con salida en UTF-8."""
    script_path = BASE_DIR / rel_path
    if not script_path.exists():
        return False, f"[ERROR] Script no encontrado: {script_path}"

    env = {**os.environ, "PYTHONUTF8": "1"}
    try:
        # Se fuerza encoding UTF-8 para leer stdout/stderr sin errores de Windows
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        out, err = proc.communicate()
        out = out.decode("utf-8", errors="replace")
        err = err.decode("utf-8", errors="replace")
        combined = "---- STDOUT ----\n" + out
        if err:
            combined += "\n---- STDERR ----\n" + err
        combined += f"\n[returncode={proc.returncode}]"
        return proc.returncode == 0, combined
    except Exception as e:
        return False, f"[EXCEPTION] {e}"


# ---------- Views ----------
class IAHealthView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({
            "ok": True,
            "time_utc": datetime.utcnow().isoformat() + "Z",
            "ventas_csv": VENTAS_CSV.exists(),
            "detalles_csv": DETALLES_CSV.exists(),
            "predicciones_csv": PREDICCIONES_CSV.exists(),
            "metadata_json": METADATA_JSON.exists(),
        })

class GenerarDatosSinteticosView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ok, out = _run_script("scikit_learn_ia/generar_datos_sinteticos.py")
        status_code = status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({"ok": ok, "log": out[-8000:]}, status=status_code)  # devuelve últimas líneas del log

class EntrenarModeloCantidadesView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ok, out = _run_script("scikit_learn_ia/train_model_cantidades.py")
        # Cargar métricas si existen
        payload = {"ok": ok, "log": out[-8000:]}
        if METADATA_JSON.exists():
            try:
                payload["metadata"] = json.loads(METADATA_JSON.read_text(encoding="utf-8"))
            except Exception as e:
                payload["metadata_error"] = str(e)
        status_code = status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(payload, status=status_code)

class PredecirCantidadesView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ok, out = _run_script("scikit_learn_ia/predict_sales_cantidades.py")
        payload = {"ok": ok, "log": out[-8000:]}
        if PREDICCIONES_CSV.exists():
            try:
                df = pd.read_csv(PREDICCIONES_CSV)
                payload["rows"] = len(df)
                # muestra rápida
                payload["preview"] = df.head(12).to_dict(orient="records")
            except Exception as e:
                payload["csv_error"] = str(e)
        status_code = status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(payload, status=status_code)

class PrediccionesListView(APIView):
    """
    GET /ia/predicciones?anio=2025  -> lista predicciones del año
    GET /ia/predicciones?anio=2025&mes=11 -> trae un mes
    """
    permission_classes = [AllowAny]
    def get(self, request):
        if not PREDICCIONES_CSV.exists():
            return Response({"ok": False, "error": "No existe el CSV de predicciones."},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            df = pd.read_csv(PREDICCIONES_CSV)
            df = add_periodo_fields(df)
            anio = request.query_params.get("anio")
            mes = request.query_params.get("mes")

            if anio:
                df = df[df["anio"] == int(anio)]
            if mes:
                df = df[df["mes"] == int(mes)]

            df = df.sort_values(["anio", "mes"])
            return Response({
                "ok": True,
                "count": len(df),
                "items": df.to_dict(orient="records")
            })
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReporteVentasMensualView(APIView):
    """
    GET /ia/reporte-ventas?anio=2022&mes=1
    Devuelve total y cantidad de ventas (nivel venta o nivel ítem) del mes solicitado.
    """
    permission_classes = [AllowAny]
    def get(self, request):
        anio = int(request.query_params.get("anio", 0))
        mes = int(request.query_params.get("mes", 0))
        if anio == 0 or mes == 0:
            return Response({"ok": False, "error": "Parámetros requeridos: anio, mes"},
                            status=status.HTTP_400_BAD_REQUEST)

        if not VENTAS_CSV.exists():
            return Response({"ok": False, "error": "No existe ventas.csv"}, status=status.HTTP_404_NOT_FOUND)

        try:
            df_ventas = pd.read_csv(VENTAS_CSV)
            df_ventas = add_periodo_fields(df_ventas)

            # Nivel venta: total de las ventas de ese mes
            df_mes = df_ventas[(df_ventas["anio"] == anio) & (df_ventas["mes"] == mes)]
            total_ventas = float(df_mes["total"].sum()) if "total" in df_mes.columns else None
            cant_ventas = int(df_mes["id"].count()) if "id" in df_mes.columns else None

            # Nivel ítem: si hay detalles
            nivel_item = None
            if DETALLES_CSV.exists():
                try:
                    df_det = pd.read_csv(DETALLES_CSV)
                    df_det = df_det.merge(df_ventas[["id", "anio", "mes", "periodo"]], left_on="venta_id", right_on="id", how="inner")
                    df_det = add_periodo_fields(df_det)
                    df_det_mes = df_det[(df_det["anio"] == anio) & (df_det["mes"] == mes)]
                    cantidad_items = int(df_det_mes["cantidad"].sum()) if "cantidad" in df_det_mes.columns else None
                    total_items = float(df_det_mes["subtotal"].sum()) if "subtotal" in df_det_mes.columns else None
                    nivel_item = {
                        "cantidad_items": cantidad_items,
                        "monto_items": total_items
                    }
                except Exception as e:
                    nivel_item = {"error": f"Detalles no disponibles: {e}"}

            return Response({
                "ok": True,
                "filtro": {"anio": anio, "mes": mes, "periodo": f"{anio}-{mes:02d}"},
                "nivel_venta": {"cantidad_ventas": cant_ventas, "monto_total": total_ventas},
                "nivel_item": nivel_item
            })
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportePDFView(APIView):
    """
    GET  /ia/reporte-pdf/   -> genera (si no existe) y descarga PDF
    POST /ia/reporte-pdf/   -> fuerza regeneración y descarga PDF
    """
    permission_classes = [AllowAny]

    def get(self, request):
        if not PDF_PATH.exists():
            if not PREDICCIONES_CSV.exists():
                return Response({"ok": False, "error": "No hay predicciones CSV para generar el PDF."},
                                status=status.HTTP_404_NOT_FOUND)
            ok = crear_reporte_pdf(desde_csv=True)
            if not ok:
                return Response({"ok": False, "error": "Error generando PDF."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not PDF_PATH.exists():
            return HttpResponseNotFound("No se encontró el archivo PDF.")

        resp = FileResponse(open(PDF_PATH, "rb"), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{PDF_PATH.name}"'
        resp["Last-Modified"] = http_date(PDF_PATH.stat().st_mtime)
        return resp

    def post(self, request):
        if not PREDICCIONES_CSV.exists():
            return Response({"ok": False, "error": "No hay predicciones CSV para generar el PDF."},
                            status=status.HTTP_404_NOT_FOUND)
        ok = crear_reporte_pdf(desde_csv=True)
        if not ok or not PDF_PATH.exists():
            return Response({"ok": False, "error": "Falló la generación del PDF."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        resp = FileResponse(open(PDF_PATH, "rb"), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{PDF_PATH.name}"'
        resp["Last-Modified"] = http_date(PDF_PATH.stat().st_mtime)
        return resp


class ReporteExcelView(APIView):
    """
    GET  /ia/reporte-excel/  -> genera (si no existe) y descarga XLSX
    POST /ia/reporte-excel/  -> fuerza regeneración y descarga XLSX
    """
    permission_classes = [AllowAny]

    def get(self, request):
        if not XLSX_PATH.exists():
            if not PREDICCIONES_CSV.exists():
                return Response({"ok": False, "error": "No hay predicciones CSV para generar el Excel."},
                                status=status.HTTP_404_NOT_FOUND)
            ok = crear_reporte_excel(desde_csv=True)
            if not ok:
                return Response({"ok": False, "error": "Error generando Excel."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not XLSX_PATH.exists():
            return HttpResponseNotFound("No se encontró el archivo Excel.")

        resp = FileResponse(
            open(XLSX_PATH, "rb"),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = f'attachment; filename="{XLSX_PATH.name}"'
        resp["Last-Modified"] = http_date(XLSX_PATH.stat().st_mtime)
        return resp

    def post(self, request):
        if not PREDICCIONES_CSV.exists():
            return Response({"ok": False, "error": "No hay predicciones CSV para generar el Excel."},
                            status=status.HTTP_404_NOT_FOUND)
        ok = crear_reporte_excel(desde_csv=True)
        if not ok or not XLSX_PATH.exists():
            return Response({"ok": False, "error": "Falló la generación del Excel."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        resp = FileResponse(
            open(XLSX_PATH, "rb"),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = f'attachment; filename="{XLSX_PATH.name}"'
        resp["Last-Modified"] = http_date(XLSX_PATH.stat().st_mtime)
        return resp

def _panel_paths_for(scope: str):
    """Devuelve paths útiles para un scope."""
    series_summary_csv = DATA_DIR / f"panel_{scope}_series_summary.csv"   # creado en train_model_panel.py
    metrics_csv        = DATA_DIR / f"panel_{scope}_metrics.csv"          # creado en train_model_panel.py
    return series_summary_csv, metrics_csv

def _panel_pred_csv(scope: str, serie: str):
    """Nombre de archivo de predicciones por serie para el scope."""
    # Para categoria es string (p.ej. 'Categoría 2'); producto/cliente suelen ser enteros pero guardamos como str
    safe = str(serie)
    return DATA_DIR / f"pred_{scope}_{safe}.csv"

def _panel_predict_all_csv(scope: str):
    return DATA_DIR / f"pred_{scope}_all.csv"

def _run_predict(scope: str, serie: str | None):
    """Llama al script de predicción por panel."""
    script = BASE_DIR / "scikit_learn_ia" / "predict_sales_panel.py"
    if not script.exists():
        return False, f"No existe el script de predicción: {script}"
    cmd = [os.getenv("PYTHON", "python"), str(script), scope]
    if serie is not None:
        cmd.append(str(serie))
    try:
        proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
        ok = (proc.returncode == 0)
        log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return ok, log[-8000:]
    except Exception as e:
        return False, f"Error ejecutando predict: {e}"

class PanelSeriesListView(APIView):
    """
    GET /api/ia/panel/series/?scope=categoria|producto|cliente
    -> Lista de series disponibles (para selector del frontend).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        scope = str(request.query_params.get("scope", "")).lower().strip()
        if scope not in VALID_SCOPES:
            return Response({"ok": False, "error": f"scope inválido. Usa {sorted(VALID_SCOPES)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        series_summary_csv, metrics_csv = _panel_paths_for(scope)
        if not series_summary_csv.exists():
            return Response({"ok": False, "error": f"No existe {series_summary_csv.name}. Entrena primero."},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            df = pd.read_csv(series_summary_csv)
            # La columna key es la que no es anio/mes/cantidad… (train_model_panel la deja como primera col)
            key_cols = [c for c in df.columns if c not in {"puntos", "activos", "total", "media", "std"}]
            if not key_cols:
                return Response({"ok": False, "error": "No se pudo detectar la columna identificadora."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            key = key_cols[0]
            # Orden por volumen
            df = df.sort_values("total", ascending=False)
            items = df[[key, "puntos", "activos", "total", "media", "std"]].to_dict(orient="records")
            return Response({
                "ok": True,
                "scope": scope,
                "key": key,
                "count": len(items),
                "items": items
            })
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PanelPrediccionesView(APIView):
    """
    GET /api/ia/panel/predicciones/?scope=categoria|producto|cliente&serie=<id_o_nombre>&force=1
       - scope=categoria -> serie es string (p.ej. 'Categoría 2')
       - scope=producto  -> serie es id (int)   (p.ej. 25)
       - scope=cliente   -> serie es id (int)   (p.ej. 102)
    Si no existe el CSV de predicción y viene force=1, se genera on-the-fly.
    Si no se pasa 'serie', devuelve el agregado TOP (pred_{scope}_all.csv) si existe
    o lo genera con force=1.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        scope = str(request.query_params.get("scope", "")).lower().strip()
        serie = request.query_params.get("serie", None)
        force = str(request.query_params.get("force", "0")).strip() in {"1", "true", "True"}

        if scope not in VALID_SCOPES:
            return Response({"ok": False, "error": f"scope inválido. Usa {sorted(VALID_SCOPES)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Si no se pidió serie, intentamos servir el agregado TOP
        if not serie:
            agg_path = _panel_predict_all_csv(scope)
            if not agg_path.exists():
                if not force:
                    return Response({"ok": False, "error": f"No existe {agg_path.name}. Ejecuta predict o usa force=1."},
                                    status=status.HTTP_404_NOT_FOUND)
                ok, log = _run_predict(scope, None)
                if not ok or not agg_path.exists():
                    return Response({"ok": False, "error": "Falló la generación agregada", "log": log},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                df = pd.read_csv(agg_path)
                df = df.sort_values(["anio", "mes"])
                return Response({"ok": True, "scope": scope, "aggregate": True, "count": len(df),
                                 "items": df.to_dict(orient="records")})
            except Exception as e:
                return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Se pidió una serie concreta
        # Normaliza enteros para producto/cliente
        if scope in {"producto", "cliente"}:
            try:
                serie = int(serie)
            except:
                return Response({"ok": False, "error": f"Para scope={scope}, 'serie' debe ser entero."},
                                status=status.HTTP_400_BAD_REQUEST)

        pred_path = _panel_pred_csv(scope, serie)

        if not pred_path.exists():
            if not force:
                return Response({"ok": False, "error": f"No existe {pred_path.name}. Ejecuta predict o usa force=1."},
                                status=status.HTTP_404_NOT_FOUND)
            ok, log = _run_predict(scope, serie)
            if not ok or not pred_path.exists():
                return Response({"ok": False, "error": "Falló la generación de la serie", "log": log},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            df = pd.read_csv(pred_path)
            df = df.sort_values(["anio", "mes"])
            return Response({"ok": True, "scope": scope, "serie": serie, "count": len(df),
                             "items": df.to_dict(orient="records")})
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)