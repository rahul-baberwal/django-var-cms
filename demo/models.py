from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


STATUS_CHOICES = [("draft","Draft"),("published","Published"),("archived","Archived")]


class Article(models.Model):
    title       = models.CharField(max_length=255)
    slug        = models.SlugField(unique=True)
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    author      = models.CharField(max_length=120)
    body        = models.TextField()
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_featured = models.BooleanField(default=False)
    view_count  = models.PositiveIntegerField(default=0)
    rating      = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "article"
        verbose_name_plural = "articles"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MediaAsset(models.Model):
    ASSET_TYPES = [("image","Image"),("video","Video"),("audio","Audio"),("document","Document"),("other","Other")]

    title       = models.CharField(max_length=200)
    asset_type  = models.CharField(max_length=20, choices=ASSET_TYPES, default="image")
    image       = models.ImageField(upload_to="var_cms/images/%Y/%m/", blank=True, null=True)
    file        = models.FileField(upload_to="var_cms/files/%Y/%m/",  blank=True, null=True)
    alt_text    = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    tags        = models.CharField(max_length=300, blank=True, help_text="Comma-separated tags")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "media asset"
        verbose_name_plural = "media assets"

    def __str__(self):
        return self.title


class Page(models.Model):
    title        = models.CharField(max_length=255)
    slug         = models.SlugField(unique=True)
    meta_desc    = models.CharField(max_length=160, blank=True)
    body         = models.TextField()
    parent       = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    is_published = models.BooleanField(default=False)
    show_in_nav  = models.BooleanField(default=True)
    sort_order   = models.PositiveSmallIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "page"
        verbose_name_plural = "pages"
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title


# ── Optional Geo models ───────────────────────────────────────────────────────
try:
    from django.core.exceptions import ImproperlyConfigured as _IC
    try:
        from django.contrib.gis.db import models as gis_models

        class Location(gis_models.Model):
            name      = models.CharField(max_length=200)
            address   = models.CharField(max_length=400, blank=True)
            point     = gis_models.PointField()
            is_active = models.BooleanField(default=True)
            created_at = models.DateTimeField(auto_now_add=True)
            class Meta:
                verbose_name = "location"
                verbose_name_plural = "locations"
            def __str__(self): return self.name

        class Zone(gis_models.Model):
            name      = models.CharField(max_length=200)
            boundary  = gis_models.PolygonField()
            description = models.TextField(blank=True)
            created_at = models.DateTimeField(auto_now_add=True)
            class Meta:
                verbose_name = "zone"
                verbose_name_plural = "zones"
            def __str__(self): return self.name

        HAS_GEO_MODELS = True
    except (_IC, Exception):
        HAS_GEO_MODELS = False
except Exception:
    HAS_GEO_MODELS = False
