from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

# Create your models here.

class centro_costos(models.Model):
    codigo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class empleados(models.Model):
    legajo = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=100)
    cc = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    nro_tarjeta = models.ManyToManyField('nro_tarjeta', blank=True)
    perfil_riesgo = models.ForeignKey('perfil_riesgo', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.cc.descripcion}"

    def get_cc(self):
        return f"{self.cc.codigo} - {self.cc.descripcion}"


class maestro_de_materiales(models.Model):
    codigo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)
    clase_sap = models.CharField(max_length=10)
    cantidad_stock = models.DecimalField(max_digits=10, decimal_places=0)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class permisos(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.nombre

class Roles(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    permisos = models.ManyToManyField(permisos, related_name='roles')

    def __str__(self):
        return self.nombre

class Usuarios(AbstractUser):
    empleado = models.OneToOneField(
        empleados, on_delete=models.CASCADE, null=True, blank=True
    )
    rol = models.ForeignKey(Roles, on_delete=models.CASCADE, null=True, blank=True)
    cc_permitidos = models.ManyToManyField(centro_costos, related_name='usuarios_permitidos', blank=True)

    def __str__(self):
        return self.username

    def get_user_permissions(self):
        return self.rol.permisos.all()

class VSM(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado'),
    ]
    centro_costos = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    solicitante = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
    retirante = models.ForeignKey(empleados, related_name='retirante', on_delete=models.CASCADE)
    productos = models.ManyToManyField('maestro_de_materiales', through='VSMProducto')
    tipo_entrega = models.CharField(
        max_length=20,
        choices=[('INSUMOS', 'Insumos'), ('EPP', 'EPP')],
        null=True, blank=True
    )
    tipo_facturacion = models.CharField(
        max_length=20,
        choices=[('FACTURADO', 'Facturado'), ('NO_FACTURADO', 'No facturado')],
        null=True, blank=True
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(null=True, blank=True)
    observaciones_entrega = models.TextField(null=True, blank=True)
    numero_sap = models.CharField(max_length=50, blank=True, null=True)
    active = models.BooleanField(default=True)
    estado_sap = models.CharField(max_length=20, choices=[('procesado', 'Procesado'), ('no_procesado', 'No Procesado'), ('error', 'Error')], default='no_procesado')
    actualizado = models.DateTimeField(auto_now=True)

    def entrega_completa(self):
        return self.estado == 'entregado' and self.cantidad_entregada == self.cantidad_solicitada

class VSMProducto(models.Model):
    vsm = models.ForeignKey(VSM, on_delete=models.CASCADE)
    producto = models.ForeignKey('maestro_de_materiales', on_delete=models.CASCADE)
    cantidad_solicitada = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_entregada = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)

    def __str__(self):
        return f"{self.producto.descripcion} - {self.cantidad_solicitada} unidades"

class epp(models.Model):
    codigo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

class PermisoRetiro(models.Model):
    centro_costo = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    producto = models.ManyToManyField(maestro_de_materiales)

    def __str__(self):
        return f"{self.centro_costo} - {self.centro_costo.descripcion}"

class tags_productos(models.Model):
    nombre = models.CharField(max_length=100)
    productos = models.ManyToManyField(maestro_de_materiales, related_name='tags')

    def __str__(self):
        return self.nombre

class perfil_riesgo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    tags_productos = models.ManyToManyField(tags_productos, related_name='perfiles')

    def __str__(self):
        return self.nombre

class nro_tarjeta(models.Model):
    numero = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.numero}"

class relacion_cc_perfil_riesgo(models.Model):
    centro_costo = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    perfil_riesgo = models.ForeignKey(perfil_riesgo, on_delete=models.CASCADE)
    default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.centro_costo} - {self.perfil_riesgo}"

    class Meta:
        unique_together = ('centro_costo', 'perfil_riesgo', 'default') 