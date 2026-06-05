from django import template
from django.db import models
from django.urls import reverse
from django.utils.html import format_html, mark_safe

register = template.Library()


@register.simple_tag
def var_cms_list_url(app, model_name):
    return reverse(f"var_cms:var_cms_{app}_{model_name}_list")


@register.simple_tag
def var_cms_add_url(app, model_name):
    return reverse(f"var_cms:var_cms_{app}_{model_name}_add")


@register.simple_tag
def var_cms_edit_url(app, model_name, pk):
    return reverse(f"var_cms:var_cms_{app}_{model_name}_edit", args=[pk])


@register.simple_tag
def var_cms_delete_url(app, model_name, pk):
    return reverse(f"var_cms:var_cms_{app}_{model_name}_delete", args=[pk])


@register.simple_tag
def var_cms_view_url(app, model_name, pk):
    return reverse(f"var_cms:var_cms_{app}_{model_name}_view", args=[pk])


@register.filter(is_safe=True)
def safe_html(value):
    return mark_safe(value)


@register.filter
def get_item(dictionary, key):
    if hasattr(dictionary, "get"):
        return dictionary.get(key)
    return None


@register.filter
def index(lst, i):
    try:
        return lst[i]
    except (IndexError, TypeError):
        return ""


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    request = context["request"]
    params = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            params.pop(k, None)
        else:
            params[k] = v
    return params.urlencode()


@register.simple_tag
def var_cms_field_preview(obj, field_name):
    """Return HTML preview snippet for a file/image field on an existing object."""
    if obj is None:
        return ""
    try:
        field = obj._meta.get_field(field_name)
        value = getattr(obj, field_name, None)
        if not value:
            return ""

        if isinstance(field, models.ImageField):
            return format_html(
                '<img src="{}" class="preview-thumb" data-preview="{}" title="Click to open" style="height:48px;width:48px;" />',
                value.url, value.url
            )
        if isinstance(field, models.FileField):
            ext = str(value.name).rsplit(".", 1)[-1].lower()
            icon_name = {"mp4": "video", "webm": "video", "mov": "video",
                         "mp3": "music", "wav": "music", "ogg": "music",
                         "pdf": "file-text"}.get(ext, "paperclip")
            return format_html(
                '<i data-lucide="{}" style="width:14px;height:14px;display:inline-block;vertical-align:middle;margin-right:4px;"></i>'
                '<a href="{}" class="file-preview-link" data-ext="{}" data-url="{}">{}</a>',
                icon_name, value.url, ext, value.url, value.name.split("/")[-1]
            )
    except Exception:
        pass
    return ""


@register.filter
def form_field_grid_style(field, admin):
    """Return the CSS style rule specifying grid column span for the field container.
    
    Priority order:
    1. form_field_widths (explicit override)
    2. form_field_rows (auto-computed equal split)
    3. Default heuristic (textarea/checkbox = full, others = half)
    """
    widths = getattr(admin, "form_field_widths", {})
    width = widths.get(field.html_name) if widths else None

    mapping = {
        "full": "grid-column: span 12;",
        "half": "grid-column: span 6;",
        "one-third": "grid-column: span 4;",
        "two-thirds": "grid-column: span 8;",
        "one-fourth": "grid-column: span 3;",
        "three-fourths": "grid-column: span 9;",
    }

    if width in mapping:
        style = mapping[width]
    else:
        # Check form_field_rows: if this field is grouped in a row, compute equal span
        rows = getattr(admin, "form_field_rows", [])
        row_span = None
        if rows:
            for row in rows:
                if field.html_name in row:
                    count = len(row)
                    # 12-col grid: split equally, floor to nearest valid value
                    span = max(1, 12 // count)
                    row_span = f"grid-column: span {span};"
                    break
        
        if row_span:
            style = row_span
        else:
            # Default heuristic
            widget_str = str(field.field.widget)
            input_type = getattr(field.field.widget, "input_type", "")
            if "Checkbox" in widget_str or input_type == "checkbox" or "Textarea" in widget_str or input_type == "textarea":
                style = "grid-column: span 12;"
            else:
                style = "grid-column: span 6;"

    # Combine with any custom inline styles
    custom_styles = getattr(admin, "form_field_styles", {})
    if custom_styles and field.html_name in custom_styles:
        style = f"{style} {custom_styles[field.html_name]}"

    return style


@register.filter
def field_widget_type(field, admin):
    """Return the custom widget type for a field, or empty string."""
    widgets = getattr(admin, "form_field_widgets", {})
    return widgets.get(field.html_name, "")
