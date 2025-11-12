import sys
import os

# Añadir el directorio raíz al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configurar Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # Ajusta con el nombre de tu archivo de configuración
django.setup()

# Ahora puedes importar los modelos de tienda
from tienda.models import Venta, DetalleVenta, Productos
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error
from data_preprocessing import cargar_datos, preparar_datos

def entrenar_modelo():
    print("Cargando y preparando los datos...")
    # Cargar y preparar los datos
    df = cargar_datos()
    X, y = preparar_datos(df)

    # Verifica el tamaño de los datos antes de dividir
    print(f"Tamaño de X: {len(X)}")
    print(f"Tamaño de y: {len(y)}")

    # Dividir los datos en conjunto de entrenamiento y prueba
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Tamaño de X_train: {len(X_train)}")
    print(f"Tamaño de X_test: {len(X_test)}")

    # Verifica que tengamos suficientes datos en X_train
    if len(X_train) < 2:
        print("No hay suficientes datos para realizar validación cruzada.")
        return

    # Crear el modelo base
    modelo = RandomForestRegressor(random_state=42)

    # Definir los parámetros a probar con GridSearchCV
    parametros = {
        'n_estimators': [100, 200, 300],  # Número de árboles
        'max_depth': [10, 20, 30],  # Profundidad máxima de los árboles
        'min_samples_split': [2, 5, 10],  # Mínimos samples para dividir un nodo
        'min_samples_leaf': [1, 2, 4]  # Mínimos samples en una hoja
    }

    # Crear el objeto GridSearchCV
    grid_search = GridSearchCV(estimator=modelo, param_grid=parametros, cv=2, scoring='neg_mean_absolute_error')

    print("Entrenando el modelo con GridSearchCV...")
    # Entrenar el modelo con la búsqueda de los mejores parámetros
    grid_search.fit(X_train, y_train)

    # Ver los mejores parámetros encontrados
    print(f"Mejores parámetros: {grid_search.best_params_}")

    # Usar el mejor modelo
    modelo_optimo = grid_search.best_estimator_

    # Evaluar el modelo optimizado
    predicciones_optimas = modelo_optimo.predict(X_test)
    error_optimo = mean_absolute_error(y_test, predicciones_optimas)
    print(f"Error absoluto medio después de la optimización: {error_optimo}")

    # Guardar el modelo entrenado con los mejores parámetros
    print("Guardando el modelo entrenado...")
    joblib.dump(modelo_optimo, 'scikit_learn_ia/model/modelo_prediccion_ventas.joblib')
    print("Modelo guardado en 'scikit_learn_ia/model/modelo_prediccion_ventas.joblib'")

if __name__ == "__main__":
    entrenar_modelo()
