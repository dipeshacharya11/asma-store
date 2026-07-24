from django import template
import json

register = template.Library()


@register.filter
def split(value, delimiter=","):
    """
    Split a string into a list.
    """
    if not value:
        return []
    return str(value).split(delimiter)


@register.filter
def trim(value):
    """
    Remove leading and trailing whitespace.
    """
    if value is None:
        return ""
    return str(value).strip()


@register.filter
def json_loads(value):
    """
    Parse a JSON string to a Python object.
    """
    if not value:
        return []
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []