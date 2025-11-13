from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
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
    FCMDevice,
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

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['categoria']

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Productos.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['subcategoria', 'estado']

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cliente']

class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['venta', 'producto', 'usuario']

class GarantiaViewSet(viewsets.ModelViewSet):
    queryset = Garantia.objects.all()
    serializer_class = GarantiaSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['producto', 'detalle_venta']

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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activo']

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


from tienda.serializer import FCMDeviceSerializer
from authz.models import Usuario as UsuarioModel
from core.notifications import enviar_tokens_push


class FCMDeviceRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Registrar o actualizar un token FCM desde la app móvil.

        Payload esperado: { "registration_id": "..", "tipo_dispositivo": "android" }
        """
        reg = request.data.get('registration_id') or request.data.get('token')
        tipo = request.data.get('tipo_dispositivo') or request.data.get('tipo') or 'android'
        if not reg:
            return Response({'detail': 'registration_id requerido'}, status=status.HTTP_400_BAD_REQUEST)

        usuario = None
        try:
            usuario = UsuarioModel.objects.get(user=request.user)
        except Exception:
            usuario = None

        obj, created = FCMDevice.objects.update_or_create(
            registration_id=reg,
            defaults={'usuario': usuario, 'tipo_dispositivo': tipo, 'activo': True}
        )
        serializer = FCMDeviceSerializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class FCMDeviceListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = FCMDevice.objects.all().order_by('-fecha_creacion')
        serializer = FCMDeviceSerializer(qs, many=True)
        return Response(serializer.data)


class FCMDeviceUnregisterView(APIView):
    """Desactiva un token FCM (logout).

    Request JSON: { "registration_id": "<FCM_TOKEN>" }
    Reglas:
    - Si el token pertenece al `Usuario` autenticado se marca `activo=False`.
    - Si el usuario es admin/staff puede desactivar cualquier token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reg = request.data.get('registration_id') or request.data.get('registrationId') or request.data.get('token')
        if not reg:
            return Response({'detail': 'registration_id requerido'}, status=status.HTTP_400_BAD_REQUEST)

        # Intentar obtener perfil Usuario
        usuario = None
        try:
            usuario = UsuarioModel.objects.get(user=request.user)
        except Exception:
            usuario = None

        qs = FCMDevice.objects.filter(registration_id=reg)
        if usuario:
            qs = qs.filter(usuario=usuario)
        else:
            # Si no hay perfil y no es staff, negar
            if not request.user.is_staff:
                return Response({'detail': 'No permitido'}, status=status.HTTP_403_FORBIDDEN)

        updated = qs.update(activo=False)
        if updated == 0:
            return Response({'detail': 'No se encontró el token para desactivar'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'detail': f'{updated} dispositivo(s) desactivado(s)'} , status=status.HTTP_200_OK)


class SendNotificationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Enviar notificación a usuarios o dispositivos.

        Payload: { title, body, user_ids: [1,2], device_ids: [1,2], broadcast: bool }
        """
        title = request.data.get('title') or request.data.get('titulo')
        body = request.data.get('body') or request.data.get('cuerpo')
        if not title or not body:
            return Response({'detail': 'title y body son requeridos'}, status=status.HTTP_400_BAD_REQUEST)

        user_ids = request.data.get('user_ids') or request.data.get('usuario_ids') or []
        device_ids = request.data.get('device_ids') or request.data.get('device_ids') or []
        broadcast = bool(request.data.get('broadcast'))

        tokens = []
        if broadcast:
            tokens = list(FCMDevice.objects.filter(activo=True, tipo_dispositivo='android').values_list('registration_id', flat=True))
        else:
            if user_ids:
                tokens += list(FCMDevice.objects.filter(usuario_id__in=user_ids, activo=True, tipo_dispositivo='android').values_list('registration_id', flat=True))
            if device_ids:
                tokens += list(FCMDevice.objects.filter(id__in=device_ids, activo=True, tipo_dispositivo='android').values_list('registration_id', flat=True))

        # eliminar duplicados
        tokens = list(dict.fromkeys(tokens))

        if not tokens:
            return Response({'detail': 'No se encontraron tokens destinatarios'}, status=status.HTTP_400_BAD_REQUEST)

        result = enviar_tokens_push(tokens, title, body)
        return Response(result)

