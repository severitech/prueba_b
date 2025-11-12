from django.db import models

from django.contrib.auth.models import User


class Rol(models.Model):
    rol = models.CharField(max_length=50)

    def __str__(self):
        return self.rol

class Usuario(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil_authz'  
    )
    rol = models.ForeignKey('Rol', on_delete=models.SET_NULL, null=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    estado = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.user.username} ({self.rol})"
