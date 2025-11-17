
# Create your models here.
from django.conf import settings
from django.db import models
from django.utils import timezone

from .notifications import enviar_tokens_push


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class Notificacion(TimeStampedModel):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PROGRAMADA = "programada", "Programada"
        ENVIADA = "enviada", "Enviada"
        FALLIDA = "fallida", "Fallida"

    titulo = models.CharField(max_length=140)
    cuerpo = models.TextField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    programada_para = models.DateTimeField(null=True, blank=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    enviar_a_todos = models.BooleanField(default=True)
    destinatarios = models.ManyToManyField(
        "authz.Usuario",
        blank=True,
        related_name="notificaciones_recibidas",
    )
    datos_extra = models.JSONField(default=dict, blank=True)
    ultimo_resultado = models.JSONField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificaciones_creadas",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self) -> str:
        return f"{self.titulo} ({self.get_estado_display()})"

    def _build_datos(self, datos: dict | None = None) -> dict:
        payload = datos if datos is not None else self.datos_extra or {}
        return {str(k): ("" if v is None else str(v)) for k, v in payload.items()}

    def _tokens_destino(self):
        from tienda.models import FCMDevice

        queryset = FCMDevice.objects.filter(activo=True)
        if not self.enviar_a_todos:
            destinatarios_ids = list(self.destinatarios.values_list("id", flat=True))
            if not destinatarios_ids:
                return []
            queryset = queryset.filter(usuario_id__in=destinatarios_ids)
        return list(queryset.values("registration_id", "tipo_dispositivo"))

    def enviar(self, *, datos_extra: dict | None = None) -> dict:
        tokens = self._tokens_destino()
        ahora = timezone.now()

        if not tokens:
            resultado = {
                "success": 0,
                "failure": 0,
                "responses": [],
                "detalle": "Sin tokens activos para enviar",
            }
            self.estado = Notificacion.Estado.FALLIDA
            self.enviada_en = ahora
            self.ultimo_resultado = resultado
            self.save(update_fields=["estado", "enviada_en", "ultimo_resultado", "updated_at"])
            return resultado

        payload = self._build_datos(datos_extra)
        resultado = enviar_tokens_push(tokens, self.titulo, self.cuerpo, payload)

        self.enviada_en = ahora
        self.ultimo_resultado = resultado
        self.estado = (
            Notificacion.Estado.ENVIADA
            if resultado.get("success", 0) > 0 and resultado.get("failure", 0) == 0
            else Notificacion.Estado.FALLIDA
        )
        self.save(update_fields=["estado", "enviada_en", "ultimo_resultado", "updated_at"])
        return resultado

    def puede_enviarse(self) -> bool:
        if self.estado == Notificacion.Estado.ENVIADA:
            return False
        if not self.enviar_a_todos and not self.destinatarios.exists():
            return False
        return True
