
from django.urls import path, include
from rest_framework import routers
from . import views
from .api import UserViewSet, RolViewSet

router = routers.DefaultRouter()
# router.register(r'usuarios', UserViewSet)
router.register(r'roles', RolViewSet)

urlpatterns = [
    path('login/', views.login),
    path('register/', views.register),
    path('perfil/', views.perfil),
    path('', include(router.urls)),
]