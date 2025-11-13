import rest_framework.serializers as serializers

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
    Prediccion,
    FCMDevice,
)

from authz.models import Usuario, Rol



class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = "__all__"


class SubCategoriaSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(
        read_only=True
    )  # 👈 muestra los datos de la categoría
    categoria_id = serializers.PrimaryKeyRelatedField(  # 👈 permite enviar solo el id al crear/editar
        queryset=Categoria.objects.all(), source="categoria", write_only=True
    )
    class Meta:
        model = SubCategoria
        fields = "__all__"


class ProductoSerializer(serializers.ModelSerializer):
    subcategoria = SubCategoriaSerializer(
        read_only=True
    )  # 👈 muestra los datos completos
    subcategoria_id = serializers.PrimaryKeyRelatedField(  # 👈 permite enviar solo el id al crear/editar
        queryset=SubCategoria.objects.all(), source="subcategoria", write_only=True
    )

    class Meta:
        model = Productos
        fields = "__all__"


class UsuarioSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    rol = serializers.SlugRelatedField(slug_field='rol', queryset=Rol.objects.all())

    class Meta:
        model = Usuario
        fields = "__all__"


class VentaSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)  # ✅ muestra los datos del usuario completo
    usuario_id = serializers.PrimaryKeyRelatedField(  # ✅ permite enviar el ID al crear o editar
        queryset=Usuario.objects.all(),
        source="usuario",
        write_only=True
    )

    class Meta:
        model = Venta
        fields = "__all__"



class DetalleVentaSerializer(serializers.ModelSerializer):
    venta = VentaSerializer(read_only=True)
    producto = ProductoSerializer(read_only=True)
    venta_id = serializers.PrimaryKeyRelatedField(
        queryset=Venta.objects.all(), source="venta", write_only=True
    )
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Productos.objects.all(), source="producto", write_only=True
    )
    class Meta:
        model = DetalleVenta
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class GarantiaSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Productos.objects.all(), source="producto", write_only=True
    )
    class Meta:
        model = Garantia
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class IngresoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(), source="usuario", write_only=True
    )
    class Meta:
        model = Ingreso
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class DetalleIngresoSerializer(serializers.ModelSerializer):
    ingreso = IngresoSerializer(read_only=True)
    producto = ProductoSerializer(read_only=True)
    ingreso_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingreso.objects.all(), source="ingreso", write_only=True
    )
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Productos.objects.all(), source="producto", write_only=True
    )
    class Meta:
        model = DetalleIngreso
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class PromocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocion
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ProductoPromocionSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    promocion = PromocionSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Productos.objects.all(), source="producto", write_only=True
    )
    promocion_id = serializers.PrimaryKeyRelatedField(
        queryset=Promocion.objects.all(), source="promocion", write_only=True
    )
    class Meta:
        model = ProductoPromocion
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class PagoSerializer(serializers.ModelSerializer):
    venta = VentaSerializer(read_only=True)
    venta_id = serializers.PrimaryKeyRelatedField(
        queryset=Venta.objects.all(), source="venta", write_only=True
    )
    class Meta:
        model = Pago
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class MantenimientoSerializer(serializers.ModelSerializer):
    detalle_venta = DetalleVentaSerializer(read_only=True)
    detalle_venta_id = serializers.PrimaryKeyRelatedField(
        queryset=DetalleVenta.objects.all(), source="detalle_venta", write_only=True
    )
    usuario = UsuarioSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(), source="usuario", write_only=True
    )
    class Meta:
        model = Mantenimiento
        fields = "__all__"

class PrediccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediccion
        fields = "__all__"


class FCMDeviceSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    class Meta:
        model = FCMDevice
        fields = [
            'id',
            'usuario',
            'registration_id',
            'tipo_dispositivo',
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['id', 'usuario', 'fecha_creacion', 'fecha_modificacion']