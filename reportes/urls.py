# reportes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('reportes/voz/', views.ReporteVozView.as_view(), name='reporte_voz'),
    path('reportes/voz/audio/', views.ReporteVozAudioView.as_view(), name='reporte_voz_audio'),  # NUEVO
    path('reportes/ventas/', views.ReporteVentasView.as_view(), name='reporte_ventas'),
    path('reportes/productos/', views.ReporteProductosView.as_view(), name='reporte_productos'),
    path('reportes/clientes/', views.ReporteClientesView.as_view(), name='reporte_clientes'),
    path('reportes/inventario/', views.ReporteInventarioView.as_view(), name='reporte_inventario'),
    path('reportes/status/', views.ReportesStatusView.as_view(), name='reportes_status'),
]