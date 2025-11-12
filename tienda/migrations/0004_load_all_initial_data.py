# tienda/migrations/0004_load_all_initial_data.py
from django.db import migrations
from django.core.management import call_command


def load_all_initial_data(apps, schema_editor):
    # Cargar en orden correcto (por dependencias)
    fixtures = [
        'tienda/fixtures/categorias.json',      
        'tienda/fixtures/subcategorias.json',   
        'tienda/fixtures/productos.json',       
        'tienda/fixtures/ingresos.json',         
        'tienda/fixtures/prediccion.json',
        'tienda/fixtures/promociones.json',
        'tienda/fixtures/venta.json',
        'tienda/fixtures/detalle_ingreso.json',
        'tienda/fixtures/detalle_venta.json',
        'tienda/fixtures/promociones_productos.json',  
        'tienda/fixtures/mantenimiento.json',    
        'tienda/fixtures/pagos.json',    
    ]
    
    for fixture in fixtures:
        call_command('loaddata', fixture)


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0003_productos_imagenes'),  # Tu última migración
    ]

    operations = [
        migrations.RunPython(load_all_initial_data, reverse_code=migrations.RunPython.noop),
    ]