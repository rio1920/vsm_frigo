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
from .models import empleados, PermisoRetiro, VSM, VSMProducto
from django.contrib import messages
from .decorator import permission_required
from django.utils.safestring import mark_safe
import json
from xhtml2pdf import pisa
from .utils.sap_rfc import call_sap_rfc



def home(request):
    return render(request, "home.html")

@permission_required("registros_can_view")
def registros(request):
    vales = (
        models.VSM.objects
        .filter(estado__in=['pendiente', 'entregado'], active=True)
        .prefetch_related('vsmproducto_set__producto')
        .order_by('-fecha_solicitud')
    )
    paginator = Paginator(vales, 7)  

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    solicitante = request.GET.get('solicitante', '').strip()
    retirante = request.GET.get('retirante', '').strip()
    legajo = request.GET.get('legajo', '').strip()
    cc = request.GET.get('cc', '').strip()
    estado = request.GET.get('estado', '').strip()

    if solicitante:
        vales = vales.filter(solicitante__username__icontains=solicitante) 

    if retirante:
        vales = vales.filter(retirante__nombre__icontains=retirante)  

    if cc:
        vales = vales.filter(centro_costos__codigo__icontains=cc)

    if estado and estado != "#":
        vales = vales.filter(estado=estado)

    context = {
        'vales': vales,
        'registros': page_obj,
        'page_obj': page_obj,
        'filtros': {
            'solicitante': solicitante,
            'retirante': retirante,
            'cc': cc,
            'estado': estado,
        }
    }

    return render(request, "registros.html", context)

from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from vsm_app.utils.sap_rfc import get_stock_sap

@permission_required(["facturado_can_create", "no_facturado_can_create"])
def nuevo_vsm(request):
    empleados = models.empleados.objects.all()
    centro_costos = models.centro_costos.objects.all()
    usuario_logeado = request.user  
    centro_usuario = usuario_logeado.cc_permitidos.all()
    productos = models.maestro_de_materiales.objects.all()

    if request.method == 'POST':
        solicitante_id = request.POST.get('solicitante')
        observaciones = request.POST.get('detalles', '')
        centro_costos_id = request.POST.get('centro_costos')
        tipo_entrega = request.POST.get('tipo_entrega')
        tipo_facturacion = request.POST.get('tipo_facturacion')
        retirante = request.POST.get('retirante')

        if not solicitante_id:
            return render(request, "nuevo_vsm.html", {
                'productos': productos,
                'empleados': empleados,
                'error': 'Debe seleccionar un solicitante.'
            })

        # Validar stock de todos los productos antes de crear el VSM
        productos_solicitados = []
        for key, value in request.POST.items():
            if key.startswith('producto_'):
                try:
                    producto_id = int(key.split('_')[1])
                    cantidad_solicitada = int(value)
                    if cantidad_solicitada > 0:
                        producto = get_object_or_404(models.maestro_de_materiales, id=producto_id)
                        stock_actual = get_stock_sap(producto.codigo)

                        if stock_actual <= 0:
                            messages.error(request, f"No hay stock disponible en SAP para el producto {producto.codigo}.")
                            return render(request, "nuevo_vsm.html", {
                                'productos': productos,
                                'empleados': empleados,
                                'usuario_logeado': usuario_logeado,
                                'centro_costos': centro_costos,
                                'centro_usuario': centro_usuario
                            })
                        elif stock_actual < cantidad_solicitada:
                            messages.error(request, f"Stock insuficiente para el producto {producto.codigo}. Disponible: {stock_actual}")
                            return render(request, "nuevo_vsm.html", {
                                'productos': productos,
                                'empleados': empleados,
                                'usuario_logeado': usuario_logeado,
                                'centro_costos': centro_costos,
                                'centro_usuario': centro_usuario
                            })

                        productos_solicitados.append((producto, cantidad_solicitada))
                except (ValueError, IndexError):
                    continue

        retirante_obj = None
        if retirante:
            retirante_obj = get_object_or_404(models.empleados, pk=retirante) 

        vsm = models.VSM.objects.create(
            centro_costos_id=centro_costos_id,
            solicitante=usuario_logeado,
            retirante=retirante_obj,
            fecha_solicitud=now(),
            observaciones=observaciones,
            tipo_entrega=tipo_entrega,
            tipo_facturacion=tipo_facturacion
        )

        for producto, cantidad_solicitada in productos_solicitados:
            models.VSMProducto.objects.create(
                vsm=vsm,
                producto=producto,
                cantidad_solicitada=cantidad_solicitada
            )

        messages.success(request, "✅ VSM creado con éxito")
        return redirect('home')

    return render(request, "nuevo_vsm.html", {
        'productos': productos,
        'empleados': empleados, 
        'usuario_logeado': usuario_logeado,
        'centro_costos': centro_costos,
        'centro_usuario': centro_usuario
    })



def detalle_vsm(request, id):
    vsm = models.VSM.objects.get(id=id)
    context = {
        'vsm': vsm
    }

    return render(request, "detalle_vsm.html", context)

@permission_required(["facturado_can_edit", "no_facturado_can_edit"])
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


