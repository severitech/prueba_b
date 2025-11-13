from django.contrib import admin
from .models import FCMDevice
from django.contrib import messages
from django.http import HttpResponseRedirect


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
	list_display = ('registration_id', 'usuario', 'tipo_dispositivo', 'activo', 'fecha_creacion')
	list_filter = ('tipo_dispositivo', 'activo')
	search_fields = ('registration_id', 'usuario__user__username')
	actions = ['send_notification_action']

	def send_notification_action(self, request, queryset):
		"""Envía una notificación simple a los dispositivos seleccionados.

		Nota: admin actions no muestran un formulario; si quieres título/cuerpo personalizados
		usa el endpoint `/api/admin/send-notification/`.
		"""
		tokens = list(queryset.filter(activo=True, tipo_dispositivo='android').values_list('registration_id', flat=True))
		if not tokens:
			self.message_user(request, 'No hay tokens activos en la selección', level=messages.WARNING)
			return
		# enviar notificación de prueba
		from core.notifications import enviar_tokens_push
		result = enviar_tokens_push(tokens, 'Mensaje desde Admin', 'Notificación enviada desde Django Admin')
		self.message_user(request, f"Enviado: {result}")

	send_notification_action.short_description = 'Enviar notificación (test) a dispositivos seleccionados'

# Register your models here.
