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
    apellido = models.CharField(max_length=100)
    empresa = models.CharField(max_length=100)
    cc = models.ForeignKey(centro_costos, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.cc.descripcion}"


class maestro_de_materiales(models.Model):
    codigo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

class cc_permisos(models.Model):
    cc = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    empleado = models.ForeignKey(empleados, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.empleado.nombre} {self.empleado.apellido} - {self.cc.codigo}"

class permisos(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

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
    active = models.BooleanField(default=True)
    groups = models.ManyToManyField(
        "auth.Group", related_name="usuarios_set", blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission", related_name="usuarios_permissions_set", blank=True
    )

    def __str__(self):
        return self.username

    def get_user_permissions(self):
        return self.rol.permisos.all()

        
class VSM(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('entregado', 'Entregado'),
        ('parcial', 'Parcial'),
        ('rechazado', 'Rechazado'),
    ]
    centro_costos = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE)
    retirante = models.ForeignKey(empleados, related_name='retirante', on_delete=models.CASCADE)
    productos = models.ManyToManyField('maestro_de_materiales', through='VSMProducto')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(null=True, blank=True)
    observaciones_entrega = models.TextField(null=True, blank=True)
    numero_sap = models.CharField(max_length=50, blank=True, null=True)
    active = models.BooleanField(default=True)

    def entrega_completa(self):
        return self.estado == 'entregado' and self.cantidad_entregada == self.cantidad_solicitada

class VSMProducto(models.Model):
    vsm = models.ForeignKey(VSM, on_delete=models.CASCADE)
    producto = models.ForeignKey('maestro_de_materiales', on_delete=models.CASCADE)
    cantidad_solicitada = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_entregada = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

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
