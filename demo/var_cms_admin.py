"""
demo/var_cms_admin.py
=====================
Auto-discovered by var_cms on startup.
Demonstrates all registration options including role-based permissions.
"""

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
    dashboard_card = True
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
    custom_object_actions = [
        {
            "name": "toggle_active",
            "label": "Toggle Active",
            "class": "btn-blue",
            "icon": "shuffle",
            "action_fn": "toggle_active_status"
        }
    ]

    def toggle_active_status(self, request, obj):
        from django.contrib import messages
        obj.is_active = not obj.is_active
        obj.save()
        messages.success(request, f"Category '{obj.name}' active status toggled to {obj.is_active}.")
        return None


class ArticleAdmin(VarCMSModelAdmin):
    list_display  = ["title", "category", "author", "status", "is_featured", "view_count", "created_at"]
    list_filter   = ["status", "is_featured", "category"]
    search_fields = ["title", "body", "author"]
    readonly_fields = ["created_at", "updated_at", "view_count"]
    ordering = ["-created_at"]
    list_per_page = 20
    html_fields = ["body"]
    icon = "file-text"
    dashboard_card = True
    card_buttons = [
        {"label": "All Articles", "action": "list"},
        {"label": "Write Draft", "action": "add"}
    ]

    permissions = [
        RolePermission("superuser", add=True,  list=True, view=True, edit=True,  delete=True),
        RolePermission("editor",    add=True,  list=True, view=True, edit=True,  delete=False),
        RolePermission("author",    add=True,  list=True, view=True, edit=True,  delete=False),
        RolePermission("viewer",    add=False, list=True, view=True, edit=False, delete=False),
        # Per-user override — "alice" can delete even as a viewer
        UserPermission("alice",     add=True,  list=True, view=True, edit=True,  delete=True),
    ]
    role_editable_fields = {
        "superuser": "__all__",
        "editor":    ["title", "slug", "body", "status", "category", "is_featured"],
        "author":    ["title", "body", "status"],   # authors can't touch slug/category
        "*":         [],  # all other roles: no edits
    }


class MediaAssetAdmin(VarCMSModelAdmin):
    list_display  = ["title", "asset_type", "image", "file", "tags", "created_at"]
    list_filter   = ["asset_type"]
    search_fields = ["title", "alt_text", "tags", "description"]
    readonly_fields = ["created_at"]
    icon = "image"
    dashboard_card = True

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
    dashboard_card = True

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


# ── Optional geo registrations ───────────────────────────────────────────────
try:
    from .models import HAS_GEO_MODELS
    if HAS_GEO_MODELS:
        from .models import Location, Zone

        class LocationAdmin(VarCMSModelAdmin):
            list_display  = ["name", "address", "point", "is_active"]
            list_filter   = ["is_active"]
            search_fields = ["name", "address"]
            readonly_fields = ["created_at"]
            permissions = [RolePermission("superuser", add=True, list=True, view=True, edit=True, delete=True)]
            role_editable_fields = {"superuser": "__all__"}

        class ZoneAdmin(VarCMSModelAdmin):
            list_display  = ["name", "boundary", "created_at"]
            search_fields = ["name", "description"]
            readonly_fields = ["created_at"]
            permissions = [RolePermission("superuser", add=True, list=True, view=True, edit=True, delete=True)]
            role_editable_fields = {"superuser": "__all__"}

        var_cms_site.register(Location, LocationAdmin)
        var_cms_site.register(Zone, ZoneAdmin)
except Exception:
    pass
