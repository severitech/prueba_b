from datetime import datetime, timedelta
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from tienda.models import Venta, Usuario

class Command(BaseCommand):
    help = "Generar datos sintéticos de ventas distribuidos en el tiempo"

    def add_arguments(self, parser):
        parser.add_argument('--cantidad', type=int, default=8000)
        parser.add_argument('--inicio', type=str, default='2020-01-01')
        parser.add_argument('--fin', type=str, default='2025-12-31')

    def handle(self, *args, **kwargs):
        cantidad = kwargs['cantidad']
        inicio_str = kwargs['inicio']
        fin_str = kwargs['fin']

        try:
            fecha_inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
            fecha_fin = datetime.strptime(fin_str, '%Y-%m-%d')
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Error en formato de fecha: {e}"))
            return

        if fecha_inicio > fecha_fin:
            self.stdout.write(self.style.ERROR("Error: fecha_inicio > fecha_fin"))
            return

        usuarios = list(Usuario.objects.all())
        if not usuarios:
            self.stdout.write(self.style.ERROR("❌ No hay usuarios en la base de datos"))
            return

        self.generar_ventas_simple(cantidad, fecha_inicio, fecha_fin, usuarios)

    @transaction.atomic
    def generar_ventas_simple(self, cantidad, fecha_inicio, fecha_fin, usuarios):
        """Versión simplificada y robusta"""
        
        delta_days = (fecha_fin - fecha_inicio).days
        self.stdout.write(f"📅 Generando {cantidad} ventas entre {fecha_inicio.date()} y {fecha_fin.date()} ({delta_days} días)")

        ventas = []
        for i in range(cantidad):
            # Fecha aleatoria en el rango
            dias_aleatorios = random.randint(0, delta_days)
            fecha_venta = fecha_inicio + timedelta(days=dias_aleatorios)
            
            # Hora aleatoria del día
            hora = random.randint(8, 20)
            minuto = random.randint(0, 59)
            segundo = random.randint(0, 59)
            fecha_venta = fecha_venta.replace(hour=hora, minute=minuto, second=segundo)
            
            usuario = random.choice(usuarios)
            
            # Monto aleatorio entre 50 y 5000
            total = round(random.uniform(50, 5000), 2)
            
            # Estado con probabilidades realistas
            estado = random.choices(
                ['Pagado', 'Pendiente', 'Cancelado'],
                weights=[80, 15, 5]  # 80% Pagado, 15% Pendiente, 5% Cancelado
            )[0]
            
            venta = Venta(
                usuario=usuario,
                fecha=fecha_venta,
                total=total,
                estado=estado
            )
            ventas.append(venta)

            # Mostrar progreso
            if (i + 1) % 1000 == 0:
                self.stdout.write(f"🔄 {i + 1}/{cantidad} ventas generadas...")

        # Crear todas las ventas de una vez
        self.stdout.write("💾 Guardando ventas en la base de datos...")
        Venta.objects.bulk_create(ventas, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ ¡Éxito! Generadas {cantidad} ventas desde {fecha_inicio.date()} hasta {fecha_fin.date()}"
            )
        )

        # Mostrar resumen
        self.mostrar_resumen()

    def mostrar_resumen(self):
        """Mostrar resumen básico"""
        from django.db.models import Count
        
        total = Venta.objects.count()
        por_estado = Venta.objects.values('estado').annotate(total=Count('id'))
        
        self.stdout.write("\n📊 RESUMEN:")
        self.stdout.write(f"Total de ventas en sistema: {total}")
        self.stdout.write("Distribución por estado:")
        for item in por_estado:
            self.stdout.write(f"  {item['estado']}: {item['total']}")