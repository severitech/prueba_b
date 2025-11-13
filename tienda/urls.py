from django.urls import include, path
from rest_framework import routers

from . import views


from .api import (
    CategoriaViewSet,
    SubCategoriaViewSet,
    ProductoViewSet,
    VentaViewSet,
    DetalleVentaViewSet,
    GarantiaViewSet,
    IngresoViewSet,
    DetalleIngresoViewSet,
    PromocionViewSet,
    ProductoPromocionViewSet,
    PagoViewSet,
    MantenimientoViewSet,
    FCMDeviceRegisterView,
    FCMDeviceListView,
    SendNotificationView,
)


router = routers.DefaultRouter()
router.register(r"categorias", CategoriaViewSet)
router.register(r"subcategorias", SubCategoriaViewSet)
router.register(r"productos", ProductoViewSet)
router.register(r"ventas", VentaViewSet)
router.register(r"detalleventas", DetalleVentaViewSet)
router.register(r"garantias", GarantiaViewSet)
# router.register(r"ingresos", IngresoViewSet)
# router.register(r"detalleingresos", DetalleIngresoViewSet)
router.register(r"promociones", PromocionViewSet)
router.register(r"productospromociones", ProductoPromocionViewSet)
router.register(r"pagos", PagoViewSet)
router.register(r"mantenimientos", MantenimientoViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path('mis-ventas/', views.MisVentasList.as_view(), name='mis-ventas'),
    path('api/', include('reportes.urls')),
    path('api/ia/', include('scikit_learn_ia.urls')),
    # FCM / Push endpoints
    path('devices/register/', FCMDeviceRegisterView.as_view(), name='device-register'),
    path('devices/unregister/', FCMDeviceUnregisterView.as_view(), name='device-unregister'),
    path('admin/devices/', FCMDeviceListView.as_view(), name='admin-devices'),
    path('admin/send-notification/', SendNotificationView.as_view(), name='admin-send-notification'),
]