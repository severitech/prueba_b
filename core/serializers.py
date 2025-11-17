from rest_framework import serializers

from authz.models import Usuario
from .models import Notificacion


class UsuarioSimpleSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = Usuario
        fields = ("id", "user_id", "nombre", "email", "telefono", "estado")


class NotificacionSerializer(serializers.ModelSerializer):
    destinatarios = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(estado=True),
        many=True,
        required=False,
    )
    destinatarios_detalle = UsuarioSimpleSerializer(source="destinatarios", many=True, read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    puede_enviarse = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = (
            "id",
            "titulo",
            "cuerpo",
            "estado",
            "estado_display",
            "programada_para",
            "enviada_en",
            "enviar_a_todos",
            "destinatarios",
            "destinatarios_detalle",
            "datos_extra",
            "ultimo_resultado",
            "puede_enviarse",
            "creado_por",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "enviada_en",
            "ultimo_resultado",
            "puede_enviarse",
            "creado_por",
            "created_at",
            "updated_at",
        )

    def get_puede_enviarse(self, obj: Notificacion) -> bool:
        return obj.puede_enviarse()

    def validate_estado(self, value: str) -> str:
        if self.instance is None and value in (
            Notificacion.Estado.ENVIADA,
            Notificacion.Estado.FALLIDA,
        ):
            raise serializers.ValidationError("No se puede crear una notificación ya enviada o fallida.")
        return value

    def validate(self, attrs: dict) -> dict:
        enviar_a_todos = attrs.get(
            "enviar_a_todos",
            self.instance.enviar_a_todos if self.instance else True,
        )
        destinatarios = attrs.get("destinatarios", None)
        if not enviar_a_todos:
            destinatarios_existentes = (
                self.instance.destinatarios.exists() if self.instance else False
            )
            if not destinatarios and not destinatarios_existentes:
                raise serializers.ValidationError(
                    {"destinatarios": "Debe seleccionar destinatarios cuando enviar_a_todos es falso."}
                )
        datos_extra = attrs.get("datos_extra")
        if datos_extra is not None and not isinstance(datos_extra, dict):
            raise serializers.ValidationError({"datos_extra": "Debe ser un objeto JSON válido."})
        return attrs

    def create(self, validated_data: dict, **kwargs) -> Notificacion:
        destinatarios = validated_data.pop("destinatarios", [])
        creado_por = kwargs.get("creado_por")
        if creado_por is not None:
            validated_data.setdefault("creado_por", creado_por)
        notificacion = Notificacion.objects.create(**validated_data)
        if destinatarios:
            notificacion.destinatarios.set(destinatarios)
        return notificacion

    def update(self, instance: Notificacion, validated_data: dict, **kwargs) -> Notificacion:
        destinatarios = validated_data.pop("destinatarios", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if destinatarios is not None:
            instance.destinatarios.set(destinatarios)
        return instance
