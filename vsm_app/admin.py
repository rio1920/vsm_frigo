from django.contrib import admin
from .models import *

class VSMProductoInline(admin.TabularInline):
    model = VSMProducto
    extra = 1  # Número de filas vacías por defecto para agregar
    autocomplete_fields = ['producto']

class VSMAdmin(admin.ModelAdmin):
    list_display = ['id', 'solicitante','centro_costos', 'fecha_solicitud','retirante', 'estado', 'active']
    inlines = [VSMProductoInline]

    def mostrar_productos(self, obj):
        productos = obj.vsmproducto_set.all()
        return ", ".join([f"{vp.producto} (sol: {vp.cantidad_solicitada}, ent: {vp.cantidad_entregada or 0})" for vp in productos])
    mostrar_productos.short_description = "Productos" 

class CentroCostosAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion')
    search_fields = ('codigo', 'descripcion')

class EmpleadosAdmin(admin.ModelAdmin):
    list_display = ('legajo', 'nombre', 'get_cc')
    search_fields = ('nombre',)
    list_filter = ()

class MaestroDeMaterialesAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'clase_sap', 'cantidad_stock')
    search_fields = ('codigo', 'descripcion')
    list_filter = ()

class CcPermisosAdmin(admin.ModelAdmin):
    list_display = ('cc', 'empleado')
    search_fields = ('cc__codigo', 'empleado__nombre', 'empleado__apellido')

class UsuariosAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active')

class RolesAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

class PermisosAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

class PermisoRetiroAdmin(admin.ModelAdmin):
    list_display = ('centro_costo',)
    search_fields = ('centro_costo__codigo',)

class TagsProductosAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

class PerfilDeRiesgoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre', 'descripcion')


class NroTarjetaInline(admin.ModelAdmin):
    model = nro_tarjeta
    extra = 1

admin.site.register(tags_productos, TagsProductosAdmin)
admin.site.register(PerfilDeRiesgo, PerfilDeRiesgoAdmin)
admin.site.register(Roles, RolesAdmin)
admin.site.register(permisos, PermisosAdmin)
admin.site.register(VSM, VSMAdmin)
admin.site.register(centro_costos, CentroCostosAdmin)
admin.site.register(empleados, EmpleadosAdmin)
admin.site.register(Usuarios, UsuariosAdmin)
admin.site.register(maestro_de_materiales, MaestroDeMaterialesAdmin)
admin.site.register(PermisoRetiro, PermisoRetiroAdmin)
admin.site.register(nro_tarjeta, NroTarjetaInline)
