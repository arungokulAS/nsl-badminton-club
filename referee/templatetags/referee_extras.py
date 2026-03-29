from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def range_list(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return []
    value = max(1, min(value, 3))
    return range(1, value + 1)
