from django import template

register = template.Library()

@register.filter
def adminsort(value):
    """
    Sort hidden fields in the order they should be displayed.
    This is a simplified version that just returns the input.
    In a real implementation, this might sort by field name or by a predefined order.
    """
    return value