@permission_required(["facturado_can_edit", "no_facturado_can_edit"])
def eliminar_vsm(request, id):
    vsm = models.VSM.objects.get(id=id)
    
    if request.method == 'POST':
        vsm.delete()
        return render(request, "registros.html", {'message': 'VSM eliminado exitosamente.'})

    context = {
        'vsm': vsm
    }

    return render(request, "registros.html", context)

@permission_required(["facturado_can_deliver", "no_facturado_can_deliver"])
def confirmar_entrega(request, vsm_id):
    vsm = models.VSM.objects.prefetch_related('vsmproducto_set__producto').get(id=vsm_id)
    tarjetas = list(vsm.retirante.nro_tarjeta.values_list("numero", flat=True))
    firma_empleado = vsm.retirante.id if vsm.retirante else None

    if request.method == 'POST':
        observaciones_entrega = request.POST.get('observaciones_entrega')

        # recorrer cada producto del VSM
        for vp in vsm.vsmproducto_set.all():
            cantidad_str = request.POST.get(f'cantidad_entregada_{vp.id}', 0)
            try:
                cantidad = float(cantidad_str) if cantidad_str else 0
            except ValueError:
                cantidad = 0
            vp.firma_empleado = firma_empleado
            vp.cantidad_entregada = cantidad
            vp.save()

        vsm.observaciones_entrega = observaciones_entrega
        vsm.fecha_entrega = timezone.now()

        entregado_completo = all(
            (vp.cantidad_entregada) >= 1
            for vp in vsm.vsmproducto_set.all()
        )

        vsm.estado = 'entregado' if entregado_completo else 'pendiente'

        vsm.save()

        return JsonResponse({"success": True, "estado": vsm.estado})

    return render(request, 'confirmar_entrega.html', {'vsm': vsm, "tarjetas_json": mark_safe(json.dumps(tarjetas))})

@permission_required(["facturado_can_deliver", "no_facturado_can_deliver"])
def rechazar_entrega(request, vsm_id):
    vsm = get_object_or_404(models.VSM, id=vsm_id)

    if request.method == 'POST':
        motivo = request.POST.get('observaciones_entrega', '')
        vsm.estado = 'rechazado'
        vsm.observaciones_entrega = motivo
        vsm.fecha_entrega = timezone.now()
        vsm.save()
        return redirect('listar_vsm_pendientes')

    return render(request, 'rechazar_entrega.html', {'vsm': vsm})

@permission_required(["facturado_can_deliver", "no_facturado_can_deliver"])
def listar_vsm_pendientes(request):
    vales = (
        models.VSM.objects
        .filter(estado__in=['pendiente', 'entregado'], active=True)
        .prefetch_related('vsmproducto_set__producto')
        .order_by('-fecha_solicitud')
    )

    solicitante = request.GET.get('solicitante', '').strip()
    retirante = request.GET.get('retirante', '').strip()
    legajo = request.GET.get('legajo', '').strip()
    cc = request.GET.get('cc', '').strip()
    estado = request.GET.get('estado', '').strip()

    if solicitante:
        vales = vales.filter(solicitante__username__icontains=solicitante) 

    if retirante:
        vales = vales.filter(retirante__nombre__icontains=retirante)  

    if cc:
        vales = vales.filter(centro_costos__codigo__icontains=cc)

    if estado and estado != "#":
        vales = vales.filter(estado=estado)

    paginator = Paginator(vales, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'pendientes': page_obj,
        'page_obj': page_obj,
        'filtros': {    
            'solicitante': solicitante,
            'retirante': retirante,
            'cc': cc,
            'estado': estado,
        }
    }
    return render(request, 'listar_vsm_pendientes.html', context)

     
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
    empleados_qs = empleados.objects.filter(cc_id=centro_id).values('id','nombre','legajo')
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

from vsm_app.utils.sap_rfc import get_stock_sap_multiple 

def buscar_productos_por_centro(request):
    query = request.GET.get('q', '')
    centro_id = request.GET.get('centro_costo')
    tipo_entrega = request.GET.get('tipo_entrega')

    if not centro_id:
        return JsonResponse({'results': []})

    try:
        permiso = PermisoRetiro.objects.get(centro_costo_id=centro_id)
        productos = permiso.producto.filter(descripcion__icontains=query)

        if tipo_entrega == "EPP":
            productos = productos.filter(clase_sap="EPP")
        elif tipo_entrega == "INSUMOS":
            productos = productos.exclude(clase_sap="EPP")

        productos = productos[:20]

    except PermisoRetiro.DoesNotExist:
        return JsonResponse({'results': []})

    if not productos:
        print("⚠️ No hay productos locales para ese centro o búsqueda")
        return JsonResponse({'results': []})

    codigos = [p.codigo for p in productos if p.codigo]
    print("📦 Códigos consultados a SAP:", codigos)

    stock_dict = get_stock_sap_multiple(codigos, debug=True)
    print("📊 Stock devuelto por SAP:", stock_dict)

    results = []
    for p in productos:
        stock = stock_dict.get(p.codigo, None)
        print(f"➡️ {p.codigo} -> stock {stock}")

        if stock and stock > 0:
            results.append({
                'id': p.id,
                'text': f"{p.descripcion} ({p.codigo}) — STOCK: {stock}"
            })

    if not results:
        print("❌ Ningún producto con stock > 0")
        results = [{'id': '0', 'text': '⚠️ No hay productos con stock disponible'}]

    return JsonResponse({'results': results})


