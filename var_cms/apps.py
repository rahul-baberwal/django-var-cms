from django.apps import AppConfig


class VarCmsConfig(AppConfig):
    name = "var_cms"
    verbose_name = "VAR CMS"

    def ready(self):
        from django.apps import apps
        for app_config in apps.get_app_configs():
            try:
                __import__(f"{app_config.name}.var_cms_admin")
            except ModuleNotFoundError:
                pass
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "var_cms_admin import error in %s: %s", app_config.name, e
                )
