import logging
from django.conf import settings

logger = logging.getLogger('django')

class PathInspectorMiddleware:
    """
    Este Middleware intercepta la solicitud inmediatamente después de que es recibida
    por Django para imprimir la ruta exacta que se está intentando resolver.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("PathInspectorMiddleware inicializado.")

    def __call__(self, request):
        # La ruta que Django está intentando resolver (incluye cualquier prefijo)
        full_path = request.path
        
        # Opcional: la ruta sin el prefijo de la URL de la aplicación
        # (usando request.path_info)
        path_info = request.path_info 
        
        logger.warning(f"RUTA RECIBIDA POR DJANGO: {full_path}")
        logger.warning(f"PATH_INFO (sin prefijo URLconf): {path_info}")

        response = self.get_response(request)
        return response