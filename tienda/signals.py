# tienda/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.core.management import call_command
import os


@receiver(post_migrate)
def load_fixtures(sender, **kwargs):
    if sender.name == "tienda":
        fixture_dir = "fixtures"
        if os.path.exists(fixture_dir):
            fixtures = [
                "categorias.json",
                "productos.json",
                "ingresos.json",
                "mantenimientos.json",
                "pagos.json",
                "prediccion.json",
                "promociones.json",
                "venta" "subcategorias.json",
                "detalle_ingreso.json",
                "detalle_venta.json",
                "promociones_productos.json",
            ]

            for fixture in fixtures:
                fixture_path = os.path.join(fixture_dir, fixture)
                if os.path.exists(fixture_path):
                    try:
                        call_command("loaddata", fixture_path)
                        print(f"✓ Fixture cargado: {fixture}")
                    except Exception as e:
                        print(f"✗ Error cargando {fixture}: {e}")
