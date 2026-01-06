from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.

class centro_costos(models.Model):
    codigo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

class almacenes(models.Model):
    almacen = models.CharField(max_length=5)
    empresa = models.ForeignKey(
        "empresas", on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return f"{self.almacen} - {self.empresa.empresa if self.empresa else 'Sin Empresa'}"
    
class empresas (models.Model):
    empresa = models.CharField(max_length=5)
    descripcion = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.empresa} - {self.descripcion}"

class empleados(models.Model):
    legajo = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=100)
    cc = models.ForeignKey(
        centro_costos, on_delete=models.CASCADE, null=True, blank=True
    )
    nro_tarjeta = models.ManyToManyField("nro_tarjeta", blank=True)
    perfil_riesgo = models.ForeignKey(
        "perfil_riesgo", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.nombre} - {self.cc.descripcion if self.cc else 'Sin CC'}"


class maestro_de_materiales(models.Model):
    codigo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)
    clase_sap = models.CharField(max_length=10)
    centro = models.CharField(max_length=4)
    almacen = models.OneToOneField(
        almacenes, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class permisos(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Usuarios(AbstractUser):
    empleado = models.OneToOneField(
        empleados, on_delete=models.CASCADE, null=True, blank=True
    )
    permisos = models.ManyToManyField(permisos, related_name="usuarios", blank=True)
    cc_permitidos = models.ManyToManyField(
        centro_costos, related_name="usuarios_permitidos", blank=True
    )
    empresas = models.ManyToManyField(
        empresas, related_name="usuarios_empresas", blank=True
    )

    def __str__(self):
        return self.username

    def get_user_permissions(self):
        return self.permisos.all()


class VSM(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("entregado", "Entregado"),
        ("rechazado", "Rechazado"),
    ]
    centro_costos = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    solicitante = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
    retirante = models.ForeignKey(
        empleados, related_name="retirante", on_delete=models.CASCADE
    )
    productos = models.ManyToManyField("maestro_de_materiales", through="VSMProducto")
    tipo_entrega = models.CharField(
        max_length=20,
        choices=[("INSUMOS", "Insumos"), ("EPP", "EPP")],
        null=True,
        blank=True,
    )
    tipo_facturacion = models.CharField(
        max_length=20,
        choices=[("FACTURADO", "Facturado"), ("NO_FACTURADO", "No facturado")],
        null=True,
        blank=True,
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="pendiente"
    )
    observaciones = models.TextField(null=True, blank=True)
    observaciones_entrega = models.TextField(null=True, blank=True)
    numero_sap = models.CharField(max_length=50, blank=True, null=True)
    anio_documento = models.CharField(max_length=4, null=True, blank=True)
    almacen = models.ForeignKey(almacenes, on_delete=models.CASCADE, null=True, blank=True)
    active = models.BooleanField(default=True)
    estado_sap = models.CharField(
        max_length=20,
        choices=[
            ("procesado", "Procesado"),
            ("no_procesado", "No Procesado"),
            ("error", "Error"),
        ],
        default="no_procesado",
    )
    actualizado = models.DateTimeField(auto_now=True)
    estado_aprobacion = models.CharField(
        max_length=20,
        choices=[
            ("APROBADO", "Aprobado"), 
            ("RECHAZADO", "Rechazado"), 
            ("PENDIENTE", "Pendiente")
        ],
        default="APROBADO",
    )

    def entrega_completa(self):
        return (
            self.estado == "entregado"
            and self.cantidad_entregada == self.cantidad_solicitada
        )

class VSMProducto(models.Model):
    vsm = models.ForeignKey(VSM, on_delete=models.CASCADE)
    producto = models.ForeignKey("maestro_de_materiales", on_delete=models.CASCADE)
    cantidad_solicitada = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_entregada = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0
    )
    firma_retirante = models.ImageField(upload_to="firmas/", null=True, blank=True)

    def __str__(self):
        return f"{self.producto.descripcion} - {self.cantidad_solicitada} unidades"


class PermisoRetiro(models.Model):
    centro_costo = models.ForeignKey(centro_costos, on_delete=models.CASCADE)
    producto = models.ManyToManyField(maestro_de_materiales)

    def __str__(self):
        return f"{self.centro_costo} - {self.centro_costo.descripcion}"


class tags_productos(models.Model):
    descripcion = models.CharField(max_length=20)

    def __str__(self):
        return self.descripcion


class perfil_riesgo(models.Model):
    nombre = models.CharField(max_length=100)
    tags_productos = models.ManyToManyField(
        tags_productos, related_name="perfiles", blank=True, default=None
    )

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
        unique_together = ("centro_costo", "perfil_riesgo", "default")

class permiso_empresa_almacen(models.Model):
    empresa = models.ForeignKey(empresas, on_delete=models.CASCADE)
    almacen = models.ForeignKey(almacenes, on_delete=models.CASCADE)
    requiere_aprobacion = models.BooleanField(default=False)
    usuarios_aprobadores = models.ManyToManyField(Usuarios, blank=True)

    def __str__(self):
        return f"{self.empresa} - {self.almacen}"

    class Meta:
        unique_together = ("empresa", "almacen")