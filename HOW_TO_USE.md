# VAR CMS Setup, Features & Integration Guide

Welcome to **VAR CMS**, a premium, high-fidelity administrative Control Panel designed for Django projects. This guide covers how to set up the CMS in your project, customize branding options, configure custom login flows, and register models.

---

## ⚙️ Project Setup

Follow these steps to integrate VAR CMS into your Django application:

### 1. Register the Application
Add `"var_cms"` to your list of `INSTALLED_APPS` inside `settings.py`:
```python
INSTALLED_APPS = [
    ...
    "var_cms",
    "demo",  # Your custom app
]
```

### 2. Configure Static Files & Media
Make sure your template processors are set up, and configure the static files directories to serve your custom logo assets from your project root:
```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

# Serve assets from your root 'static' directory
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

### 3. Add URL Routing & Custom Login Settings
Update your login redirect parameters and include the VAR CMS routes inside your project's root `urls.py`:

**settings.py**
```python
LOGIN_URL = "/var-cms/login/"       # Directs unauthorized traffic to custom glassmorphic login
LOGIN_REDIRECT_URL = "/var-cms/"    # Redirects back to dashboard on success
```

**urls.py**
```python
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("var-cms/", include("var_cms.urls", namespace="var_cms")),
]
```

---

## 🛠️ Registering Models

Create a file named `var_cms_admin.py` inside any of your app directories (auto-discovered on startup):

```python
from var_cms.registry import var_cms_site, VarCMSModelAdmin
from .models import Article

class ArticleAdmin(VarCMSModelAdmin):
    list_display  = ["title", "author", "status", "created_at"]
    list_filter   = ["status", "category"]
    search_fields = ["title", "body", "author"]
    ordering      = ["-created_at"]
    icon          = "file-text"  # Lucide icon name

var_cms_site.register(Article, ArticleAdmin)
```

---

## 🎨 Branding & Customization Settings

You can customize the header, subtitle, logo, HSL accent color, and email verification options directly in your Django `settings.py`:

```python
# settings.py

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

---

## 🔑 Authentication & Password Tools

### 1. Custom Glassmorphic Login
*   A premium, modern dark login interface is provided out-of-the-box at `/var-cms/login/`.

### 2. Optional OTP Verification (2FA)
*   When `enable_otp = True`, successful user logins redirect to an OTP verification view.
*   The system sends a 6-digit code to the user's email.
*   **Development Tip**: If SMTP parameters are not configured in `settings.py`, the code prints directly to your terminal console as `[VAR CMS OTP]: ******` to prevent developers from getting locked out.

### 3. Forgot Password Request
*   Includes a "Forgot Password" link on the login screen. It prompts users to enter their email or username, generates a password reset OTP, and allows defining a new password securely.

### 4. Logged-in Password Reset
*   Users can change their password directly inside the dashboard. Click the **User profile badge** -> select **Reset Password**. It renders a custom password modification form embedded within the base CMS template.

---

## 🎯 Core Features & Options

### 1. HTML Rich-Text Editor (`html_fields`)
Transform standard Django `TextFields` into interactive HTML editors using Quill.js.
*   **How to Use**: Declare `html_fields` on your model admin class:
    ```python
    class ArticleAdmin(VarCMSModelAdmin):
        html_fields = ["body"]
    ```

### 2. Role-Based Permissions (`permissions`)
Configure access, editing, or deletion records per model using groups and roles.
*   **Example**:
    ```python
    from var_cms.permissions import RolePermission

    class ArticleAdmin(VarCMSModelAdmin):
        permissions = [
            RolePermission("superuser", add=True, edit=True, delete=True),
            RolePermission("editor",    add=True, edit=True, delete=False),
        ]
    ```

### 3. Collapsible Sidebar
*   Click the **Menu toggle button** on the left side of the top bar to collapse the sidebar into icon-only mode. Collapsed states are automatically saved to `localStorage` and persist across page loads.

### 4. Custom Regex Field Validation (`regex_validators`)
Validate user input on specific text fields using custom regular expressions. This automatically enforces native HTML5 validation constraints client-side in the browser and Django `RegexValidator` rules on the server.
*   **How to Use**:
    ```python
    class ArticleAdmin(VarCMSModelAdmin):
        regex_validators = {
            "slug": (r"^[a-z0-9-]+$", "Slug must consist of lowercase letters, numbers, and hyphens only.")
        }
    ```
