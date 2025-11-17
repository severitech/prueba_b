# railway_check.py
import os
import sys
from pathlib import Path

import django

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from scikit_learn_ia.paths import print_paths_banner
from django.conf import settings
from django.db import connection

def verificar_railway():
    print("🚄 Verificación del Entorno Railway")
    print("=" * 50)
    
    # Verificar paths
    print_paths_banner('🔍 Verificación en Railway')
    
    # Verificar configuración de base de datos
    print("\n📊 Configuración de Base de Datos:")
    db_config = settings.DATABASES['default']
    print(f"Motor: {db_config['ENGINE']}")
    print(f"Nombre DB: {db_config['NAME']}")
    print(f"Host: {db_config.get('HOST', 'localhost')}")
    
    # Verificar conexión a la base de datos
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            print(f"✅ PostgreSQL Version: {db_version[0]}")
    except Exception as e:
        print(f"❌ Error conectando a DB: {e}")
    
    # Verificar variables de entorno importantes
    print("\n🔧 Variables de Entorno:")
    important_vars = ['DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'DATABASE_URL']
    for var in important_vars:
        value = getattr(settings, var, 'No configurado')
        print(f"{var}: {value}")

if __name__ == "__main__":
    verificar_railway()