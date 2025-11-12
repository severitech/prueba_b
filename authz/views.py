from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializer import UserSerializer, PerfilUsuarioSerializer
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework import status
from .models import Rol, Usuario
from django.contrib.auth import authenticate
# Create your views here.


@api_view(['POST'])
def login(request):
    """
    Vista personalizada para login que devuelve todos los datos del usuario
    """
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email y contraseña son requeridos'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Buscar usuario por email
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'Credenciales inválidas'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Autenticar con username (que es igual al email en tu caso)
    user = authenticate(username=user.username, password=password)
    
    if user:
        # Obtener o crear token
        token, created = Token.objects.get_or_create(user=user)
        
        # Obtener el perfil del usuario
        try:
            perfil = Usuario.objects.get(user=user)
            perfil_serializer = PerfilUsuarioSerializer(perfil)
            
            # Crear respuesta CONSISTENTE con el register
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "perfil": perfil_serializer.data
            }
            
        except Usuario.DoesNotExist:
            # Si no tiene perfil, crear uno por defecto
            rol_cliente = Rol.objects.get(rol="Cliente")
            perfil = Usuario.objects.create(user=user, rol=rol_cliente)
            perfil_serializer = PerfilUsuarioSerializer(perfil)
            
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "perfil": perfil_serializer.data
            }
        
        return Response({
            'token': token.key,
            'user': user_data
        })
    else:
        return Response(
            {'error': 'Credenciales inválidas'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    
@api_view(["POST"])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data.get("email")
        password = serializer.validated_data["password"]
        first_name = serializer.validated_data.get("first_name", "")
        last_name = serializer.validated_data.get("last_name", "")
        telefono = request.data.get("telefono", "")  # Extraer teléfono del request
        
        user = User.objects.create_user(
            username=email, 
            email=email, 
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Asignar rol
        rol_id = request.data.get("rol")
        if rol_id:
            try:
                rol_obj = Rol.objects.get(id=rol_id)
            except Rol.DoesNotExist:
                rol_obj = Rol.objects.get(rol="Cliente")
        else:
            rol_obj = Rol.objects.get(rol="Cliente")

        # Crear perfil CON teléfono
        Usuario.objects.create(
            user=user,
            rol=rol_obj,
            telefono=telefono,  # ¡Pasar el teléfono aquí!
        )

        # Crear token
        token, _ = Token.objects.get_or_create(user=user)

        # Serializar el usuario completo para la respuesta
        user_serializer = UserSerializer(user)

        return Response(
            {
                "token": token.key,
                "user": user_serializer.data
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def perfil(request):
    return Response({"message": "perfil successful"})


@api_view(["PATCH"])
def cambiar_rol(request, user_id):
    try:
        perfil = Usuario.objects.get(user_id=user_id)
        nuevo_rol = request.data.get("rol")
        rol_obj = Rol.objects.get(rol=nuevo_rol)
        perfil.rol = rol_obj
        perfil.save()
        return Response({"message": f"Rol actualizado a {nuevo_rol}"})
    except Usuario.DoesNotExist:
        return Response({"error": "Perfil no encontrado"}, status=404)
    except Rol.DoesNotExist:
        return Response({"error": "Rol no válido"}, status=400)
