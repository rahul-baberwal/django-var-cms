from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("var-cms/", include("var_cms.urls", namespace="var_cms")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
