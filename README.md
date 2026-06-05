# django-var-cms

A modern, highly customizable administrative Control Panel and CMS registry for Django projects. Built with premium glassmorphic aesthetics, role-based security, and rich media processing.

Created by **[Rahul Baberwal](https://rahulbaberwal.com)**.

---

## 🚀 Key Features

- **🎨 Modern Design System**: Responsive glassmorphic layout, collapsible navigation sidebar with `localStorage` persistent state, and custom HSL accent color configurations.
- **🔑 Role & User Permissions**: Manage fine-grained view, list, edit, add, and delete actions matching Django Groups or specific user accounts.
- **📝 HTML Editor**: Integrated Quill.js rich text editor out of the box.
- **✅ Regex Field Validation**: Easily enforce custom regular expression patterns both client-side and server-side.
- **🖼️ Media Previews & Image Cropper**:
  - Modal-based previews for images, video, audio, and PDFs.
  - Built-in Image Cropper (rotate, flip, custom aspect ratio crops).
  - API endpoints for media conversion (JPEG, PNG, WebP, WAV, MP3, MP4).

---

## ⚙️ Setup & Installation

### 1. Install Dependencies
Install `django-var-cms` along with required media dependencies:

```bash
# Using pip
pip install django-var-cms pillow whitenoise

# Using uv
uv add django-var-cms pillow whitenoise
```

### 2. Configure settings.py
Register `"var_cms"` in your Django `INSTALLED_APPS` and specify static/media paths. You can also customize branding globally here:

```python
# settings.py

INSTALLED_APPS = [
    # ... Django standard apps
    "var_cms",
    # "demo", (optional demo app)
]

# Media settings for handling file uploads/crops
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Static files settings
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Redirect paths for authentication
LOGIN_URL = "/var-cms/login/"
LOGIN_REDIRECT_URL = "/var-cms/"

# ── Global VAR CMS Site Customizations ──────────────────────────────────────
VAR_CMS_SITE_HEADER = "Easy Khata"          # Custom brand title
VAR_CMS_SITE_SUB = "ADMIN PANEL"           # Subtitle
VAR_CMS_SITE_URL = "/"                     # "View Site" redirect URL
VAR_CMS_LOGO_URL = "/static/var_cms/var.png" # Brand Logo
VAR_CMS_ACCENT_COLOR = "142, 72%, 45%"      # Custom HSL accent color (Emerald green)
VAR_CMS_ENABLE_OTP = False                  # Optional email OTP 2FA on login

# Optional Developer Profile (shown in Help section)
VAR_CMS_DEVELOPER_NAME = "Rahul Baberwal"
VAR_CMS_DEVELOPER_WEBSITE = "https://rahulbaberwal.com"
VAR_CMS_DEVELOPER_GITHUB = "https://github.com/rahul-baberwal"
VAR_CMS_DEVELOPER_LINKEDIN = "https://linkedin.com/in/rahul-baberwal"
VAR_CMS_DEVELOPER_EMAIL = "im@rahulbaberwal.com"
```

### 3. Add URL Routing
Include the `var_cms` routes in your project's main `urls.py`:

```python
# urls.py
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... other paths
    path("var-cms/", include("var_cms.urls", namespace="var_cms")),
]

# CRITICAL: Serve uploaded media files (images/files) during local development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 🧪 Seeding the Demo App (Optional)

If you are developing or exploring features in the source repository:
1. Run migrations to initialize the database:
   ```bash
   python manage.py migrate
   ```
2. Run the seed management command to generate default database models, pages, media, and test accounts:
   ```bash
   python manage.py seed_demo
   ```
3. Start the server:
   ```bash
   python manage.py runserver
   ```
4. Access the dashboard at `http://127.0.0.1:8000/var-cms/`.

### Demo User Accounts

| Username | Password | Role / Group | Permissions |
| :--- | :--- | :--- | :--- |
| **admin** | admin | superuser | Full unrestricted access |
| **editor** | editor | editor | Add + Edit (Cannot delete) |
| **author** | author | author | Add + Edit specific fields (Cannot delete) |
| **viewer** | viewer | viewer | List + View records only |
| **alice** | alice | viewer | Viewer permissions, with delete override |

---

## 🛠️ Registering Models (Example)

Create a file named `var_cms_admin.py` in any of your Django apps. It is automatically discovered on startup.

```python
# myapp/var_cms_admin.py
from var_cms.registry import var_cms_site, VarCMSModelAdmin
from var_cms.permissions import RolePermission, UserPermission
from .models import Article

# Customize branding globally
var_cms_site.site_header = "My CMS"
var_cms_site.site_sub    = "Control Center"
var_cms_site.site_url    = "https://example.com"
var_cms_site.logo_url    = "/static/var_cms/var.png"  # Custom brand logo

class ArticleAdmin(VarCMSModelAdmin):
    list_display  = ["title", "category", "author", "status", "created_at"]
    list_filter   = ["status", "category"]
    search_fields = ["title", "body", "author"]
    readonly_fields = ["created_at", "updated_at", "view_count"]
    
    # Enable Quill.js Rich Text Editor on body field
    html_fields = ["body"]
    
    # Custom icon from Lucide
    icon = "file-text"
    
    # Regex validator: client-side + server-side validation
    regex_validators = {
        "slug": (r"^[a-z0-9-]+$", "Slug must consist of lowercase letters, numbers, and hyphens only.")
    }
    
    # Define role permissions
    permissions = [
        RolePermission("superuser", add=True,  list=True, view=True, edit=True,  delete=True),
        RolePermission("editor",    add=True,  list=True, view=True, edit=True,  delete=False),
        RolePermission("author",    add=True,  list=True, view=True, edit=True,  delete=False),
        RolePermission("viewer",    add=False, list=True, view=True, edit=False, delete=False),
        UserPermission("alice",     add=True,  list=True, view=True, edit=True,  delete=True),
    ]
    
    # Limit editable fields by user role
    role_editable_fields = {
        "superuser": "__all__",
        "editor":    ["title", "slug", "body", "status", "category"],
        "author":    ["title", "body", "status"],
        "*":         [],
    }

# Register the model on the custom site
var_cms_site.register(Article, ArticleAdmin)
```

---

## 🎨 Layout Customizations

You can customize the accent color scheme using HSL values on the global `var_cms_site` registry:

```python
# Custom accent color (Emerald green)
var_cms_site.accent_color = "142, 72%, 45%"
```

---

## 📁 URL Structure

```text
/var-cms/                          → Admin Dashboard
/var-cms/{app}/{model}/            → Paginated List view
/var-cms/{app}/{model}/add/        → Object Creation Form
/var-cms/{app}/{model}/{pk}/       → Object Modification Form
/var-cms/{app}/{model}/{pk}/view/  → Read-only Details view
/var-cms/{app}/{model}/{pk}/delete/→ Object Delete confirmation
/var-cms/api/media/crop/           → POST endpoint: crop image
/var-cms/api/media/convert/        → POST endpoint: convert media file type
```

---

## 📖 Detailed Integration & How To Use Guide

For detailed reference on branding customizations, optional two-factor authentication (OTP), and role-based permissions, see below:

### 🎨 Branding & Customization Settings

You can customize the header, subtitle, favicon, and email verification options on the global registry singleton.

Inside your `var_cms_admin.py` or startup setup, modify the settings on the singleton instance `var_cms_site`:

```python
from var_cms.registry import var_cms_site

# ── Change Name & Subtitle ───────────────────────────────────────────────
var_cms_site.site_header = "CMS"              # Default: "VAR CMS"
var_cms_site.site_sub    = "DASHBOARD"        # Default: "CONTROL PANEL"

# ── Customize "View Site" Link ───────────────────────────────────────────
var_cms_site.site_url    = "https://myblog.com" # Default: "/"

# ── Custom Image Logo & Favicon ──────────────────────────────────────────
var_cms_site.logo_url    = "/static/var_cms/var.png"  # Serves var.png as the brand logo & tab favicon

# ── Optional OTP 2FA Verification ────────────────────────────────────────
var_cms_site.enable_otp  = True               # Requires SMTP settings. Sends 6-digit OTP code to email.
```

### 🔑 Authentication & Password Tools

#### 1. Custom Glassmorphic Login
- A premium, modern dark login interface is provided out-of-the-box at `/var-cms/login/`.

#### 2. Optional OTP Verification (2FA)
- When `enable_otp = True`, successful user logins redirect to an OTP verification view.
- The system sends a 6-digit code to the user's email.
- **Development Tip**: If SMTP parameters are not configured in `settings.py`, the code prints directly to your terminal console as `[VAR CMS OTP]: ******` to prevent developers from getting locked out.

#### 3. Forgot Password Request
- Includes a "Forgot Password" link on the login screen. It prompts users to enter their email or username, generates a password reset OTP, and allows defining a new password securely.

#### 4. Logged-in Password Reset
- Users can change their password directly inside the dashboard. Click the **User profile badge** -> select **Reset Password**. It renders a custom password modification form embedded within the base CMS template.

---

## 📖 Complete Demo Reference Examples

Below are the complete source files from the demo application showcasing how models are declared and how they integrate with custom role-based permissions, Quill editors, image croppers, and validators in `django-var-cms`:

### 1. Model Definitions (`demo/models.py`)
```python
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

STATUS_CHOICES = [("draft", "Draft"), ("published", "Published"), ("archived", "Archived")]

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
    ASSET_TYPES = [("image", "Image"), ("video", "Video"), ("audio", "Audio"), ("document", "Document"), ("other", "Other")]

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
```

### 2. CMS Administration Configuration (`demo/var_cms_admin.py`)
```python
from var_cms.registry import var_cms_site, VarCMSModelAdmin
from var_cms.permissions import RolePermission, UserPermission
from .models import Article, Category, MediaAsset, Page

class CategoryAdmin(VarCMSModelAdmin):
    list_display  = ["name", "slug", "is_active", "created_at"]
    list_filter   = ["is_active"]
    search_fields = ["name", "slug", "description"]
    readonly_fields = ["created_at"]
    ordering = ["name"]
    icon = "folder"
    regex_validators = {
        "slug": (r"^[a-z0-9-]+$", "Slug must consist of lowercase letters, numbers, and hyphens only.")
    }

    permissions = [
        RolePermission("superuser", add=True,  list=True, view=True, edit=True,  delete=True),
        RolePermission("editor",    add=True,  list=True, view=True, edit=True,  delete=False),
        RolePermission("viewer",    add=False, list=True, view=True, edit=False, delete=False),
    ]
    role_editable_fields = {
        "superuser": "__all__",
        "editor":    ["name", "description", "is_active"],
    }

class ArticleAdmin(VarCMSModelAdmin):
    list_display  = ["title", "category", "author", "status", "is_featured", "view_count", "created_at"]
    list_filter   = ["status", "is_featured", "category"]
    search_fields = ["title", "body", "author"]
    readonly_fields = ["created_at", "updated_at", "view_count"]
    ordering = ["-created_at"]
    list_per_page = 20
    html_fields = ["body"] # Quill editor
    icon = "file-text"
    card_buttons = [
        {"label": "All Articles", "action": "list"},
        {"label": "Write Draft", "action": "add"}
    ]

    permissions = [
        RolePermission("superuser", add=True,  list=True, view=True, edit=True,  delete=True),
        RolePermission("editor",    add=True,  list=True, view=True, edit=True,  delete=False),
        RolePermission("author",    add=True,  list=True, view=True, edit=True,  delete=False),
        RolePermission("viewer",    add=False, list=True, view=True, edit=False, delete=False),
        UserPermission("alice",     add=True,  list=True, view=True, edit=True,  delete=True),
    ]
    role_editable_fields = {
        "superuser": "__all__",
        "editor":    ["title", "slug", "body", "status", "category", "is_featured"],
        "author":    ["title", "body", "status"],
        "*":         [],
    }

class MediaAssetAdmin(VarCMSModelAdmin):
    list_display  = ["title", "asset_type", "image", "file", "tags", "created_at"]
    list_filter   = ["asset_type"]
    search_fields = ["title", "alt_text", "tags", "description"]
    readonly_fields = ["created_at"]
    icon = "image"

    permissions = [
        RolePermission("superuser", add=True, list=True, view=True, edit=True, delete=True),
        RolePermission("editor",    add=True, list=True, view=True, edit=True, delete=True),
        RolePermission("viewer",    add=False,list=True, view=True, edit=False,delete=False),
    ]
    role_editable_fields = {
        "superuser": "__all__",
        "editor":    "__all__",
    }

class PageAdmin(VarCMSModelAdmin):
    list_display  = ["title", "slug", "parent", "is_published", "show_in_nav", "sort_order"]
    list_filter   = ["is_published", "show_in_nav"]
    search_fields = ["title", "slug", "body", "meta_desc"]
    readonly_fields = ["created_at"]
    ordering = ["sort_order", "title"]
    html_fields = ["body"]
    icon = "book-open"

    permissions = [
        RolePermission("superuser", add=True, list=True, view=True, edit=True, delete=True),
        RolePermission("editor",    add=True, list=True, view=True, edit=True, delete=False),
        RolePermission("viewer",    add=False,list=True, view=True, edit=False,delete=False),
    ]
    role_editable_fields = {
        "superuser": "__all__",
        "editor":    ["title", "body", "meta_desc", "is_published", "show_in_nav", "sort_order"],
    }

var_cms_site.register(Category,   CategoryAdmin)
var_cms_site.register(Article,    ArticleAdmin)
var_cms_site.register(MediaAsset, MediaAssetAdmin)
var_cms_site.register(Page,       PageAdmin)
```

---

## 👥 Credits & Authors

Created and maintained by **Rahul Baberwal** — [rahulbaberwal.com](https://rahulbaberwal.com).
