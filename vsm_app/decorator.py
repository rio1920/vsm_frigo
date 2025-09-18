from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import render

def permission_required(required_permissions):
    """
    Decorador para verificar si el usuario tiene al menos uno de los permisos requeridos.
    `required_permissions` puede ser un string (ej: "registros_can_view")
    o una lista de strings (ej: ["registros_can_view", "registros_can_edit"]).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                return HttpResponseForbidden("Usuario no autenticado.")

            if not user.rol:
                return HttpResponseForbidden("El usuario no tiene un rol asignado.")

            # Traer permisos activos como strings
            Usuario  = request.user

            permisos_del_rol = Usuario.rol.permisos.values_list(
                'nombre', flat=True
            )
            permisos_asignados = set(permisos_del_rol)

            # Normalizar siempre a lista
            if isinstance(required_permissions, str):
                required_permissions_list = [required_permissions]
            else:
                required_permissions_list = required_permissions

            # Verificar si al menos uno de los permisos está asignado
            if not any(perm in permisos_asignados for perm in required_permissions_list):
                return render(request, "403.html", status=403)

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator