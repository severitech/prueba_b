# scikit_learn_ia/views.py
import os
import json
import subprocess, sys
from datetime import datetime

import pandas as pd
from django.utils.http import http_date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.http import FileResponse, HttpResponseNotFound

# 🔗 RUTAS UNIFICADAS (local / Railway)
from scikit_learn_ia.paths import (
    BASE_DIR, DATA_DIR, MODEL_DIR,
    VENTAS_CSV, DETALLES_CSV, PRED_TOTALES_CSV,
    METADATA_CANT, PDF_PATH, XLSX_PATH,
    panel_series_summary, panel_pred_file,
)

VALID_SCOPES = {"categoria", "producto", "cliente"}

# ---------- Helpers de tiempo ----------
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
        df["anio"] = df["fecha"].dt.year
        df["mes"] = df["fecha"].dt.month
        df["periodo"] = df["fecha"].dt.strftime("%Y-%m")
    else:
        if "anio" in df.columns and "mes" in df.columns:
            df["periodo"] = df.apply(lambda r: f"{int(r['anio'])}-{int(r['mes']):02d}", axis=1)
    return df

# ---------- Helper ejecución de scripts ----------
def _run_script(rel_path: str) -> tuple[bool, str]:
    """
    Ejecuta un script Python como MÓDULO (python -m paquete.modulo) para que funcionen los imports.
    Acepta entradas tipo 'scikit_learn_ia/generar_datos_sinteticos.py' o 'scikit_learn_ia/predict_sales_panel.py'.
    """
    module = rel_path.replace("\\", "/")
    if module.endswith(".py"):
        module = module[:-3]
    module = module.replace("/", ".")

    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONPATH": str(BASE_DIR),
        "PYTHONIOENCODING": "utf-8",
    }
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", module],
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

def _run_script_args(rel_path: str, args: list[str]) -> tuple[bool, str]:
    script_path = BASE_DIR / rel_path
    if not script_path.exists():
        return False, f"[ERROR] Script no encontrado: {script_path}"
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(BASE_DIR),
    }
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script_path), *args],
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

