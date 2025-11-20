from django import template

register = template.Library()

@register.filter
def status_badge_color(status):
    """Returns Tailwind color classes based on validation status."""
    colors = {
        'pendente': 'bg-gray-50 text-gray-600 ring-gray-500/10',
        'em_analise': 'bg-yellow-50 text-yellow-800 ring-yellow-600/20',
        'aprovado': 'bg-green-50 text-green-700 ring-green-600/20',
        'reprovado': 'bg-red-50 text-red-700 ring-red-600/20',
    }
    return colors.get(status, 'bg-gray-50 text-gray-600 ring-gray-500/10')


@register.filter
def dict_get(dictionary, key):
    """Get value from dictionary by key - works with objects as keys."""
    if dictionary is None:
        return []
    return dictionary.get(key, [])


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
