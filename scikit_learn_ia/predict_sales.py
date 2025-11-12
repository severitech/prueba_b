import pandas as pd
import joblib
import os
from datetime import datetime, timedelta

# ================================
# CONFIGURACIÓN
# ================================
MODEL_PATH = "scikit_learn_ia/model/modelo_prediccion_ventas.joblib"
OUTPUT_PATH = "scikit_learn_ia/datasets/predicciones_mensuales.csv"

# ================================
# CARGA DEL MODELO
# ================================
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"❌ No se encontró el modelo en {MODEL_PATH}")

modelo = joblib.load(MODEL_PATH)

# ================================
# GENERACIÓN DE DATOS FUTUROS
# ================================
# Generar 12 meses futuros a partir del mes actual
hoy = datetime.now()
fechas_futuras = [hoy + timedelta(days=30 * i) for i in range(12)]

# Crear DataFrame con las mismas columnas y orden que en el entrenamiento
df_pred = pd.DataFrame({
    "dia_del_anio": [f.timetuple().tm_yday for f in fechas_futuras],
    "mes": [f.month for f in fechas_futuras]
})


# ================================
# PREDICCIÓN CON EL MODELO
# ================================
predicciones = modelo.predict(df_pred)

# Convertir en DataFrame mensual
df_resultado = pd.DataFrame({
    "mes": [f.strftime("%Y-%m") for f in fechas_futuras],
    "ventas_estimadas": predicciones
})

# ================================
# AJUSTE DE ESCALA
# ================================
# Ajustamos las predicciones al nivel real del dataset histórico
# (escala diaria -> mensual total)
FACTOR_ESCALA = 3.0  # Ajusta si tus datos cambian en el futuro
df_resultado["ventas_estimadas"] = df_resultado["ventas_estimadas"] * FACTOR_ESCALA

# Asegurar valores positivos
df_resultado["ventas_estimadas"] = df_resultado["ventas_estimadas"].clip(lower=0)

# ================================
# SALIDA
# ================================
# Mostrar primeras filas
print("📈 Predicciones de ventas por MES (ajustadas a escala real):\n")
print(df_resultado.round(2))

# Guardar a CSV
df_resultado.to_csv(OUTPUT_PATH, index=False)
print(f"\n✅ Archivo mensual guardado en: {OUTPUT_PATH}")

