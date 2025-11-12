from rest_framework import generics, permissions
from .models import Venta
from .serializer import VentaSerializer

class MisVentasList(generics.ListAPIView):
    serializer_class = VentaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from authz.models import Usuario
        try:
            perfil = Usuario.objects.get(user=self.request.user)
            return Venta.objects.filter(usuario=perfil)
        except Usuario.DoesNotExist:
            return Venta.objects.none()