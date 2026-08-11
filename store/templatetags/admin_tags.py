from django import template
from django.template.loader import render_to_string

register = template.Library()


@register.simple_tag(takes_context=True)
def admin_search_form(context):
    """
    Custom search form for the custom admin changelist.
    """
    request = context.get("request")
    cl = context.get("cl")

    return render_to_string(
        "admin/includes/search_form.html",
        {
            "request": request,
            "cl": cl,
        },
        request=request,
    )


@register.simple_tag(takes_context=True)
def admin_filters(context, hide_title=False):
    """
    Custom filter toolbar for the custom admin changelist.
    """
    request = context.get("request")
    cl = context.get("cl")

    filter_specs = []

    if cl:
        filter_specs = getattr(cl, "filter_specs", [])

    return render_to_string(
        "admin/includes/filters.html",
        {
            "request": request,
            "cl": cl,
            "filter_specs": filter_specs,
            "hide_title": hide_title,
        },
        request=request,
    )