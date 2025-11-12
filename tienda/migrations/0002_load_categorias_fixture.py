from django.db import migrations
from django.core.management import call_command


def load_categorias(apps, schema_editor):
    call_command('loaddata', 'tienda/fixtures/categorias.json')


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0001_initial'),
        ('authz', '0003_load_initial_fixture'),
    ]

    operations = [
        migrations.RunPython(load_categorias, reverse_code=migrations.RunPython.noop),
    ]
