from django.contrib import admin

from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
	list_display = (
		"titulo",
		"estado",
		"enviar_a_todos",
		"programada_para",
		"enviada_en",
		"created_at",
		"updated_at",
	)
	list_filter = ("estado", "enviar_a_todos", "programada_para", "enviada_en")
	search_fields = ("titulo", "cuerpo")
	filter_horizontal = ("destinatarios",)
