from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("authz", "0003_load_initial_fixture"),
        ("tienda", "0005_fcmdevice"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notificacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, blank=True, null=True)),
                ("titulo", models.CharField(max_length=140)),
                ("cuerpo", models.TextField()),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("borrador", "Borrador"),
                            ("programada", "Programada"),
                            ("enviada", "Enviada"),
                            ("fallida", "Fallida"),
                        ],
                        default="borrador",
                        max_length=20,
                    ),
                ),
                ("programada_para", models.DateTimeField(blank=True, null=True)),
                ("enviada_en", models.DateTimeField(blank=True, null=True)),
                ("enviar_a_todos", models.BooleanField(default=True)),
                ("datos_extra", models.JSONField(blank=True, default=dict)),
                ("ultimo_resultado", models.JSONField(blank=True, null=True)),
                (
                    "creado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notificaciones_creadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "verbose_name": "Notificación",
                "verbose_name_plural": "Notificaciones",
            },
        ),
        migrations.AddField(
            model_name="notificacion",
            name="destinatarios",
            field=models.ManyToManyField(blank=True, related_name="notificaciones_recibidas", to="authz.usuario"),
        ),
    ]
