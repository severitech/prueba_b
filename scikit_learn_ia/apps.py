# scikit_learn_ia/apps.py
from django.apps import AppConfig


class ScikitLearnIaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "scikit_learn_ia"

    def ready(self):
        from .paths import print_paths_banner
        print_paths_banner("Startup scikit_learn_ia")