#from django.shortcuts import render

# Create your views here.
# envios/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Encomienda, Empleado, HistorialEstado
from clientes.models import Cliente
from rutas.models import Ruta
from config.choices import EstadoEnvio

from django.core.paginator import Paginator 


from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin

from .models import Encomienda
from .forms import EncomiendaForm




# ── Vista mínima ──────────────────────────────────────────────
def mi_vista(request):
    # 1. Recibe el request
    # 2. Ejecuta lógica
    # 3. Devuelve una respuesta
    from django.http import HttpResponse
    return HttpResponse('Hola desde Django')


# ── Vista real: dashboard del sistema ────────────────────────
@login_required
def dashboard(request):
    """Vista principal del sistema con estadísticas"""

    hoy = timezone.now().date()

    context = {
        'total_activas': Encomienda.objects.activas().count(),
        'en_transito': Encomienda.objects.en_transito().count(),
        'con_retraso': Encomienda.objects.con_retraso().count(),
        'entregadas_hoy': Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO,
            fecha_entrega_real=hoy
        ).count(),
        'ultimas': Encomienda.objects.con_relaciones()[:5],
    }

    return render(request, 'envios/dashboard.html', context)

@login_required
def encomienda_crear(request):
    """
    GET → muestra el formulario vacío
    POST → valida, guarda y redirige al detalle
    """

    #from .forms import EncomiendaForm

    if request.method == 'POST':
        form = EncomiendaForm(request.POST)

        if form.is_valid():
            enc = form.save(commit=False)  # no guarda aún en BD

            enc.empleado_registro = Empleado.objects.get(
                email=request.user.email
            )

            enc.save()  # ahora sí guarda

            messages.success(
                request,
                f'Encomienda {enc.codigo} registrada correctamente.'
            )

            # Redirige para evitar reenvío del formulario al recargar
            return redirect('encomienda_detalle', pk=enc.pk)

        # Si el form tiene errores, vuelve a mostrar con los errores
    else:
        form = EncomiendaForm()  # GET: form vacío

    return render(request, 'envios/form.html', {
        'form': form,
        'titulo': 'Nueva Encomienda',
    })

@login_required
def encomienda_lista(request):
    qs = Encomienda.objects.con_relaciones()

    # ── Filtros opcionales ────────────────────────────────────────
    estado = request.GET.get('estado', '')
    q = request.GET.get('q', '')

    if estado:
        qs = qs.filter(estado=estado)

    if q:
        from django.db.models import Q

        qs = qs.filter(
            Q(codigo__icontains=q) |
            Q(remitente__apellidos__icontains=q) |
            Q(destinatario__apellidos__icontains=q)
        )

    # ── Paginación ────────────────────────────────────────────────
    paginator = Paginator(qs, 15)  # 15 por página
    page_number = request.GET.get('page', 1)
    encomiendas = paginator.get_page(page_number)

    # El objeto Page tiene estos atributos útiles:
    # encomiendas.number                     → número de página actual
    # encomiendas.paginator.count           → total de registros
    # encomiendas.paginator.num_pages       → total de páginas
    # encomiendas.has_previous()            → True/False
    # encomiendas.has_next()                → True/False
    # encomiendas.previous_page_number()    → número página anterior
    # encomiendas.next_page_number()        → número página siguiente

    return render(
        request,
        'envios/lista.html',
        {
            'encomiendas': encomiendas,
            'estados': EstadoEnvio.choices,
            'estado_activo': estado,
            'q': q,
        }
    )


# ── ListView: lista paginada ──────────────────────────────────────
class EncomiendaListView(LoginRequiredMixin, ListView):
    model = Encomienda
    template_name = 'envios/lista.html'
    context_object_name = 'encomiendas'
    paginate_by = 15
    ordering = ['-fecha_registro']

    def get_queryset(self):
        qs = Encomienda.objects.con_relaciones()

        estado = self.request.GET.get('estado')

        if estado:
            qs = qs.filter(estado=estado)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estados'] = EstadoEnvio.choices
        return ctx


# ── DetailView: detalle de un registro ───────────────────────────
class EncomiendaDetailView(LoginRequiredMixin, DetailView):
    model = Encomienda
    template_name = 'envios/detalle.html'
    context_object_name = 'encomienda'

    def get_queryset(self):
        return Encomienda.objects.con_relaciones()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['historial'] = self.object.historial.select_related('empleado')
        return ctx


# ── CreateView: formulario de creación ───────────────────────────
class EncomiendaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Encomienda
    form_class = EncomiendaForm
    template_name = 'envios/form.html'

    success_message = 'Encomienda %(codigo)s creada correctamente.'

    def get_success_url(self):
        return reverse_lazy(
            'encomienda_detalle',
            kwargs={'pk': self.object.pk}
        )

    def form_valid(self, form):
        # Asignar el empleado antes de guardar
        form.instance.empleado_registro = self.request.user.empleado
        return super().form_valid(form)


# ── UpdateView: formulario de edición ────────────────────────────
class EncomiendaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Encomienda
    form_class = EncomiendaForm
    template_name = 'envios/form.html'

    success_message = 'Encomienda actualizada correctamente.'

    def get_success_url(self):
        return reverse_lazy(
            'encomienda_detalle',
            kwargs={'pk': self.object.pk}
        )