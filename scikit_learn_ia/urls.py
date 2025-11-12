# scikit_learn_ia/urls.py
from django.urls import path
from .views import (
    IAHealthView,
    GenerarDatosSinteticosView,
    EntrenarModeloCantidadesView,
    PredecirCantidadesView,
    PrediccionesListView,
    ReporteVentasMensualView,
    ReportePDFView,
    ReporteExcelView,
    PanelSeriesListView,
    PanelPrediccionesView
)

urlpatterns = [
    path("health/", IAHealthView.as_view(), name="ia-health"),
    path("generar-datos/", GenerarDatosSinteticosView.as_view(), name="ia-generar-datos"),
    path("entrenar-modelo/", EntrenarModeloCantidadesView.as_view(), name="ia-entrenar-modelo"),
    path("predict-cantidades/", PredecirCantidadesView.as_view(), name="ia-predict-cantidades"),
    path("predicciones/", PrediccionesListView.as_view(), name="ia-predicciones"),
    path("reporte-ventas/", ReporteVentasMensualView.as_view(), name="ia-reporte-ventas"),
    path('reporte-pdf/', ReportePDFView.as_view(), name='ia-reporte-pdf'),
    path('reporte-excel/', ReporteExcelView.as_view(), name='ia-reporte-excel'),
    path("panel/series/", PanelSeriesListView.as_view(), name="ia-panel-series"),
    path("panel/predicciones/", PanelPrediccionesView.as_view(), name="ia-panel-predicciones"),
]

