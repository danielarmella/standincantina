from django.apps import AppConfig


class CantinaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cantina"
    verbose_name = "Stand-in Cantina Booking"

    def ready(self):
        import cantina.signals