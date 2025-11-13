from django.contrib import admin
from .models import FCMDevice
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
	list_display = ('registration_id', 'usuario', 'tipo_dispositivo', 'activo', 'fecha_creacion')
	list_filter = ('tipo_dispositivo', 'activo')
	search_fields = ('registration_id', 'usuario__user__username')
	actions = ['send_notification_action']

	def get_urls(self):
		urls = super().get_urls()
		custom_urls = [
			path('send_custom_notification/', self.admin_site.admin_view(self.send_custom_notification_view), name='fcmdevice_send_custom'),
		]
		return custom_urls + urls

	def send_notification_action(self, request, queryset):
		"""Envía una notificación simple a los dispositivos seleccionados.

		Nota: admin actions no muestran un formulario; si quieres título/cuerpo personalizados
		usa el endpoint `/api/admin/send-notification/`.
		"""
		tokens = list(queryset.filter(activo=True, tipo_dispositivo='android').values_list('registration_id', flat=True))
		if not tokens:
			self.message_user(request, 'No hay tokens activos en la selección', level=messages.WARNING)
			return
		# redirigir a la vista custom para permitir título/cuerpo personalizados
		ids = ",".join([str(x) for x in queryset.values_list('id', flat=True)])
		return HttpResponseRedirect(f"./send_custom_notification/?ids={ids}")

	send_notification_action.short_description = 'Enviar notificación (test) a dispositivos seleccionados'

	def send_custom_notification_view(self, request):
		"""Vista admin para enviar notificaciones con título y cuerpo personalizados a dispositivos seleccionados."""
		ids = request.GET.get('ids', '') or request.POST.get('ids', '')
		id_list = [int(i) for i in ids.split(',') if i]

		if request.method == 'POST':
			title = request.POST.get('title')
			body = request.POST.get('body')
			if not title or not body:
				self.message_user(request, 'Title y body son requeridos', level=messages.ERROR)
				return HttpResponseRedirect(request.path + f'?ids={ids}')

			tokens = list(FCMDevice.objects.filter(id__in=id_list, activo=True, tipo_dispositivo='android').values_list('registration_id', flat=True))
			if not tokens:
				self.message_user(request, 'No hay tokens activos en la selección', level=messages.WARNING)
				return HttpResponseRedirect(request.path + f'?ids={ids}')

			from core.notifications import enviar_tokens_push
			result = enviar_tokens_push(tokens, title, body)
			self.message_user(request, f'Enviado: {result}')
			# redirect back to changelist
			changelist_url = request.META.get('HTTP_REFERER', '../../')
			return HttpResponseRedirect(changelist_url)

		# GET: mostrar formulario simple
		devices = FCMDevice.objects.filter(id__in=id_list)
		context = dict(
			self.admin_site.each_context(request),
			devices=devices,
			ids=ids,
		)
		return render(request, 'admin/fcm_send_custom.html', context)

# Register your models here.
