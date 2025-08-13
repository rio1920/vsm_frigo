from django.shortcuts import render
from . import models
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import HttpResponse
from .models import empleados


def home(request):

    return render(request, "home.html")

def registros(request):
    vales = models.VSM.objects.all().order_by('-fecha_solicitud')
    paginator = Paginator(vales, 7)  

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'registros': page_obj,
        'page_obj': page_obj
    }

    return render(request, "registros.html", context)

from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now

def nuevo_vsm(request):
    productos = models.maestro_de_materiales.objects.all()
    empleados = models.empleados.objects.all()
    centro_costos = models.centro_costos.objects.all()
    usuario_logeado = request.user
    print(request.POST)

    if request.method == 'POST':
        solicitante_id = request.POST.get('solicitante')
        observaciones = request.POST.get('detalles', '')
        centro_costos_id = request.POST.get('centro_costos')

        if not solicitante_id:
            return render(request, "nuevo_vsm.html", {
                'productos': productos,
                'empleados': empleados,
                'error': 'Debe seleccionar un solicitante.'
            })

        solicitante = get_object_or_404(models.empleados, id=solicitante_id)

        vsm = models.VSM.objects.create(
            centro_costos_id=centro_costos_id,
            solicitante=usuario_logeado,
            retirante=solicitante,
            fecha_solicitud=now(),
            observaciones=observaciones
        )

        # Iterar por los productos enviados
        for key, value in request.POST.items():
            if key.startswith('producto_'):
                try:
                    producto_id = int(key.split('_')[1])
                    cantidad_solicitada = int(value)
                    if cantidad_solicitada > 0:
                        producto = get_object_or_404(models.maestro_de_materiales, id=producto_id)
                        models.VSMProducto.objects.create(
                            vsm=vsm,
                            producto=producto,
                            cantidad_solicitada=cantidad_solicitada
                        )
                except (ValueError, IndexError):
                    continue

        return redirect('home')  

    return render(request, "nuevo_vsm.html", {
        'productos': productos,
        'empleados': empleados,
        'usuario_logeado': usuario_logeado,
        'centro_costos': centro_costos
    })



    

def detalle_vsm(request, id):
    vsm = models.VSM.objects.get(id=id)
    context = {
        'vsm': vsm
    }

    return render(request, "detalle_vsm.html", context)

def editar_vsm(request, id):
    vsm = models.VSM.objects.get(id=id)
    productos = models.maestro_de_materiales.objects.all()

    if request.method == 'POST':
        vsm.nombre = request.POST.get('nombre')
        vsm.descripcion = request.POST.get('descripcion')
        vsm.producto = request.POST.get('producto')
        vsm.save()
        return render(request, "detalle_vsm.html", {'vsm': vsm})

    context = {
        'vsm': vsm,
        'productos': productos
    }

    return render(request, "editar_vsm.html", context)

def eliminar_vsm(request, id):
    vsm = models.VSM.objects.get(id=id)
    
    if request.method == 'POST':
        vsm.delete()
        return render(request, "registros.html", {'message': 'VSM eliminado exitosamente.'})

    context = {
        'vsm': vsm
    }

    return render(request, "registros.html", context)

def confirmar_entrega(request, vsm_id):
    vsm = models.VSM.objects.prefetch_related('vsmproducto_set__producto').get(id=vsm_id)

    if request.method == 'POST':
        cantidad_entregada = request.POST.get('cantidad_entregada')
        observaciones_entrega = request.POST.get('observaciones_entrega')

        vsm.cantidad_entregada = cantidad_entregada
        vsm.observaciones_entrega = observaciones_entrega
        vsm.fecha_entrega = timezone.now()

        if float(cantidad_entregada) >= float(vsm.cantidad_solicitada):
            vsm.estado = 'entregado'
        else:
            vsm.estado = 'parcial'

        vsm.save()

        return redirect('home')

    return render(request, 'confirmar_entrega.html', {'vsm': vsm})