def _run_module(modname: str, *args: str) -> tuple[bool, str]:
    """Ejecuta un módulo con -m usando el mismo venv, UTF-8 y PYTHONPATH correcto."""
    try:
        env = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(BASE_DIR),
        }
        proc = subprocess.run(
            [sys.executable, "-m", modname, *[str(a) for a in args]],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return proc.returncode == 0, out[-8000:]
    except Exception as e:
        return False, f"[EXCEPTION] {e}"

# ---------- Slug consistente con predict_sales_panel ----------
import re, unicodedata
def _slug(value) -> str:
    s = str(value)
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    s = re.sub(r"[^A-Za-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "serie"

# ---------- Views ----------
class IAHealthView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({
            "ok": True,
            "time_utc": datetime.utcnow().isoformat() + "Z",
            "ventas_csv": VENTAS_CSV.exists(),
            "detalles_csv": DETALLES_CSV.exists(),
            "predicciones_csv": PRED_TOTALES_CSV.exists(),
            "metadata_json": METADATA_CANT.exists(),
            "paths": {
                "BASE_DIR": str(BASE_DIR),
                "DATA_DIR": str(DATA_DIR),
                "MODEL_DIR": str(MODEL_DIR),
            }
        })

class GenerarDatosSinteticosView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ok, out = _run_script("scikit_learn_ia/generar_datos_sinteticos.py")
        status_code = status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({"ok": ok, "log": out[-8000:]}, status=status_code)

class EntrenarModeloCantidadesView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ok, out = _run_script("scikit_learn_ia/train_model_cantidades.py")
        payload = {"ok": ok, "log": out[-8000:]}
        if METADATA_CANT.exists():
            try:
                payload["metadata"] = json.loads(METADATA_CANT.read_text(encoding="utf-8"))
            except Exception as e:
                payload["metadata_error"] = str(e)
        status_code = status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(payload, status=status_code)

class PredecirCantidadesView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ok, out = _run_script("scikit_learn_ia/predict_sales_cantidades.py")
        payload = {"ok": ok, "log": out[-8000:]}
        if PRED_TOTALES_CSV.exists():
            try:
                df = pd.read_csv(PRED_TOTALES_CSV)
                payload["rows"] = len(df)
                payload["preview"] = df.head(12).to_dict(orient="records")
            except Exception as e:
                payload["csv_error"] = str(e)
        status_code = status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(payload, status=status_code)

class PrediccionesListView(APIView):
    """
    GET /ia/predicciones?anio=2025
    GET /ia/predicciones?anio=2025&mes=11
    """
    permission_classes = [AllowAny]
    def get(self, request):
        if not PRED_TOTALES_CSV.exists():
            return Response({"ok": False, "error": "No existe el CSV de predicciones."},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            df = pd.read_csv(PRED_TOTALES_CSV)
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

            df_mes = df_ventas[(df_ventas["anio"] == anio) & (df_ventas["mes"] == mes)]
            total_ventas = float(df_mes["total"].sum()) if "total" in df_mes.columns else None
            cant_ventas = int(df_mes["id"].count()) if "id" in df_mes.columns else None

            nivel_item = None
            if DETALLES_CSV.exists():
                try:
                    df_det = pd.read_csv(DETALLES_CSV)
                    df_det = df_det.merge(
                        df_ventas[["id", "anio", "mes", "periodo"]],
                        left_on="venta_id", right_on="id", how="inner"
                    )
                    df_det = add_periodo_fields(df_det)
                    df_det_mes = df_det[(df_det["anio"] == anio) & (df_det["mes"] == mes)]
                    cantidad_items = int(df_det_mes["cantidad"].sum()) if "cantidad" in df_det_mes.columns else None
                    total_items = float(df_det_mes["subtotal"].sum()) if "subtotal" in df_det_mes.columns else None
                    nivel_item = {"cantidad_items": cantidad_items, "monto_items": total_items}
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
    permission_classes = [AllowAny]
    def get(self, request):
        if not PDF_PATH.exists():
            if not PRED_TOTALES_CSV.exists():
                return Response({"ok": False, "error": "No hay predicciones CSV para generar el PDF."},
                                status=status.HTTP_404_NOT_FOUND)
            from scikit_learn_ia.reportes.generar_reporte_pdf import crear_reporte_pdf
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
        if not PRED_TOTALES_CSV.exists():
            return Response({"ok": False, "error": "No hay predicciones CSV para generar el PDF."},
                            status=status.HTTP_404_NOT_FOUND)
        from scikit_learn_ia.reportes.generar_reporte_pdf import crear_reporte_pdf
        ok = crear_reporte_pdf(desde_csv=True)
        if not ok or not PDF_PATH.exists():
            return Response({"ok": False, "error": "Falló la generación del PDF."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        resp = FileResponse(open(PDF_PATH, "rb"), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{PDF_PATH.name}"'
        resp["Last-Modified"] = http_date(PDF_PATH.stat().st_mtime)
        return resp

class ReporteExcelView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        if not XLSX_PATH.exists():
            if not PRED_TOTALES_CSV.exists():
                return Response({"ok": False, "error": "No hay predicciones CSV para generar el Excel."},
                                status=status.HTTP_404_NOT_FOUND)
            from scikit_learn_ia.reportes.generar_reporte_excel import crear_reporte_excel
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
        if not PRED_TOTALES_CSV.exists():
            return Response({"ok": False, "error": "No hay predicciones CSV para generar el Excel."},
                            status=status.HTTP_404_NOT_FOUND)
        from scikit_learn_ia.reportes.generar_reporte_excel import crear_reporte_excel
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

# ---------- Panel: listar series ----------
class PanelSeriesListView(APIView):
    """
    GET /api/ia/panel/series/?scope=categoria|producto|cliente
    """
    permission_classes = [AllowAny]
    def get(self, request):
        scope = str(request.query_params.get("scope", "")).lower().strip()
        if scope not in VALID_SCOPES:
            return Response({"ok": False, "error": f"scope inválido. Usa {sorted(VALID_SCOPES)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        series_summary_csv = panel_series_summary(scope)
        if not series_summary_csv.exists():
            return Response({"ok": False, "error": f"No existe {series_summary_csv.name}. Entrena primero."},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            df = pd.read_csv(series_summary_csv)
            key_cols = [c for c in df.columns if c not in {"puntos", "activos", "total", "media", "std"}]
            if not key_cols:
                return Response({"ok": False, "error": "No se pudo detectar la columna identificadora."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            key = key_cols[0]
            df = df.sort_values("total", ascending=False)
            items = df[[key, "puntos", "activos", "total", "media", "std"]].to_dict(orient="records")
            return Response({"ok": True, "scope": scope, "key": key, "count": len(items), "items": items})
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ---------- Panel: obtener predicciones ----------
class PanelPrediccionesView(APIView):
    """
    GET /api/ia/panel/predicciones/?scope=categoria|producto|cliente&serie=<id_o_nombre>&force=1
      - Sin 'serie': devuelve/produce el agregado TOP (pred_{scope}_all.csv)
      - Con 'serie': devuelve/produce pred_{scope}_{slug(serie)}.csv
    """
    permission_classes = [AllowAny]

    def _run_predict(self, scope: str, serie: str | None):
        script = BASE_DIR / "scikit_learn_ia" / "predict_sales_panel.py"
        if not script.exists():
            return False, f"No existe el script de predicción: {script}"
        cmd = [sys.executable, str(script), scope]
        if serie is not None:
            cmd.append(str(serie))
        try:
            env = {
                **os.environ,
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONPATH": str(BASE_DIR),
            }
            proc = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            ok = (proc.returncode == 0)
            log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            return ok, log[-8000:]
        except Exception as e:
            return False, f"Error ejecutando predict: {e}"

    def get(self, request):
        scope = str(request.query_params.get("scope", "")).lower().strip()
        serie = request.query_params.get("serie", None)
        # force se mantiene por compatibilidad, pero ya no es requerido
        # si falta el CSV, se autogenera igual
        # force = str(request.query_params.get("force", "0")).strip() in {"1", "true", "True"}

        if scope not in VALID_SCOPES:
            return Response({"ok": False, "error": f"scope inválido. Usa {sorted(VALID_SCOPES)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Sin serie -> agregado TOP
        if not serie:
            agg_path = panel_pred_file(scope, None)  # pred_{scope}_all.csv
            if not agg_path.exists():
                ok, log = self._run_predict(scope, None)
                if not ok or not agg_path.exists():
                    return Response({"ok": False, "error": f"Falló la generación agregada para {scope}", "log": log},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                df = pd.read_csv(agg_path).sort_values(["anio", "mes"])
                return Response({"ok": True, "scope": scope, "aggregate": True, "count": len(df),
                                 "items": df.to_dict(orient="records")})
            except Exception as e:
                return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Con serie -> normaliza tipo para producto/cliente; para categoría usa slug
        serie_key = serie
        if scope in {"producto", "cliente"}:
            try:
                serie_key = int(serie_key)
            except:
                return Response({"ok": False, "error": f"Para scope={scope}, 'serie' debe ser entero."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            serie_key = _slug(serie_key)

        pred_path = panel_pred_file(scope, serie_key)

        if not pred_path.exists():
            # IMPORTANTE: al script le pasamos el valor ORIGINAL (no slug),
            # porque él se encarga de sluggear / castear internamente al guardar.
            ok, log = self._run_predict(scope, serie)
            if not ok or not pred_path.exists():
                return Response({"ok": False, "error": "Falló la generación de la serie", "log": log},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            df = pd.read_csv(pred_path).sort_values(["anio", "mes"])
            return Response({"ok": True, "scope": scope, "serie": serie, "count": len(df),
                             "items": df.to_dict(orient="records")})
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- agrega esta vista ---
class EntrenarPanelView(APIView):
    """
    POST /api/ia/panel/entrenar/           -> entrena TODOS (producto, categoria, cliente)
    POST /api/ia/panel/entrenar/?scope=... -> entrena uno: producto|categoria|cliente
    """
    permission_classes = [AllowAny]

    def post(self, request):
        scope = str(request.query_params.get("scope", "")).lower().strip()
        if scope and scope not in VALID_SCOPES:
            return Response({"ok": False, "error": f"scope inválido. Usa {sorted(VALID_SCOPES)}"},
                            status=status.HTTP_400_BAD_REQUEST)
        args = [scope] if scope else []
        ok, out = _run_module("scikit_learn_ia.train_model_panel", *args)
        status_code = status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({"ok": ok, "log": out[-8000:]}, status=status_code)

class PanelHealthView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        scopes = sorted(list(VALID_SCOPES))
        res = {}
        for s in scopes:
            res[s] = {
                "modelo": (MODEL_DIR / f"panel_{s}_cantidades.joblib").exists(),
                "metrics_csv": (DATA_DIR / f"panel_{s}_metrics.csv").exists(),
                "series_summary_csv": (DATA_DIR / f"panel_{s}_series_summary.csv").exists(),
            }
        return Response({"ok": True, "scopes": res})


# ---------- Panel: descargar reporte (CSV/PDF/Excel) ----------
class PanelDescargarReporteView(APIView):
    """
    GET /api/ia/panel/descargar/?scope=producto[&serie=...][&formato=pdf|excel|csv][&force=1]

    - Sin 'serie': descarga el agregado TOP (pred_{scope}_all.csv)
    - Con 'serie': descarga pred_{scope}_{serie}.csv
    - 'formato' permite obtener PDF o Excel a partir del CSV.
    """
    permission_classes = [AllowAny]

    def _run_predict(self, scope: str, serie: str | None):
        script = BASE_DIR / "scikit_learn_ia" / "predict_sales_panel.py"
        if not script.exists():
            return False, f"No existe el script de predicción: {script}"

        cmd = [sys.executable, str(script), scope]
        if serie:
            cmd.append(str(serie))
        env = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(BASE_DIR),
        }
        try:
            proc = subprocess.run(
                cmd, cwd=str(BASE_DIR), capture_output=True,
                text=True, encoding="utf-8", errors="replace", env=env
            )
            ok = (proc.returncode == 0)
            log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            return ok, log[-6000:]
        except Exception as e:
            return False, str(e)

    def get(self, request):
        scope = str(request.query_params.get("scope", "")).lower().strip()
        serie = request.query_params.get("serie", None)
        formato = str(request.query_params.get("formato", "csv")).lower().strip()
        force = str(request.query_params.get("force", "0")).strip() in {"1", "true", "True"}

        if scope not in VALID_SCOPES:
            return Response({"ok": False, "error": f"Scope inválido. Usa {sorted(VALID_SCOPES)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Resolución de archivo CSV base
        if not serie:
            csv_path = panel_pred_file(scope, None)
            if not csv_path.exists() and not force:
                ok, log = self._run_predict(scope, None)
                if not ok or not csv_path.exists():
                    return Response({"ok": False, "error": "No existe agregado y falló generación", "log": log},
                                    status=status.HTTP_404_NOT_FOUND)
        else:
            serie_key = serie
            if scope in {"producto", "cliente"}:
                try:
                    serie_key = int(serie_key)
                except:
                    return Response({"ok": False, "error": f"Para scope={scope}, 'serie' debe ser entero."},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                serie_key = _slug(serie_key)
            csv_path = panel_pred_file(scope, serie_key)
            if not csv_path.exists() and not force:
                ok, log = self._run_predict(scope, serie)
                if not ok or not csv_path.exists():
                    return Response({"ok": False, "error": "No existe serie y falló generación", "log": log},
                                    status=status.HTTP_404_NOT_FOUND)

        if not csv_path.exists():
            return Response({"ok": False, "error": f"No existe archivo {csv_path.name}"},
                            status=status.HTTP_404_NOT_FOUND)

        # === FORMATO CSV (por defecto) ===
        if formato == "csv":
            resp = FileResponse(open(csv_path, "rb"), content_type="text/csv; charset=utf-8")
            resp["Content-Disposition"] = f'attachment; filename="{csv_path.name}"'
            return resp

        # === FORMATO EXCEL ===
        elif formato in {"excel", "xlsx"}:
            df = pd.read_csv(csv_path)
            out_path = csv_path.with_suffix(".xlsx")
            df.to_excel(out_path, index=False)
            resp = FileResponse(open(out_path, "rb"),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            resp["Content-Disposition"] = f'attachment; filename="{out_path.name}"'
            return resp

        # === FORMATO PDF ===
        elif formato == "pdf":
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet

            df = pd.read_csv(csv_path)
            pdf_path = csv_path.with_suffix(".pdf")

            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
            styles = getSampleStyleSheet()
            elements = [Paragraph(f"Predicciones - {scope.upper()}", styles["Title"])]

            # Cabecera + datos
            data = [df.columns.tolist()] + df.values.tolist()
            t = Table(data, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            elements.append(t)
            doc.build(elements)

            resp = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="{pdf_path.name}"'
            return resp

        else:
            return Response({"ok": False, "error": f"Formato inválido '{formato}'. Usa: csv, pdf o excel"},
                            status=status.HTTP_400_BAD_REQUEST)

# ---------- Ventas históricas (por período, total/producto/cliente/categoria) ----------
class VentasHistoricasView(APIView):
    """
    GET /api/ia/ventas-historicas/?scope=total|producto|cliente|categoria[&anio=2025][&mes=11][&producto_id=...][&cliente_id=...][&categoria=...]
    
    - scope=total: agrupa por anio, mes desde ventas.csv
    - scope=cliente: agrupa por anio, mes, usuario_id (desde ventas.csv)
    - scope=producto: usa detalles_venta.csv + merge(fecha) con ventas.csv
    - scope=categoria: requiere columna 'categoria' en detalles_venta.csv (si no, devuelve error)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        scope = str(request.query_params.get("scope", "total")).lower().strip()
        anio = request.query_params.get("anio")
        mes = request.query_params.get("mes")
        producto_id = request.query_params.get("producto_id")
        cliente_id = request.query_params.get("cliente_id")
        categoria = request.query_params.get("categoria")

        if scope not in {"total", "producto", "cliente", "categoria"}:
            return Response({"ok": False, "error": "scope inválido. Usa: total, producto, cliente, categoria"},
                            status=status.HTTP_400_BAD_REQUEST)

        if not VENTAS_CSV.exists():
            return Response({"ok": False, "error": "No existe ventas.csv"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # CARGA VENTAS
            dfv = pd.read_csv(VENTAS_CSV)
            dfv = add_periodo_fields(dfv)

            # FILTROS BÁSICOS
            if anio: dfv = dfv[dfv["anio"] == int(anio)]
            if mes:  dfv = dfv[dfv["mes"] == int(mes)]

            # ===== TOTAL / CLIENTE desde ventas.csv =====
            if scope in {"total", "cliente"}:
                if scope == "total":
                    # totales por periodo
                    grp = dfv.groupby(["anio", "mes"], as_index=False).agg({
                        "id": "count",
                        **({"total": "sum"} if "total" in dfv.columns else {})
                    }).rename(columns={"id": "cantidad_ventas", "total": "monto_total"})
                    grp = grp.sort_values(["anio", "mes"])
                    return Response({
                        "ok": True,
                        "scope": scope,
                        "group_key": None,
                        "count": len(grp),
                        "items": grp.to_dict(orient="records")
                    })

                else:  # cliente
                    if "usuario_id" not in dfv.columns:
                        return Response({"ok": False, "error": "ventas.csv no tiene columna 'usuario_id'"},
                                        status=status.HTTP_400_BAD_REQUEST)
                    if cliente_id:
                        dfv = dfv[dfv["usuario_id"] == int(cliente_id)]

                    grp = dfv.groupby(["anio", "mes", "usuario_id"], as_index=False).agg({
                        "id": "count",
                        **({"total": "sum"} if "total" in dfv.columns else {})
                    }).rename(columns={"id": "cantidad_ventas", "total": "monto_total"})
                    grp = grp.sort_values(["usuario_id", "anio", "mes"])
                    return Response({
                        "ok": True,
                        "scope": scope,
                        "group_key": "usuario_id",
                        "count": len(grp),
                        "items": grp.to_dict(orient="records")
                    })

            # ===== PRODUCTO / CATEGORIA requieren DETALLES + fecha =====
            if not DETALLES_CSV.exists():
                return Response({"ok": False, "error": "No existe detalles_venta.csv para ese scope"},
                                status=status.HTTP_404_NOT_FOUND)

            dfd = pd.read_csv(DETALLES_CSV)
            # merge para heredar periodo desde venta_id
            cols_keep = ["id", "anio", "mes", "periodo"]
            dfm = dfd.merge(dfv[cols_keep], left_on="venta_id", right_on="id", how="inner", suffixes=("", "_venta"))
            # limpiar id duplicado del merge
            if "id_venta" in dfm.columns:
                dfm = dfm.rename(columns={"id_venta": "venta_id_ref"})
            # métricas seguras
            if "cantidad" not in dfm.columns:
                dfm["cantidad"] = 0
            if "subtotal" not in dfm.columns:
                dfm["subtotal"] = 0.0

            if anio: dfm = dfm[dfm["anio"] == int(anio)]
            if mes:  dfm = dfm[dfm["mes"] == int(mes)]

            if scope == "producto":
                if "producto_id" not in dfm.columns:
                    return Response({"ok": False, "error": "detalles_venta.csv no tiene 'producto_id'"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if producto_id:
                    dfm = dfm[dfm["producto_id"] == int(producto_id)]
                grp = dfm.groupby(["anio", "mes", "producto_id"], as_index=False).agg({
                    "cantidad": "sum",
                    "subtotal": "sum"
                }).rename(columns={"subtotal": "monto_items"})
                grp = grp.sort_values(["producto_id", "anio", "mes"])
                return Response({
                    "ok": True,
                    "scope": scope,
                    "group_key": "producto_id",
                    "count": len(grp),
                    "items": grp.to_dict(orient="records")
                })

            else:  # categoria
                if "categoria" not in dfm.columns:
                    return Response({"ok": False, "error": "detalles_venta.csv no tiene columna 'categoria'"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if categoria:
                    dfm = dfm[dfm["categoria"].astype(str).str.lower() == str(categoria).lower()]
                grp = dfm.groupby(["anio", "mes", "categoria"], as_index=False).agg({
                    "cantidad": "sum",
                    "subtotal": "sum"
                }).rename(columns={"subtotal": "monto_items"})
                grp = grp.sort_values(["categoria", "anio", "mes"])
                return Response({
                    "ok": True,
                    "scope": scope,
                    "group_key": "categoria",
                    "count": len(grp),
                    "items": grp.to_dict(orient="records")
                })

        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