def get_materiales_por_centro(request):
    centro_id = request.GET.get("centro_id")

    if not centro_id:
        return JsonResponse({"error": "Centro no especificado"}, status=400)

    permisos = PermisoRetiro.objects.filter(centro_costo_id=centro_id)

    materiales = maestro_de_materiales.objects.filter(permisoretiro__in=permisos).distinct()

    data = [
        {"id": m.id, "nombre": f"{m.codigo} - {m.descripcion}"}
        for m in materiales
    ]

    return JsonResponse(data, safe=False)


def editar_pendiente(request, vsm_id):  
    vsm = get_object_or_404(models.VSM, id=vsm_id, estado="pendiente")
    centro_costos = models.centro_costos.objects.all()
    empleados = models.empleados.objects.all()
    tipo_entrega_choices = models.VSM.tipo_entrega
    tipo_facturacion_choices = models.VSM.tipo_facturacion

    if request.method == "POST":
        observaciones = request.POST.get("detalles", "")
        tipo_entrega = request.POST.get("tipo_entrega")
        tipo_facturacion = request.POST.get("tipo_facturacion")
        retirante_id = request.POST.get("retirante")
        productos = request.POST.getlist("productos[]")
        cantidades = request.POST.getlist("cantidades[]")   

        vsm.observaciones = observaciones
        vsm.retirante = empleados.get(id=retirante_id) if retirante_id else None
        vsm.tipo_entrega = tipo_entrega
        vsm.tipo_facturacion = tipo_facturacion
        vsm.vsmproducto_set.all().delete()


        vsm.fecha_modificacion = now()  
        vsm.save()

        messages.success(request, "✅ VSM editado correctamente")
        return redirect("registros")

    return render(request, "editar_pendiente.html",
     {"vsm": vsm, "centro_costos": centro_costos, "empleados": empleados,
      "tipo_entrega_choices": tipo_entrega_choices, "tipo_facturacion_choices": tipo_facturacion_choices})

def rechazar_pendiente(request, vsm_id):
    vsm = get_object_or_404(models.VSM, id=vsm_id, estado="pendiente")

    if request.method == "POST":
        motivo = request.POST.get("motivo", "")
        vsm.estado = "RECHAZADO"
        vsm.motivo_rechazo = motivo
        vsm.fecha_modificacion = now()
        vsm.save()

        messages.error(request, "❌ VSM rechazado correctamente")
        return redirect("home")

    return render(request, "rechazar_vsm.html", {"vsm": vsm})

def ver_pendiente(request, vsm_id):
    vsm = get_object_or_404(models.VSM, id=vsm_id)
    productos = vsm.vsmproducto_set.select_related('producto').all()
    return render(request, "ver_pendiente.html", {"vsm": vsm, "productos": productos})


def get_tags_por_empleado(request, empleado_id):
    empleado = get_object_or_404(empleados, id=empleado_id)

    if not empleado.perfil_riesgo:
        return JsonResponse([], safe=False)

    tags = empleado.perfil_riesgo.tags_productos.all()

    data = [{"id": t.id, "descripcion": t.descripcion} for t in tags]
    return JsonResponse(data, safe=False)

def generar_pdf(request, vsm_id):
    vsm = get_object_or_404(VSM, id=vsm_id)
    productos = vsm.vsmproducto_set.select_related('producto').all()

    template_path = 'vsm_pdf.html'
    context = {'vsm': vsm, 'productos': productos}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="VSM_{vsm.id}.pdf"'

    html = render_to_string(template_path, context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
    
    return response

def generar_template_insumo(request, vsm_id):

    vsm = get_object_or_404(VSM, id=vsm_id)
    productos = vsm.vsmproducto_set.select_related('producto').all()

    context = {'vsm': vsm, 'productos': productos}
    return render(request, 'vsm_pdf.html', context)

def generar_template_epp(request, vsm_id):

    vsm = get_object_or_404(VSM, id=vsm_id)
    productos = vsm.vsmproducto_set.select_related('producto').all()

    context = {'vsm': vsm, 'productos': productos}
    return render(request, 'epp_pdf.html', context)

def test_sap_connection(request):
    data = call_sap_rfc("ZRFC_STOCK_SMARTSAFETY")
    return JsonResponse({"data": data}, safe=False)

def consultar_stock(request):
    codigos = request.GET.get("codigos")
    if not codigos:
        return JsonResponse({"error": "Debe enviar al menos un código de material."}, status=400)

    lista_codigos = [c.strip() for c in codigos.split(",") if c.strip()]
    stock_data = get_stock_sap_multiple(lista_codigos)

    return JsonResponse({"stocks": stock_data})