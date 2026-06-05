from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-var-cms-dev-key-xyz123"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "var_cms",
    "demo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/var-cms/login/"
LOGIN_REDIRECT_URL = "/var-cms/"

# ── VAR CMS Branding and Site Settings ─────────────────────────────────────
VAR_CMS_SITE_HEADER = "CMS"
VAR_CMS_SITE_SUB = "CONTROL PANEL"
VAR_CMS_SITE_URL = "https://example.com"
VAR_CMS_LOGO_URL = "/static/var_cms/var.png"
VAR_CMS_ACCENT_COLOR = "142, 72%, 45%"
VAR_CMS_ENABLE_OTP = False

# Developer Profile info
VAR_CMS_DEVELOPER_NAME = "Rahul Baberwal"
VAR_CMS_DEVELOPER_WEBSITE = "https://rahulbaberwal.com"
VAR_CMS_DEVELOPER_GITHUB = "https://github.com/rahul-baberwal"
VAR_CMS_DEVELOPER_LINKEDIN = "https://linkedin.com/in/rahul-baberwal"
VAR_CMS_DEVELOPER_EMAIL = "im@rahulbaberwal.com"

