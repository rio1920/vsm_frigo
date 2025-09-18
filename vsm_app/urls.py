from django.contrib import admin
from django.urls import path
from vsm_app import views

urlpatterns = [
    path('', views.home, name='index'),  # Default route
    path('home/', views.home, name='home'),
    path('registros/', views.registros, name='registros'),
    path('nuevo_vsm/', views.nuevo_vsm, name='nuevo_vsm'),
    path('editar_vsm/<int:id>/', views.editar_vsm, name='editar_vsm'),
    path('eliminar_vsm/<int:id>/', views.eliminar_vsm, name='eliminar_vsm'),
    path('pendientes/', views.listar_vsm_pendientes, name='listar_vsm_pendientes'),
    path('entregar/<int:vsm_id>/', views.confirmar_entrega, name='confirmar_entrega'),
    path('rechazar_entrega/<int:vsm_id>/', views.rechazar_entrega, name='rechazar_entrega'),
    path('detalle_vsm/<int:vsm_id>/', views.detalle_vsm, name='detalle_vsm'),
    path('buscar_solicitantes/', views.buscar_solicitantes, name='buscar_solicitantes'),
    path('ajax/empleados/', views.obtener_empleados_por_centro, name='obtener_empleados_por_centro'),
    path("api/materiales/", views.get_materiales_por_centro, name="get_materiales_por_centro"),
    path('buscar_productos_por_centro/', views.buscar_productos_por_centro, name='buscar_productos_por_centro'),
    path("pendiente/<int:vsm_id>/editar/", views.editar_pendiente, name="editar_pendiente"),
    path("pendiente/<int:vsm_id>/rechazar/", views.rechazar_pendiente, name="rechazar_pendiente"),
    path("pendiente/<int:vsm_id>/ver/", views.ver_pendiente, name="ver_pendiente"),
]
