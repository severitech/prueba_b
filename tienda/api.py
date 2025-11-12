from rest_framework import viewsets, permissions
from .serializer import (
    CategoriaSerializer,
    ProductoSerializer,
    SubCategoriaSerializer,
    VentaSerializer,
    DetalleVentaSerializer,
    GarantiaSerializer,
    IngresoSerializer,
    DetalleIngresoSerializer,
    PromocionSerializer,
    ProductoPromocionSerializer,
    PagoSerializer,
    MantenimientoSerializer,
)
from tienda.models import (
    Categoria,
    Productos,
    SubCategoria,
    Venta,
    DetalleVenta,
    Garantia,
    Ingreso,
    DetalleIngreso,
    Promocion,
    ProductoPromocion,
    Pago,
    Mantenimiento,
)
from django_filters.rest_framework import DjangoFilterBackend


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.AllowAny]

class SubCategoriaViewSet(viewsets.ModelViewSet):
    queryset = SubCategoria.objects.all()
    serializer_class = SubCategoriaSerializer
    permission_classes = [permissions.AllowAny]

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Productos.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [permissions.AllowAny]

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    permission_classes = [permissions.AllowAny]

class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer
    permission_classes = [permissions.AllowAny]

class GarantiaViewSet(viewsets.ModelViewSet):
    queryset = Garantia.objects.all()
    serializer_class = GarantiaSerializer
    permission_classes = [permissions.AllowAny]

class IngresoViewSet(viewsets.ModelViewSet):
    queryset = Ingreso.objects.all()
    serializer_class = IngresoSerializer
    permission_classes = [permissions.AllowAny] 

class DetalleIngresoViewSet(viewsets.ModelViewSet):
    queryset = DetalleIngreso.objects.all()
    serializer_class = DetalleIngresoSerializer
    permission_classes = [permissions.AllowAny]

class PromocionViewSet(viewsets.ModelViewSet):
    queryset = Promocion.objects.all()
    serializer_class = PromocionSerializer
    permission_classes = [permissions.AllowAny]

class ProductoPromocionViewSet(viewsets.ModelViewSet):
    queryset = ProductoPromocion.objects.all()
    serializer_class = ProductoPromocionSerializer
    permission_classes = [permissions.AllowAny]
    # Agregar esto para habilitar filtros
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['promocion', 'producto']  # Puedes filtrar por ambos
    
class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [permissions.AllowAny]

class MantenimientoViewSet(viewsets.ModelViewSet):
    queryset = Mantenimiento.objects.all()
    serializer_class = MantenimientoSerializer
    permission_classes = [permissions.AllowAny]

