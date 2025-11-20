from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        """Importa signals quando a aplicação é carregada."""
        import apps.core.signals  # noqa

