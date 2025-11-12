# authz/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Rol, Usuario

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'rol']

class PerfilUsuarioSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    rol = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id', 'user', 'rol', 'telefono']
    
    def get_rol(self, obj):
        return obj.rol.rol if obj.rol else None

# authz/serializers.py
class UserSerializer(serializers.ModelSerializer):
    perfil = PerfilUsuarioSerializer(read_only=True)
    # Permitimos que el cliente envíe un rol al crear el usuario
    rol = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(), write_only=True, required=False, allow_null=True
    )
    # Añadir first_name y last_name explícitamente
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=30)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    # Añadir teléfono como campo write-only
    telefono = serializers.CharField(required=False, allow_blank=True, max_length=20, write_only=True)

    class Meta:
        model = User
        fields = [
            "id", 
            "email", 
            "password", 
            "first_name", 
            "last_name", 
            "perfil",
            "rol",
            "telefono"  # Añadir teléfono aquí
        ]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Este correo electrónico ya está registrado."
            )
        return value

    def create(self, validated_data):
        # Extraer rol si fue enviado
        rol_obj = validated_data.pop('rol', None)
        # Extraer teléfono si fue enviado
        telefono = validated_data.pop('telefono', '')
        # Extraer first_name y last_name
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')

        email = validated_data.get("email")
        password = validated_data.get("password")
        
        # Crear usuario con todos los datos
        user = User.objects.create_user(
            username=email, 
            email=email, 
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Crear perfil y asignar rol y teléfono
        Usuario.objects.create(
            user=user, 
            rol=rol_obj,
            telefono=telefono
        )

        return user