# scikit_learn_ia/reportes.py
import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
from pathlib import Path

# Rutas base (ajustadas a tu estructura actual)
# BASE_DIR = Path(__file__).resolve().parent.parent
# DATASET_PATH = BASE_DIR / "datasets" / "predicciones_cantidades_mensuales.csv"
# OUTPUT_PATH = BASE_DIR / "datasets" / "reporte_predicciones.pdf"
# 👉 Importamos la ruta correcta desde paths.py
from scikit_learn_ia.paths import DATA_DIR

DATASET_PATH = DATA_DIR / "predicciones_cantidades_mensuales.csv"
OUTPUT_PATH  = DATA_DIR / "reporte_predicciones.pdf"


def crear_reporte_pdf(desde_csv: bool = True, predicciones=None):
    """
    Genera un reporte PDF con las predicciones de demanda (productos/mes).
    Si desde_csv=True, lee automáticamente el archivo de predicciones generado por IA.
    """
    try:
        # Cargar predicciones desde CSV si no se pasan manualmente
        if desde_csv:
            if not DATASET_PATH.exists():
                raise FileNotFoundError(f"No se encontró el archivo: {DATASET_PATH}")
            df = pd.read_csv(DATASET_PATH)
            df = df.sort_values(["anio", "mes"])
            predicciones = df.to_dict(orient="records")

        if not predicciones:
            raise ValueError("No hay datos de predicciones disponibles.")

        # Crear PDF
        c = canvas.Canvas(str(OUTPUT_PATH), pagesize=letter)
        width, height = letter

        # Encabezado
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.darkblue)
        c.drawString(80, height - 60, "📊 Reporte de Predicciones de Demanda de Productos")
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(80, height - 80, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        # Línea decorativa
        c.setStrokeColor(colors.gray)
        c.line(80, height - 90, width - 80, height - 90)

        # Tabla de datos
        y = height - 120
        c.setFont("Helvetica", 10)
        c.drawString(80, y, "Mes")
        c.drawString(160, y, "Predicción")
        c.drawString(270, y, "Rango Confianza")
        c.drawString(420, y, "Confianza (%)")
        y -= 15
        c.line(80, y, width - 80, y)
        y -= 10

        for p in predicciones:
            if y < 100:  # salto de página
                c.showPage()
                y = height - 100
                c.setFont("Helvetica", 10)

            mes = int(p.get("mes", 0))
            anio = int(p.get("anio", 0))
            pred = int(p.get("cantidad_predicha", 0))
            min_v = int(p.get("minimo", 0))
            max_v = int(p.get("maximo", 0))
            conf = round(float(p.get("confianza", 0)) * 100, 1)

            c.drawString(80, y, f"{anio}-{mes:02d}")
            c.drawString(160, y, f"{pred:,}".replace(",", "."))
            c.drawString(270, y, f"{min_v:,}-{max_v:,}".replace(",", "."))
            c.drawString(420, y, f"{conf}%")
            y -= 18

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.gray)
        c.drawString(80, 60, "SmartSales360 - Módulo de Predicción de Demanda 📦")
        c.save()

        print(f"✅ Reporte PDF generado correctamente: {OUTPUT_PATH}")
        return True

    except Exception as e:
        print(f"❌ Error al generar el reporte PDF: {e}")
        return False


# Ejemplo rápido si lo ejecutas directamente:
if __name__ == "__main__":
    crear_reporte_pdf()
