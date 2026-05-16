from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        import sys
        # Only start scheduler in main process, not in reloader
        if 'runserver' in sys.argv and '--noreload' not in sys.argv:
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception:
                pass
