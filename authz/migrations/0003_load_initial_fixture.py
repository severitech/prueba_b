from django.db import migrations
from django.core.management import call_command


def load_initial_authz(apps, schema_editor):
    # Load the authz fixture (roles + auth users + perfiles)
    call_command('loaddata', 'authz/fixtures/initial_authz.json')


class Migration(migrations.Migration):

    dependencies = [
        ('authz', '0002_usuario_estado'),
    ]

    operations = [
        migrations.RunPython(load_initial_authz, reverse_code=migrations.RunPython.noop),
    ]
