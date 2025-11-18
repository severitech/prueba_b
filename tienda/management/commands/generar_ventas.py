import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from tienda.models import Venta, Usuario  # Ajusta los nombres de tus modelos

class Command(BaseCommand):
    help = "Generar datos sintéticos para la tabla de ventas en un rango de fechas"

    def add_arguments(self, parser):
        parser.add_argument('--cantidad', type=int, default=8000, help='Cantidad de ventas a generar')
        parser.add_argument('--fecha_inicio', type=str, default='2020-01-01', help='Fecha de inicio (YYYY-MM-DD)')
        parser.add_argument('--fecha_fin', type=str, default='2025-11-17', help='Fecha de fin (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        cantidad = kwargs['cantidad']
        fecha_inicio = datetime.strptime(kwargs['fecha_inicio'], '%Y-%m-%d')
        fecha_fin = datetime.strptime(kwargs['fecha_fin'], '%Y-%m-%d')
        usuarios = list(Usuario.objects.all())  # Asegúrate de tener usuarios en tu base de datos

        if not usuarios:
            self.stdout.write(self.style.ERROR("No hay usuarios en la base de datos."))
            return

        ventas = []
        for _ in range(cantidad):
            usuario = random.choice(usuarios)
            delta = (fecha_fin - fecha_inicio).days
            fecha = fecha_inicio + timedelta(days=random.randint(0, delta))
            total = round(random.uniform(10, 1000), 2)  # Total entre 10 y 1000

            venta = Venta(
                usuario=usuario,
                fecha=fecha,
                total=total,
            )
            ventas.append(venta)

        Venta.objects.bulk_create(ventas)
        self.stdout.write(self.style.SUCCESS(f"Se generaron {cantidad} ventas entre {fecha_inicio.date()} y {fecha_fin.date()}."))