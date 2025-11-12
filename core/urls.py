# core/url.py
from django.urls import path
from .views import (
    crear_checkout_session,
    verificar_pago,
    
    crear_checkout_session_mobile,
    pago_exitoso_mobile,
    pago_cancelado_mobile,
)

urlpatterns = [
    # Endpoints web existentes
    path('crear-checkout-session/', crear_checkout_session, name='crear-checkout-session'),
    path('verificar-pago/', verificar_pago, name='verificar-pago'),
    
    path('crear-checkout-session-mobile/', crear_checkout_session_mobile, name='crear-checkout-mobile'),
    path('pago-exitoso-mobile/', pago_exitoso_mobile, name='pago-exitoso-mobile'),
    path('pago-cancelado-mobile/', pago_cancelado_mobile, name='pago-cancelado-mobile'),


]
