# debug_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from scikit_learn_ia.paths import (
    DATA_DIR,
    MODEL_DIR,
    VENTAS_CSV,
    DETALLES_CSV,
    PRED_TOTALES_CSV,
    MODEL_CANTIDADES,
    METADATA_CANT,
    PDF_PATH,
    XLSX_PATH
)


@csrf_exempt
def debug_volumen(request):
    """
    Vista temporal para verificar archivos dentro del volumen Railway.
    Acceder con:
        https://TU-APP.up.railway.app/debug/volumen/?secret=12345
    """
    # Protección básica (puedes cambiar el secret)
    if request.GET.get("secret") != "12345":
        return JsonResponse({"error": "Forbidden"}, status=403)

    def listar(ruta):
        try:
            if ruta.exists():
                return [f.name for f in ruta.iterdir()]
            return ["DIRECTORIO NO EXISTE"]
        except Exception as e:
            return [f"ERROR: {e}"]

    return JsonResponse({
        "DATA_DIR": str(DATA_DIR),
        "DATA_DIR_exists": DATA_DIR.exists(),
        "DATA_DIR_files": listar(DATA_DIR),

        "MODEL_DIR": str(MODEL_DIR),
        "MODEL_DIR_exists": MODEL_DIR.exists(),
        "MODEL_DIR_files": listar(MODEL_DIR),

        "VENTAS_CSV_exists": VENTAS_CSV.exists(),
        "DETALLES_CSV_exists": DETALLES_CSV.exists(),
        "PRED_TOTALES_CSV_exists": PRED_TOTALES_CSV.exists(),

        "MODEL_CANTIDADES_exists": MODEL_CANTIDADES.exists(),
        "METADATA_CANT_exists": METADATA_CANT.exists(),

        "PDF_predicciones_exists": PDF_PATH.exists(),
        "XLSX_predicciones_exists": XLSX_PATH.exists(),
    })
