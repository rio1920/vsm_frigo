from django import template

register = template.Library()

@register.filter
def has_perm(user, perm_name):
    """
    Verifica si el usuario tiene un permiso específico.
    Uso: {% if request.user|has_perm:"permiso" %}
    """
    if not user.is_authenticated:
        return False
    return user.permisos.filter(nombre=perm_name).exists()