def rechazar_entrega(request, vsm_id):
    vsm = get_object_or_404(models.VSM, pk=vsm_id)

    if request.method == 'POST':
        vsm.estado = 'Rechazado'
        vsm.save()
        return redirect('listar_vsm_pendientes')

    return render(request, 'listar_vsm_pendientes.html', {'vsm': vsm})

def listar_vsm_pendientes(request):
    vales = (
        models.VSM.objects
        .filter(estado__in=['pendiente', 'parcial'])
        .prefetch_related('vsmproducto_set__producto')  
        .order_by('-fecha_solicitud')
    )

    paginator = Paginator(vales, 7)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'pendientes': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'listar_vsm_pendientes.html', context)


def listar_vsm_rechazados(request):
    vales = (
        models.VSM.objects
        .filter(estado='rechazado')
        .prefetch_related('vsmproducto_set__producto')  
        .order_by('-fecha_solicitud')
    )
    paginator = Paginator(vales, 7)  

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'rechazados': page_obj,
        'page_obj': page_obj,
    }

    return render(request, 'listar_vsm_rechazados.html', context)
     
def detalle_vsm(request, pk):
    vsm = get_object_or_404(VSM, pk=pk)
    return render(request, "detalle_vsm.html", {'vsm': vsm})

def buscar_solicitantes(request):
    query = request.GET.get('q', '')

    if query:
        empleados_filtrados = models.empleados.objects.filter(
            Q(nombre__icontains=query) | Q(apellido__icontains=query)
        )[:10]
    else:
        empleados_filtrados = models.empleados.objects.all()[:10]  

    results = [
        {
            'id': emp.id,
            'text': f"{emp.nombre} {emp.apellido} ({emp.legajo})"
        }
        for emp in empleados_filtrados
    ]

    return JsonResponse({'results': results})


def obtener_empleados_por_centro(request):
    centro_id = request.GET.get('centro_id')
    empleados_qs = empleados.objects.filter(cc_id=centro_id).values('id', 'nombre', 'apellido', 'legajo')
    empleados_list = list(empleados_qs)
    return JsonResponse({'empleados': empleados_list})

def buscar_productos(request):
    query = request.GET.get('q', '')
    centro_costo_id = request.GET.get('centro_costo', None)

    productos = models.maestro_de_materiales.objects.all()

    # Si hay centro de costo, filtramos por permisos
    if centro_costo_id:
        productos = productos.filter(
            id__in=models.PermisoRetiro.objects.filter(
                centro_costo_id=centro_costo_id
            ).values_list('producto', flat=True)
        )

    # Filtro por descripción
    if query:
        productos = productos.filter(descripcion__icontains=query)

    productos = productos[:20]

    results = [
        {'id': p.id, 'text': p.descripcion}
        for p in productos
    ]
    return JsonResponse({'results': results})

def nuevo_epp(request):
    empleados = models.empleados.objects.all()
    centro_costos = models.centro_costos.objects.all()
    productos = models.maestro_de_materiales.objects.all()
    usuario_logeado = request.user

    if request.method == 'POST':
        solicitante_id = request.POST.get('solicitante')
        centro_costos_id = request.POST.get('centro_costos')
        detalles = request.POST.get('detalles', '')

        if not solicitante_id:
            return render(request, "nuevo_epp.html", {
                'empleados': empleados,
                'error': 'Debe seleccionar un solicitante.'
            })

        solicitante = get_object_or_404(models.empleados, id=solicitante_id)

        epp = models.EPP.objects.create(
            centro_costos_id=centro_costos_id,
            solicitante=usuario_logeado,
            retirante=solicitante,
            fecha_solicitud=now(),
            detalles=detalles
        )

        return redirect('home')  

    return render(request, "nuevo_epp.html", {
        'empleados': empleados,
        'usuario_logeado': usuario_logeado,
        'centro_costos': centro_costos,
        'productos': productos
    })