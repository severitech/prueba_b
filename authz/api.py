from rest_framework import viewsets, permissions
from django.contrib.auth.models import User

from .models import Rol, Usuario
from .serializer import RolSerializer, PerfilUsuarioSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [permissions.AllowAny]
