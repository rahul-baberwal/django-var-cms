from django.urls import path
from var_cms.registry import var_cms_site

app_name = "var_cms"
urlpatterns = var_cms_site.get_urls()
