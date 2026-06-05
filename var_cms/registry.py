"""
var_cms/registry.py
===================
django-var-cms  — Admin-like CMS registry with:
  • Role-based permissions  (add / list / view / edit / delete per role/group/user)
  • Field-level edit control (editable_fields, readonly_fields per role)
  • Rich media previews      (image crop, video/audio/PDF player, file converter)
  • Auto-discovery of var_cms_admin.py in every installed app

Usage
-----
    # myapp/var_cms_admin.py
    from var_cms.registry import var_cms_site, VarCMSModelAdmin
    from var_cms.permissions import RolePermission

    class ArticleAdmin(VarCMSModelAdmin):
        list_display    = ["title", "author", "status", "created_at"]
        list_filter     = ["status", "category"]
        search_fields   = ["title", "body"]
        readonly_fields = ["created_at", "updated_at"]   # nobody can edit
        ordering        = ["-created_at"]

        # ── Role-based permissions ──────────────────────────────────────
        permissions = [
            RolePermission("superuser", add=True,  list=True, view=True, edit=True, delete=True),
            RolePermission("editor",    add=True,  list=True, view=True, edit=True, delete=False),
            RolePermission("viewer",    add=False, list=True, view=True, edit=False, delete=False),
        ]

        # ── Per-role editable fields ────────────────────────────────────
        role_editable_fields = {
            "editor":  ["title", "body", "status"],   # editors can only touch these
            "superuser": "__all__",                   # superuser can edit everything
        }

    var_cms_site.register(Article, ArticleAdmin)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set, Type, Union

from django import forms
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.forms import modelform_factory
from functools import wraps
from django.http import HttpRequest, JsonResponse, Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
import random

from .permissions import RolePermission, resolve_permission, resolve_editable_fields

logger = logging.getLogger(__name__)

def var_cms_error_wrapper(view_func):
    @wraps(view_func)
    def wrapped(self, request, *args, **kwargs):
        is_api = (
            request.path.startswith('/var-cms/api/') or
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            'application/json' in request.META.get('HTTP_ACCEPT', '')
        )
        try:
            return view_func(self, request, *args, **kwargs)
        except PermissionDenied as e:
            msg = str(e) or "You do not have permission to access this resource."
            if is_api:
                return JsonResponse({"error": msg}, status=403)
            return self.error_403_view(request, message=msg)
        except Http404 as e:
            msg = str(e) or "The page or record you are looking for was not found."
            if is_api:
                return JsonResponse({"error": msg}, status=404)
            return self.error_404_view(request, message=msg)
        except Exception as e:
            from django.conf import settings
            if not getattr(settings, "DEBUG", True):
                msg = str(e) or "An internal server error occurred."
                if is_api:
                    return JsonResponse({"error": msg}, status=500)
                return self.error_500_view(request, message=msg)
            raise e
    return wrapped

# ─── GIS optional ─────────────────────────────────────────────────────────────

GEO_FIELD_TYPES: set = set()
HAS_GIS = False
try:
    from django.core.exceptions import ImproperlyConfigured as _GIS_IC
    try:
        from django.contrib.gis.db import models as gis_models
        GEO_FIELD_TYPES = {
            gis_models.PointField, gis_models.LineStringField,
            gis_models.PolygonField, gis_models.MultiPointField,
            gis_models.MultiLineStringField, gis_models.MultiPolygonField,
            gis_models.GeometryCollectionField, gis_models.GeometryField,
        }
        HAS_GIS = True
    except (_GIS_IC, Exception):
        pass
except Exception:
    pass


# ─── Display helpers ──────────────────────────────────────────────────────────

def get_field_display_value(instance, field_name: str, admin=None) -> str:
    try:
        parts = field_name.split("__")
        obj = instance
        for part in parts:
            if obj is None:
                return "—"
            obj = getattr(obj, part, None)
            if callable(obj):
                obj = obj()
        if obj is None:
            return "—"
        if isinstance(obj, bool):
            if obj:
                return format_html('<i data-lucide="check" style="width:16px;height:16px;color:var(--green);display:inline-block;vertical-align:middle;"></i>')
            else:
                return format_html('<i data-lucide="x" style="width:16px;height:16px;color:var(--red);display:inline-block;vertical-align:middle;"></i>')
        if HAS_GIS:
            try:
                from django.contrib.gis.geos import GEOSGeometry
                if isinstance(obj, GEOSGeometry):
                    return format_html(
                        '<span class="geo-tag">{} {}</span>',
                        obj.geom_type,
                        f"({obj.num_coords}pts)" if hasattr(obj, "num_coords") else "",
                    )
            except Exception:
                pass
        field = instance._meta.get_field(parts[0]) if len(parts) == 1 else None
        if field and isinstance(field, models.ImageField) and obj:
            width = 38
            height = 38
            if admin:
                width = getattr(admin, "list_image_width", 38)
                height = getattr(admin, "list_image_height", 38)
            return format_html('<img src="{}" class="preview-thumb" data-preview="{}" style="width:{}px;height:{}px;" />', obj.url, obj.url, width, height)
        if field and isinstance(field, models.FileField) and obj:
            ext = str(obj.name).rsplit(".", 1)[-1].lower()
            icon_name = {"mp4": "video", "mp3": "music", "wav": "music", "pdf": "file-text", "webm": "video"}.get(ext, "paperclip")
            return format_html(
                '<a href="{}" class="file-preview-link" data-ext="{}" data-url="{}">'
                '<i data-lucide="{}" style="width:14px;height:14px;display:inline-block;vertical-align:middle;margin-right:4px;"></i>{}</a>',
                obj.url, ext, obj.url, icon_name, obj.name.split("/")[-1]
            )
        text = str(obj)
        if len(text) > 80:
            return format_html('<span title="{}">{}&hellip;</span>', text, text[:77])
        return text
    except Exception as e:
        logger.debug("display_value error %s: %s", field_name, e)
        return "—"


def build_filter_widgets(model, filter_fields: List[str]) -> Dict[str, Any]:
    widgets = {}
    for fname in filter_fields:
        try:
            field = model._meta.get_field(fname)
        except Exception:
            continue
        if field.choices:
            widgets[fname] = {"type": "select", "choices": list(field.choices), "label": field.verbose_name.title()}
        elif isinstance(field, (models.BooleanField,)):
            widgets[fname] = {"type": "boolean", "label": field.verbose_name.title()}
        elif isinstance(field, (models.DateField, models.DateTimeField)):
            widgets[fname] = {"type": "date_range", "label": field.verbose_name.title()}
        elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
            related = field.related_model
            widgets[fname] = {
                "type": "select",
                "choices": [(str(o.pk), str(o)) for o in related.objects.all()[:300]],
                "label": field.verbose_name.title(),
            }
        elif isinstance(field, (models.IntegerField, models.FloatField, models.DecimalField)):
            widgets[fname] = {"type": "number_range", "label": field.verbose_name.title()}
        else:
            widgets[fname] = {"type": "text", "label": field.verbose_name.title()}
    return widgets


# ─── VarCMSModelAdmin ─────────────────────────────────────────────────────────

class VarCMSModelAdmin:
    """
    Register any model with this class.  All options are optional — sane defaults apply.

    Permissions
    -----------
    permissions : list[RolePermission]
        Per-role permission objects.  Falls back to superuser-only if empty.

    role_editable_fields : dict[str, list|"__all__"]
        Which fields each role may edit.  "__all__" means every non-readonly field.
        Example:
            role_editable_fields = {
                "editor":     ["title", "body", "status"],
                "superuser":  "__all__",
            }

    List display
    ------------
    list_display, list_filter, search_fields, ordering, list_per_page

    Form
    ----
    readonly_fields  — always shown, never editable
    exclude_fields   — hidden from form entirely
    """

    # ── Display ───────────────────────────────────────────────────────────────
    list_display: List[str] = []
    list_filter: List[str] = []
    search_fields: List[str] = []
    ordering: List[str] = []
    list_per_page: int = 25
    list_select_related: bool = False

    # ── Form ──────────────────────────────────────────────────────────────────
    readonly_fields: List[str] = []
    exclude_fields: List[str] = []
    regex_validators: Dict[str, Union[str, Tuple[str, str]]] = {}

    # ── Legacy simple toggles (overridden by permissions[] if set) ────────────
    allow_add: bool = True
    allow_edit: bool = True
    allow_delete: bool = True

    # ── Role-based permissions ────────────────────────────────────────────────
    permissions: List[RolePermission] = []

    # ── Per-role editable fields ──────────────────────────────────────────────
    # {"role_name": ["field1", "field2"] | "__all__"}
    role_editable_fields: Dict[str, Union[List[str], str]] = {}

    # ── Form Layout and Customizations ────────────────────────────────────────
    form_field_widths: Dict[str, str] = {}
    form_field_classes: Dict[str, str] = {}
    form_field_styles: Dict[str, str] = {}
    form_widget_classes: Dict[str, str] = {}
    form_field_placeholders: Dict[str, str] = {}
    form_field_help_texts: Dict[str, str] = {}

    # ── Custom widget types per field ─────────────────────────────────────────
    # Valid values:
    #   "select"            — standard <select> dropdown (default)
    #   "select_search"     — searchable dropdown with live filter
    #   "multiselect"       — checkbox list for multi-selection
    #   "multiselect_search"— checkbox list with search input
    form_field_widgets: Dict[str, str] = {}

    # ── Field row grouping ────────────────────────────────────────────────────
    # Group fields to be rendered in a single visual row.
    # Example: [["first_name", "last_name"], ["mobile", "email", "dob"]]
    # Fields not listed here are laid out by the default width rules.
    form_field_rows: List[List[str]] = []

    # ── HTML editor fields ────────────────────────────────────────────────────
    html_fields: List[str] = []

    # ── Customizations ────────────────────────────────────────────────────────
    icon: str = ""
    dashboard_card: bool = False
    card_buttons: List[Dict[str, str]] = []
    list_image_width: int = 38
    list_image_height: int = 38

    def __init__(self, model: Type[models.Model], site: "VarCMSSite"):
        self.model = model
        self.site = site
        if not self.list_display:
            self.list_display = [
                f.name for f in self.model._meta.get_fields()
                if isinstance(f, models.Field) and not f.many_to_many and not f.one_to_many
            ][:6]

    def get_card_buttons(self, request) -> List[Dict[str, Any]]:
        buttons = []
        if not self.card_buttons:
            if self.has_permission(request, "list"):
                buttons.append({
                    "label": "View List",
                    "url": reverse(f"var_cms:var_cms_{self.model._meta.app_label}_{self.model._meta.model_name}_list"),
                    "class": "btn-ghost"
                })
            if self.has_permission(request, "add"):
                buttons.append({
                    "label": "Add New",
                    "url": reverse(f"var_cms:var_cms_{self.model._meta.app_label}_{self.model._meta.model_name}_add"),
                    "class": "btn-primary"
                })
        else:
            for btn in self.card_buttons:
                btn_copy = btn.copy()
                action = btn_copy.get("action")
                if action == "add" and self.has_permission(request, "add"):
                    btn_copy["url"] = reverse(f"var_cms:var_cms_{self.model._meta.app_label}_{self.model._meta.model_name}_add")
                    btn_copy["class"] = btn_copy.get("class", "btn-primary")
                elif action == "list" and self.has_permission(request, "list"):
                    btn_copy["url"] = reverse(f"var_cms:var_cms_{self.model._meta.app_label}_{self.model._meta.model_name}_list")
                    btn_copy["class"] = btn_copy.get("class", "btn-ghost")
                buttons.append(btn_copy)
        return buttons

    # ── Queryset ──────────────────────────────────────────────────────────────

    def get_queryset(self, request):
        qs = self.model._default_manager.all()
        if self.list_select_related:
            qs = qs.select_related()
        if self.ordering:
            qs = qs.order_by(*self.ordering)
        return qs

    def apply_search(self, qs, query: str):
        if not query or not self.search_fields:
            return qs
        q = Q()
        for f in self.search_fields:
            q |= Q(**{f"{f}__icontains": query})
        return qs.filter(q)

    def apply_filters(self, qs, params: dict):
        for key, value in params.items():
            if not value or key in ("q", "page", "o", "ot"):
                continue
            if key.endswith("__gte") or key.endswith("__lte"):
                qs = qs.filter(**{key: value})
            elif key in [f.name for f in self.model._meta.get_fields()]:
                qs = qs.filter(**{key: value})
        return qs

    # ── Permissions ───────────────────────────────────────────────────────────

    def _get_user_role(self, request) -> str:
        """Return the best-matching role name for this user."""
        if request.user.is_superuser:
            return "superuser"
        groups = list(request.user.groups.values_list("name", flat=True))
        if self.permissions:
            defined_roles = {p.role for p in self.permissions if hasattr(p, "role")}
            for g in groups:
                if g in defined_roles:
                    return g
        return groups[0] if groups else "anonymous"

    def has_permission(self, request, action: str, obj=None) -> bool:
        """action ∈ {add, list, view, edit, delete}"""
        if not request.user.is_authenticated:
            return False
        role = self._get_user_role(request)
        if self.permissions:
            username_field = self.site._get_username_field()
            user_username = getattr(request.user, username_field, "")
            if callable(user_username):
                user_username = user_username()
            if not user_username and hasattr(request.user, "get_username"):
                user_username = request.user.get_username()
            return resolve_permission(self.permissions, role, action, username=user_username)
        # Fallback to legacy allow_* flags
        legacy = {"add": self.allow_add, "edit": self.allow_edit,
                  "delete": self.allow_delete, "list": True, "view": True}
        return legacy.get(action, False)

    def get_editable_fields(self, request) -> Union[List[str], str]:
        """Return list of field names this user may edit, or '__all__'."""
        role = self._get_user_role(request)
        if self.role_editable_fields:
            return resolve_editable_fields(self.role_editable_fields, role)
        return "__all__"

    # ── Form building ─────────────────────────────────────────────────────────

    def get_form(self, request, instance=None):
        editable = self.get_editable_fields(request)
        all_fields = [
            f.name for f in self.model._meta.get_fields()
            if isinstance(f, models.Field)
        ]
        exclude = list(self.exclude_fields)
        if not HAS_GIS:
            for f in self.model._meta.get_fields():
                if type(f) in GEO_FIELD_TYPES:
                    exclude.append(f.name)
        # Fields that are readonly stay as readonly_fields (shown separately)
        exclude += [f for f in self.readonly_fields if f in all_fields]

        FormClass = modelform_factory(
            self.model,
            exclude=[f for f in exclude if f in all_fields] or None,
            widgets=self._build_widgets(),
        )
        if self.regex_validators:
            from django.core.validators import RegexValidator
            for field_name, val in self.regex_validators.items():
                if field_name in FormClass.base_fields:
                    if isinstance(val, (list, tuple)) and len(val) >= 2:
                        pattern, err_msg = val[0], val[1]
                    else:
                        pattern, err_msg = val, "This value does not match the required format."
                    FormClass.base_fields[field_name].validators.append(
                        RegexValidator(regex=pattern, message=err_msg)
                    )
                    # Also append client-side browser pattern constraint
                    widget = FormClass.base_fields[field_name].widget
                    widget.attrs['pattern'] = pattern
                    widget.attrs['title'] = err_msg

        # Inject custom widget attributes (classes, placeholders, help texts)
        for field_name, field_obj in FormClass.base_fields.items():
            if self.form_widget_classes and field_name in self.form_widget_classes:
                existing_class = field_obj.widget.attrs.get('class', '')
                field_obj.widget.attrs['class'] = f"{existing_class} {self.form_widget_classes[field_name]}".strip()
            if self.form_field_placeholders and field_name in self.form_field_placeholders:
                field_obj.widget.attrs['placeholder'] = self.form_field_placeholders[field_name]
            if self.form_field_help_texts and field_name in self.form_field_help_texts:
                field_obj.help_text = self.form_field_help_texts[field_name]

        if request.method == "POST":
            form_inst = FormClass(request.POST, request.FILES, instance=instance)
        else:
            form_inst = FormClass(instance=instance)

        # Disable fields that the user does not have permission to edit
        for field_name, field_obj in form_inst.fields.items():
            if editable != "__all__" and isinstance(editable, list):
                if field_name not in editable:
                    field_obj.disabled = True

        return form_inst

    def _build_widgets(self):
        widgets = {}
        for f in self.model._meta.get_fields():
            if not isinstance(f, models.Field):
                continue
            if isinstance(f, models.TextField):
                if f.name in self.html_fields:
                    widgets[f.name] = forms.Textarea(attrs={"rows": 10, "class": "html-editor"})
                else:
                    widgets[f.name] = forms.Textarea(attrs={"rows": 4})
            if isinstance(f, models.DateField) and not isinstance(f, models.DateTimeField):
                widgets[f.name] = forms.DateInput(attrs={"type": "date"})
            if isinstance(f, models.DateTimeField):
                widgets[f.name] = forms.DateTimeInput(attrs={"type": "datetime-local"})

        # Apply custom widget types from form_field_widgets
        if self.form_field_widgets:
            for field_name, widget_type in self.form_field_widgets.items():
                try:
                    f = self.model._meta.get_field(field_name)
                except Exception:
                    continue
                if widget_type == "select_search":
                    # Standard select with data-searchable marker for JS enhancement
                    widgets[field_name] = forms.Select(
                        attrs={"class": "vcms-searchable-select", "data-widget": "select_search"}
                    )
                elif widget_type == "multiselect":
                    # Renders choices as checkboxes (no search)
                    widgets[field_name] = forms.CheckboxSelectMultiple(
                        attrs={"class": "vcms-checkbox-multi", "data-widget": "multiselect"}
                    )
                elif widget_type == "multiselect_search":
                    # Renders choices as checkboxes with a search box
                    widgets[field_name] = forms.CheckboxSelectMultiple(
                        attrs={"class": "vcms-checkbox-multi vcms-checkbox-search", "data-widget": "multiselect_search"}
                    )
                # "select" is the default — no override needed
        return widgets

    # ── Hooks (override for custom behaviour) ─────────────────────────────────

    def save_model(self, request, obj, form, change: bool):
        if hasattr(obj, "slug") and not obj.slug:
            from django.utils.text import slugify
            source_val = ""
            for possible_source in ["title", "name", "headline"]:
                if hasattr(obj, possible_source):
                    val = getattr(obj, possible_source)
                    if val:
                        source_val = val
                        break
            if source_val:
                base_slug = slugify(source_val)
                slug = base_slug
                num = 1
                while obj.__class__.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                    slug = f"{base_slug}-{num}"
                    num += 1
                obj.slug = slug
        obj.save()

    def delete_model(self, request, obj):
        obj.delete()

    def get_column_header(self, field_name: str) -> str:
        try:
            field = self.model._meta.get_field(field_name.split("__")[0])
            return field.verbose_name.title()
        except Exception:
            return field_name.replace("_", " ").replace("__", " › ").title()

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name

    @property
    def verbose_name_plural(self):
        return self.model._meta.verbose_name_plural


class VarCMSSite:
    def __init__(self, name: str = "var_cms"):
        self.name = name
        self._registry: Dict[Type[models.Model], VarCMSModelAdmin] = {}

        # ── Read defaults from settings.py (VAR_CMS_* keys) ──────────────────
        from django.conf import settings as _s
        def _cfg(key, default):
            return getattr(_s, f"VAR_CMS_{key}", default)

        self.site_header  = _cfg("SITE_HEADER",  "VAR CMS")
        self.site_sub     = _cfg("SITE_SUB",     "CONTROL PANEL")
        self.site_url     = _cfg("SITE_URL",     "/")
        self.logo_url     = _cfg("LOGO_URL",     "/static/var_cms/var.png")
        self.logo_svg     = _cfg("LOGO_SVG",     None)
        accent = _cfg("ACCENT_COLOR", None)
        if accent:
            try:
                parts = [p.strip() for p in accent.split(",")]
                if len(parts) == 3:
                    h = parts[0]
                    s = parts[1]
                    if not s.endswith("%"):
                        s += "%"
                    l_val = parts[2].replace("%", "").strip()
                    l_num = float(l_val)
                    if l_num < 45:
                        l_num = 45.0
                    elif l_num > 85:
                        l_num = 85.0
                    accent = f"{h}, {s}, {int(round(l_num))}%"
            except Exception as e:
                logger.warning("Failed to parse VAR_CMS_ACCENT_COLOR: %s", e)
        self.accent_color = accent
        self.enable_otp   = _cfg("ENABLE_OTP",   False)

        # Developer Profile
        self.developer_name     = _cfg("DEVELOPER_NAME",     "Rahul Baberwal")
        self.developer_website  = _cfg("DEVELOPER_WEBSITE",  "https://rahulbaberwal.com")
        self.developer_github   = _cfg("DEVELOPER_GITHUB",   "https://github.com/rahul-baberwal")
        self.developer_email    = _cfg("DEVELOPER_EMAIL",    "im@rahulbaberwal.com")
        self.developer_linkedin = _cfg("DEVELOPER_LINKEDIN", "https://linkedin.com/in/rahul-baberwal")
        self.developer_image    = _cfg("DEVELOPER_IMAGE",    "https://github.com/rahul-baberwal.png")

        self.username_field         = _cfg("USERNAME_FIELD",         None)
        self.hidden_dashboard_cards = _cfg("HIDDEN_DASHBOARD_CARDS", [])
        self.shown_dashboard_cards  = _cfg("SHOWN_DASHBOARD_CARDS",  [])

    def _get_username_field(self) -> str:
        if self.username_field:
            return self.username_field
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return getattr(User, 'USERNAME_FIELD', 'username')

    def register(self, model: Type[models.Model], admin_class=None, **options):
        if admin_class is None:
            admin_class = VarCMSModelAdmin
        if options:
            admin_class = type(f"{model.__name__}AdminAuto", (admin_class,), options)
        self._registry[model] = admin_class(model, self)

    def unregister(self, model):
        self._registry.pop(model, None)

    def get_model_admin(self, app_label, model_name) -> Optional[VarCMSModelAdmin]:
        for m, a in self._registry.items():
            if m._meta.app_label == app_label and m._meta.model_name == model_name:
                return a
        return None

    def _get_admin(self, app, model_name):
        admin = self.get_model_admin(app, model_name)
        if not admin:
            from django.http import Http404
            raise Http404(f"No var_cms admin for {app}.{model_name}")
        return admin

    # ── URLs ──────────────────────────────────────────────────────────────────

    def get_urls(self):
        lv = login_required
        urls = [
            path("", lv(self.index_view), name="var_cms_index"),
            path("about/", lv(self.about_view), name="var_cms_about"),
            path("login/", self.login_view, name="var_cms_login"),
            path("otp-verify/", self.otp_verify_view, name="var_cms_otp_verify"),
            path("logout/", self.logout_view, name="var_cms_logout"),
            path("change-password/", lv(self.change_password_view), name="var_cms_change_password"),
            path("forgot-password/", self.forgot_password_view, name="var_cms_forgot_password"),
            path("forgot-password/verify/", self.forgot_password_verify_view, name="var_cms_forgot_password_verify"),
        ]
        for model, admin in self._registry.items():
            ap, mn = model._meta.app_label, model._meta.model_name
            urls += [
                path(f"{ap}/{mn}/",              lv(self.list_view),   {"app": ap, "model": mn}, name=f"var_cms_{ap}_{mn}_list"),
                path(f"{ap}/{mn}/add/",          lv(self.add_view),    {"app": ap, "model": mn}, name=f"var_cms_{ap}_{mn}_add"),
                path(f"{ap}/{mn}/<pk>/",         lv(self.edit_view),   {"app": ap, "model": mn}, name=f"var_cms_{ap}_{mn}_edit"),
                path(f"{ap}/{mn}/<pk>/delete/",  lv(self.delete_view), {"app": ap, "model": mn}, name=f"var_cms_{ap}_{mn}_delete"),
                path(f"{ap}/{mn}/<pk>/view/",    lv(self.detail_view), {"app": ap, "model": mn}, name=f"var_cms_{ap}_{mn}_view"),
                # Media API
                path(f"api/media/crop/",         lv(self.media_crop_view),    name="var_cms_media_crop"),
                path(f"api/media/convert/",      lv(self.media_convert_view), name="var_cms_media_convert"),
            ]
        urls.append(path("<path:path>", self.catch_all_404_view, name="var_cms_404"))
        return urls

    # ── Base context ──────────────────────────────────────────────────────────

    def _base_ctx(self, request):
        nav = {}
        for m, a in self._registry.items():
            ap = m._meta.app_label
            if not a.has_permission(request, "list"):
                continue
            nav.setdefault(ap, []).append({
                "model": m, "admin": a,
                "model_name": m._meta.model_name,
                "verbose_name_plural": m._meta.verbose_name_plural,
                "url": reverse(f"var_cms:var_cms_{ap}_{m._meta.model_name}_list"),
            })
        default_svg = '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" xmlns="http://www.w3.org/2000/svg" class="default-svg-logo"><defs><linearGradient id="varLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="var(--red)" /><stop offset="100%" stop-color="var(--purple)" /></linearGradient></defs><path d="M2 5l5 14L12 5" stroke="url(#varLogoGrad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 5l5 14" stroke="url(#varLogoGrad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.5 12h5" stroke="url(#varLogoGrad)" stroke-width="2.5" stroke-linecap="round"/><path d="M12 5c4.5 0 6.5 2 6.5 4s-2 3-4 3" stroke="url(#varLogoGrad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M14.5 12L19.5 19" stroke="url(#varLogoGrad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        return {
            "var_cms_site": self,
            "var_cms_nav": nav,
            "request": request,
            "var_cms_accent_color": self.accent_color,
            "var_cms_logo_svg": self.logo_svg,
            "var_cms_logo_default": default_svg,
        }

    def _readonly_vals(self, admin, obj):
        if not obj:
            return {}
        return {f: get_field_display_value(obj, f, admin) for f in admin.readonly_fields}

    # ── Error Views ───────────────────────────────────────────────────────────

    def error_403_view(self, request, message=None):
        ctx = self._base_ctx(request)
        ctx.update({
            "status_code": 403,
            "error_title": "Access Denied",
            "error_message": message or "You do not have permission to access this resource.",
        })
        return render(request, "var_cms/error.html", ctx, status=403)

    def error_404_view(self, request, message=None):
        ctx = self._base_ctx(request)
        ctx.update({
            "status_code": 404,
            "error_title": "Page Not Found",
            "error_message": message or "The page or record you are looking for was not found.",
        })
        return render(request, "var_cms/error.html", ctx, status=404)

    def error_500_view(self, request, message=None):
        ctx = self._base_ctx(request)
        ctx.update({
            "status_code": 500,
            "error_title": "Internal Server Error",
            "error_message": message or "An unexpected error occurred on the server.",
        })
        return render(request, "var_cms/error.html", ctx, status=500)

    def catch_all_404_view(self, request, path):
        is_api = (
            request.path.startswith('/var-cms/api/') or
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            'application/json' in request.META.get('HTTP_ACCEPT', '')
        )
        if is_api:
            return JsonResponse({"error": f"Path '{path}' not found."}, status=404)
        return self.error_404_view(request, message=f"The requested path '/var-cms/{path}' does not exist.")

    # ── Views ─────────────────────────────────────────────────────────────────

    @var_cms_error_wrapper
    def index_view(self, request):
        ctx = self._base_ctx(request)
        ctx["title"] = "Dashboard"
        
        registry_items = []
        for m, a in self._registry.items():
            if not a.has_permission(request, "list"):
                continue
            
            app_label = m._meta.app_label
            model_name = m._meta.model_name
            full_name = f"{app_label}.{model_name}"
            
            show = getattr(a, "dashboard_card", False)
            
            hidden_list = getattr(self, "hidden_dashboard_cards", [])
            shown_list = getattr(self, "shown_dashboard_cards", [])
            
            if shown_list:
                if full_name in shown_list or model_name in shown_list:
                    show = True
                else:
                    show = False
            
            if hidden_list:
                if full_name in hidden_list or model_name in hidden_list:
                    show = False
                    
            registry_items.append({
                "app": app_label, "model_name": model_name,
                "verbose_name_plural": m._meta.verbose_name_plural,
                "count": m._default_manager.count(),
                "url": reverse(f"var_cms:var_cms_{app_label}_{model_name}_list"),
                "admin": a,
                "can_add": a.has_permission(request, "add"),
                "dashboard_card": show,
                "buttons": a.get_card_buttons(request),
            })
            
        ctx["registry"] = registry_items
        return render(request, "var_cms/index.html", ctx)

    @var_cms_error_wrapper
    def about_view(self, request):
        ctx = self._base_ctx(request)
        ctx["title"] = "Help & Support"
        
        # Load and render README.md
        import os
        readme_html = "<p>README.md not found.</p>"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for path_attempt in [
            os.path.join(current_dir, "README.md"),
            os.path.join(os.path.dirname(current_dir), "README.md"),
        ]:
            if os.path.exists(path_attempt):
                try:
                    with open(path_attempt, "r", encoding="utf-8") as f:
                        md_content = f.read()
                    readme_html = self._render_markdown(md_content)
                    break
                except Exception as e:
                    logger.warning("Failed to read README: %s", e)
                    
        ctx["readme_html"] = readme_html
        return render(request, "var_cms/about.html", ctx)

    def _render_markdown(self, text):
        import re
        lines = text.split("\n")
        html_lines = []
        in_code_block = False
        in_list = False
        
        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    html_lines.append("</code></pre></div>")
                    in_code_block = False
                else:
                    lang = line.strip()[3:]
                    html_lines.append(f'<div class="code-block-wrapper"><pre><code class="language-{lang}">')
                    in_code_block = True
                continue
                
            if in_code_block:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(escaped)
                continue
                
            header_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if header_match:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                level = len(header_match.group(1))
                title = header_match.group(2)
                html_lines.append(f"<h{level}>{title}</h{level}>")
                continue
                
            list_match = re.match(r"^[\s]*[\-\*\+]\s+(.*)$", line)
            if list_match:
                if not in_list:
                    html_lines.append('<ul class="readme-list">')
                    in_list = True
                html_lines.append(f"<li>{list_match.group(1)}</li>")
                continue
                
            if not list_match and line.strip() != "" and in_list:
                html_lines.append("</ul>")
                in_list = False
                
            if re.match(r"^[\s]*[\-\*_]{3,}[\s]*$", line):
                html_lines.append("<hr/>")
                continue
                
            if line.strip() != "":
                line_html = line
                line_html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line_html)
                line_html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", line_html)
                line_html = re.sub(r"`(.*?)`", r"<code>\1</code>", line_html)
                line_html = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" target="_blank">\1</a>', line_html)
                html_lines.append(f"<p>{line_html}</p>")
            else:
                html_lines.append("<br/>")
                
        if in_list:
            html_lines.append("</ul>")
        if in_code_block:
            html_lines.append("</code></pre></div>")
            
        return "\n".join(html_lines)


    @var_cms_error_wrapper
    def login_view(self, request):
        if request.user.is_authenticated:
            return redirect(reverse("var_cms:var_cms_index"))
        
        error_msg = None
        if request.method == "POST":
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if self.enable_otp:
                    otp = str(random.randint(100000, 999999))
                    request.session["var_cms_otp"] = otp
                    request.session["var_cms_pre_otp_user_id"] = user.id
                    
                    subject = f"OTP Verification Code for {self.site_header}"
                    message = f"Your one-time password (OTP) verification code is: {otp}\n\nThis code will expire once used."
                    try:
                        send_mail(
                            subject,
                            message,
                            None,
                            [user.email] if user.email else [],
                            fail_silently=False,
                        )
                    except Exception as e:
                        logger.warning("Failed to send OTP email: %s", e)
                        username_field = self._get_username_field()
                        user_username = getattr(user, username_field, "")
                        if callable(user_username):
                            user_username = user_username()
                        if not user_username and hasattr(user, "get_username"):
                            user_username = user.get_username()
                        print(f"\n[VAR CMS OTP]: {otp} for user {user_username}\n")
                    
                    return redirect(reverse("var_cms:var_cms_otp_verify"))
                else:
                    auth_login(request, user)
                    return redirect(reverse("var_cms:var_cms_index"))
            else:
                error_msg = "Invalid username or password."
        else:
            form = AuthenticationForm(request)
            
        ctx = {
            "form": form,
            "error_msg": error_msg,
            "var_cms_site": self,
            "var_cms_logo_default": self._base_ctx(request)["var_cms_logo_default"],
        }
        return render(request, "var_cms/login.html", ctx)

    @var_cms_error_wrapper
    def otp_verify_view(self, request):
        pre_user_id = request.session.get("var_cms_pre_otp_user_id")
        saved_otp = request.session.get("var_cms_otp")
        if not pre_user_id or not saved_otp:
            return redirect(reverse("var_cms:var_cms_login"))
            
        from django.contrib.auth.models import User
        user = get_object_or_404(User, id=pre_user_id)
        error_msg = None
        
        if request.method == "POST":
            entered_otp = request.POST.get("otp", "").strip()
            if entered_otp == saved_otp:
                auth_login(request, user)
                request.session.pop("var_cms_otp", None)
                request.session.pop("var_cms_pre_otp_user_id", None)
                return redirect(reverse("var_cms:var_cms_index"))
            else:
                error_msg = "Invalid OTP. Please try again."
                
        ctx = {
            "user": user,
            "error_msg": error_msg,
            "var_cms_site": self,
            "var_cms_logo_default": self._base_ctx(request)["var_cms_logo_default"],
        }
        return render(request, "var_cms/otp_verify.html", ctx)

    @var_cms_error_wrapper
    def logout_view(self, request):
        auth_logout(request)
        return redirect(reverse("var_cms:var_cms_login"))

    @var_cms_error_wrapper
    def change_password_view(self, request):
        error_msg = None
        success_msg = None
        if request.method == "POST":
            old_pass = request.POST.get("old_password", "").strip()
            new_pass = request.POST.get("new_password", "").strip()
            confirm_pass = request.POST.get("confirm_password", "").strip()
            
            if not request.user.check_password(old_pass):
                error_msg = "Current password is incorrect."
            elif new_pass != confirm_pass:
                error_msg = "New passwords do not match."
            elif len(new_pass) < 6:
                error_msg = "New password must be at least 6 characters."
            else:
                request.user.set_password(new_pass)
                request.user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                success_msg = "Password updated successfully!"
                
        ctx = self._base_ctx(request)
        ctx.update({
            "title": "Reset Password",
            "error_msg": error_msg,
            "success_msg": success_msg,
        })
        return render(request, "var_cms/change_password.html", ctx)

    @var_cms_error_wrapper
    def forgot_password_view(self, request):
        error_msg = None
        if request.method == "POST":
            username_or_email = request.POST.get("username_or_email", "").strip()
            from django.contrib.auth import get_user_model
            User = get_user_model()
            username_field = self._get_username_field()
            q_obj = Q(**{username_field: username_or_email})
            has_email = any(f.name == "email" for f in User._meta.fields)
            if has_email and username_field != "email":
                q_obj |= Q(email=username_or_email)
            user = User.objects.filter(q_obj).first()
            
            if user:
                if not user.email:
                    error_msg = "This user does not have an email address configured."
                else:
                    otp = str(random.randint(100000, 999999))
                    request.session["var_cms_reset_otp"] = otp
                    request.session["var_cms_reset_user_id"] = user.id
                    
                    subject = f"Password Reset Code for {self.site_header}"
                    message = f"Your password reset verification code is: {otp}\n\nUse this code to set a new password."
                    try:
                        send_mail(
                            subject,
                            message,
                            None,
                            [user.email],
                            fail_silently=False,
                        )
                    except Exception as e:
                        logger.warning("Failed to send reset OTP email: %s", e)
                        username_field = self._get_username_field()
                        user_username = getattr(user, username_field, "")
                        if callable(user_username):
                            user_username = user_username()
                        if not user_username and hasattr(user, "get_username"):
                            user_username = user.get_username()
                        print(f"\n[VAR CMS RESET OTP]: {otp} for user {user_username}\n")
                        
                    return redirect(reverse("var_cms:var_cms_forgot_password_verify"))
            else:
                error_msg = "No user found with that username or email."
                
        ctx = {
            "error_msg": error_msg,
            "var_cms_site": self,
            "var_cms_logo_default": self._base_ctx(request)["var_cms_logo_default"],
        }
        return render(request, "var_cms/forgot_password.html", ctx)

    @var_cms_error_wrapper
    def forgot_password_verify_view(self, request):
        user_id = request.session.get("var_cms_reset_user_id")
        saved_otp = request.session.get("var_cms_reset_otp")
        if not user_id or not saved_otp:
            return redirect(reverse("var_cms:var_cms_forgot_password"))
            
        from django.contrib.auth.models import User
        user = get_object_or_404(User, id=user_id)
        error_msg = None
        
        if request.method == "POST":
            entered_otp = request.POST.get("otp", "").strip()
            new_pass = request.POST.get("new_password", "").strip()
            confirm_pass = request.POST.get("confirm_password", "").strip()
            
            if entered_otp != saved_otp:
                error_msg = "Invalid OTP code."
            elif new_pass != confirm_pass:
                error_msg = "New passwords do not match."
            elif len(new_pass) < 6:
                error_msg = "New password must be at least 6 characters."
            else:
                user.set_password(new_pass)
                user.save()
                request.session.pop("var_cms_reset_otp", None)
                request.session.pop("var_cms_reset_user_id", None)
                return redirect(reverse("var_cms:var_cms_login"))
                
        ctx = {
            "user": user,
            "error_msg": error_msg,
            "var_cms_site": self,
            "var_cms_logo_default": self._base_ctx(request)["var_cms_logo_default"],
        }
        return render(request, "var_cms/forgot_password_verify.html", ctx)

    @var_cms_error_wrapper
    def list_view(self, request, app, model):
        admin = self._get_admin(app, model)
        if not admin.has_permission(request, "list"):
            raise PermissionDenied
        qs = admin.get_queryset(request)
        q = request.GET.get("q", "").strip()
        qs = admin.apply_search(qs, q)
        qs = admin.apply_filters(qs, request.GET.dict())
        order_field = request.GET.get("o")
        order_dir   = request.GET.get("ot", "asc")
        if order_field and order_field in admin.list_display:
            qs = qs.order_by(f"{'-' if order_dir == 'desc' else ''}{order_field}")
        if not qs.ordered:
            qs = qs.order_by("pk")
        paginator = Paginator(qs, admin.list_per_page)
        page = paginator.get_page(request.GET.get("page", 1))
        rows = [
            {"obj": obj, "pk": obj.pk,
             "cells": [get_field_display_value(obj, f, admin) for f in admin.list_display]}
            for obj in page
        ]
        ctx = self._base_ctx(request)
        ctx.update({
            "title": admin.verbose_name_plural.title(),
            "admin": admin, "app": app, "model_name": model,
            "page": page, "rows": rows,
            "headers": [admin.get_column_header(f) for f in admin.list_display],
            "filter_widgets": build_filter_widgets(admin.model, admin.list_filter),
            "search_query": q, "order_field": order_field, "order_dir": order_dir,
            "can_add":    admin.has_permission(request, "add"),
            "can_edit":   admin.has_permission(request, "edit"),
            "can_delete": admin.has_permission(request, "delete"),
            "can_view":   admin.has_permission(request, "view"),
        })
        return render(request, "var_cms/list.html", ctx)

    @var_cms_error_wrapper
    def add_view(self, request, app, model):
        admin = self._get_admin(app, model)
        if not admin.has_permission(request, "add"):
            raise PermissionDenied
        form = admin.get_form(request)
        if request.method == "POST":
            form = admin.get_form(request)
            if form.is_valid():
                obj = form.save(commit=False)
                admin.save_model(request, obj, form, False)
                return redirect(reverse(f"var_cms:var_cms_{app}_{model}_list"))
        ctx = self._base_ctx(request)
        ctx.update({"title": f"Add {admin.verbose_name}", "admin": admin,
                    "form": form, "app": app, "model_name": model,
                    "readonly_fields": self._readonly_vals(admin, None), "is_add": True,
                    "editable_fields": admin.get_editable_fields(request)})
        return render(request, "var_cms/form.html", ctx)

    @var_cms_error_wrapper
    def edit_view(self, request, app, model, pk):
        admin = self._get_admin(app, model)
        if not admin.has_permission(request, "edit"):
            raise PermissionDenied
        obj = get_object_or_404(admin.model, pk=pk)
        form = admin.get_form(request, instance=obj)
        if request.method == "POST":
            form = admin.get_form(request, instance=obj)
            if form.is_valid():
                saved = form.save(commit=False)
                admin.save_model(request, saved, form, True)
                return redirect(reverse(f"var_cms:var_cms_{app}_{model}_list"))
        ctx = self._base_ctx(request)
        ctx.update({"title": f"Edit: {obj}", "admin": admin, "form": form,
                    "obj": obj, "app": app, "model_name": model, "is_add": False,
                    "readonly_fields": self._readonly_vals(admin, obj),
                    "editable_fields": admin.get_editable_fields(request),
                    "can_delete": admin.has_permission(request, "delete")})
        return render(request, "var_cms/form.html", ctx)

    @var_cms_error_wrapper
    def detail_view(self, request, app, model, pk):
        admin = self._get_admin(app, model)
        if not admin.has_permission(request, "view"):
            raise PermissionDenied
        obj = get_object_or_404(admin.model, pk=pk)
        fields = [
            (admin.get_column_header(f.name), get_field_display_value(obj, f.name, admin))
            for f in admin.model._meta.get_fields()
            if isinstance(f, models.Field) and not f.many_to_many
        ]
        ctx = self._base_ctx(request)
        ctx.update({"title": str(obj), "obj": obj, "admin": admin,
                    "app": app, "model_name": model, "fields": fields,
                    "can_edit": admin.has_permission(request, "edit"),
                    "can_delete": admin.has_permission(request, "delete")})
        return render(request, "var_cms/detail.html", ctx)

    @var_cms_error_wrapper
    def delete_view(self, request, app, model, pk):
        admin = self._get_admin(app, model)
        if not admin.has_permission(request, "delete"):
            raise PermissionDenied
        obj = get_object_or_404(admin.model, pk=pk)
        if request.method == "POST":
            admin.delete_model(request, obj)
            return redirect(reverse(f"var_cms:var_cms_{app}_{model}_list"))
        ctx = self._base_ctx(request)
        ctx.update({"title": "Delete", "obj": obj, "admin": admin, "app": app, "model_name": model})
        return render(request, "var_cms/delete.html", ctx)

    # ── Media API views ───────────────────────────────────────────────────────

    @var_cms_error_wrapper
    def media_crop_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "POST only"}, status=405)
        from .media_utils.crop import handle_crop
        return handle_crop(request)

    @var_cms_error_wrapper
    def media_convert_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "POST only"}, status=405)
        from .media_utils.convert import handle_convert
        return handle_convert(request)


# Global singleton
var_cms_site = VarCMSSite()
