from django import template
from django.utils.html import mark_safe

register = template.Library()


@register.filter
def cms_field_label(field):
    return field.label or field.name


@register.simple_tag
def cms_list_url(app, model_name):
    from django.urls import reverse
    return reverse(f"cms:{app}_{model_name}_list")


@register.simple_tag
def cms_add_url(app, model_name):
    from django.urls import reverse
    return reverse(f"cms:{app}_{model_name}_add")


@register.simple_tag
def cms_edit_url(app, model_name, pk):
    from django.urls import reverse
    return reverse(f"cms:{app}_{model_name}_edit", args=[pk])


@register.simple_tag
def cms_delete_url(app, model_name, pk):
    from django.urls import reverse
    return reverse(f"cms:{app}_{model_name}_delete", args=[pk])


@register.filter(is_safe=True)
def safe_html(value):
    return mark_safe(value)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """Preserve existing GET params while changing specific ones."""
    request = context["request"]
    params = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            params.pop(k, None)
        else:
            params[k] = v
    return params.urlencode()
