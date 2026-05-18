# pos_project/urls.py
# envios/viewsets.py

# MODIFICAR: agregar los imports y atributos de paginacion

from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination

# Importar los paginadores del proyecto
from api.pagination import (
    EncomiendaPagination,
    HistorialPagination,
)

from .models import Encomienda, Empleado

from .serializers import (
    EncomiendaSerializer,
    EncomiendaListSerializer,# se comento
    EncomiendaDetailSerializer,
    EncomiendaV2Serializer,#nuevo pagna 72
    HistorialEstadoSerializer,
)

from config.choices import EstadoEnvio

#se agrego de la pagina 42
from rest_framework.filters import (
    SearchFilter,
    OrderingFilter
)

from django_filters.rest_framework import DjangoFilterBackend

from api.filters import EncomiendaFilter


from django.core.exceptions import ObjectDoesNotExist # se agrega por motivo de error pagina 57  58
from rest_framework import serializers as drf_serializers # se agrega por motivo de error pagina 57  58

#pagina 58
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes

#pagina 99
from api.throttles import EmpleadoRateThrottle, CambioEstadoThrottle
#
from api.exceptions import EstadoInvalidoError, EncomiendaYaEntregadaError #pagina 102
#pagina 141
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from config.settings import CACHE_TTL
from rutas.models import Ruta
from .serializers import RutaSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Listar encomiendas",
        description=(
            "Devuelve la lista paginada de encomiendas. "
            "Soporta filtros por estado, búsqueda y ordenamiento."
        ),
        tags=["Encomiendas"],
    ),
    create=extend_schema(
        summary="Crear encomienda",
        description="Registra una nueva encomienda en el sistema.",
        tags=["Encomiendas"],
    ),
    retrieve=extend_schema(
        summary="Detalle de encomienda",
        description=(
            "Devuelve los datos completos de una encomienda con "
            "remitente, destinatario, ruta e historial de estados."
        ),
        tags=["Encomiendas"],
    ),
    update=extend_schema(
        summary="Actualizar encomienda",
        tags=["Encomiendas"],
    ),
    partial_update=extend_schema(
        summary="Actualizar parcial",
        tags=["Encomiendas"],
    ),
    destroy=extend_schema(
        summary="Eliminar encomienda",
        tags=["Encomiendas"],
    ),
)

#



class EncomiendaViewSet(viewsets.ModelViewSet):

    queryset = Encomienda.objects.con_relaciones()

    serializer_class = EncomiendaSerializer

    permission_classes = [IsAuthenticated]

    # <- paginador del proyecto
    pagination_class = EncomiendaPagination

    #se agrego de la pagina 42
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter
    ]

    filterset_class = EncomiendaFilter

    throttle_classes = [EmpleadoRateThrottle] #pagina 99

    search_fields = [
        'codigo',
        'remitente__apellidos',
        'destinatario__apellidos',
        'descripcion',
    ]

    ordering_fields = [
        'fecha_registro',
        'peso_kg',
        'costo_envio'
    ]

    ordering = ['-fecha_registro']  # orden por defecto

    #pagina 99
    def get_throttles(self):
        """Throttle diferente para la acción cambiar_estado"""
        if self.action == 'cambiar_estado':
            return [CambioEstadoThrottle()]
        return super().get_throttles()
    #

    def get_serializer_class(self):
        """
        Elegir el serializer según la versión Y la acción.

        v1 list     -> EncomiendaListSerializer   (ligero)
        v1 retrieve -> EncomiendaDetailSerializer (con anidados)
        v1 write    -> EncomiendaSerializer       (estándar)

        v2 cualquier acción -> EncomiendaV2Serializer
        """
        version = getattr(self.request, 'version', 'v1')
        # v2: un solo serializer para todo
        if version == 'v2':
            return EncomiendaV2Serializer

        # v1: serializer según la acción
        if self.action == 'list':#se comento 
            return EncomiendaListSerializer #se comento

        if self.action == 'retrieve':
            return EncomiendaDetailSerializer

        return EncomiendaSerializer
        #if self.action == 'retrieve':
            #return EncomiendaDetailSerializer

        #return EncomiendaSerializer
    def get_queryset(self):
        """
        v1 y v2 usan el mismo queryset optimizado.
        Si en el futuro v2 necesita datos extra, se agrega aquí.
        """

        qs = Encomienda.objects.con_relaciones()

        estado = self.request.query_params.get('estado')

        if estado:
            qs = qs.filter(estado=estado)

        # Optimización para el listado: solo los campos necesarios
        if self.action == 'list':
            qs = qs.only(
                # Campos propios de encomienda
                'id', 'codigo', 'estado',
                'peso_kg', 'costo_envio',
                'fecha_registro', 'fecha_entrega_est',
                # Campos del remitente (prefijo del related)
                'remitente__nombres', 'remitente__apellidos',
                # Campos del destinatario
                'destinatario__nombres', 'destinatario__apellidos',
                # Campo de la ruta
                'ruta__destino',
                'empleado_registro',# se agregp para hacer el paso 11 de la pagina 136
            )
        return qs

    def list(self, request, *args, **kwargs):
        """Agregar cabecera X-API-Version en la respuesta"""

        response = super().list(request, *args, **kwargs)

        response['X-API-Version'] = getattr(request, 'version', 'v1')

        return response

    def retrieve(self, request, *args, **kwargs):
        """Agregar cabecera X-API-Version en el detalle"""

        response = super().retrieve(request, *args, **kwargs)

        response['X-API-Version'] = getattr(request, 'version', 'v1')

        return response

    def perform_create(self, serializer):

        #serializer.save(empleado_registro=self.request.user.empleado)
        try:
            empleado = Empleado.objects.get(email=self.request.user.email)
        except ObjectDoesNotExist:
            raise drf_serializers.ValidationError(
                "No existe un empleado asociado a tu usuario. Contacta al administrador."
            )
        serializer.save(empleado_registro=empleado)
    def perform_update(self, serializer):
        """Invalidar caché cuando se actualiza una encomienda"""
        super().perform_update(serializer)
        # Borrar el caché de estadísticas de este empleado
        cache_key = f'estadisticas_empleado_{self.request.user.id}'
        cache.delete(cache_key)

    #pagina 60
    @extend_schema(
        summary="Cambiar estado de encomienda",
        description="""
            Cambia el estado de una encomienda y registra el cambio
            automáticamente en el historial de estados.

            Estados disponibles:
            - PE: Pendiente
            - TR: En tránsito
            - DE: En destino
            - EN: Entregado
            - DV: Devuelto
        """,
        request=OpenApiTypes.OBJECT,
        responses={
            200: EncomiendaSerializer,
            400: OpenApiResponse(
                description="Estado inválido o ya en ese estado"
            ),
        },
        examples=[
            OpenApiExample(
                "Pasar a En tránsito",
                value={
                    "estado": "TR",
                    "observacion": "Recogido en agencia Lima",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Marcar como Entregado",
                value={
                    "estado": "EN",
                    "observacion": "Entregado al destinatario",
                },
                request_only=True,
            ),
        ],
        tags=["Encomiendas"],
    )

    #
    # ── Acciones ya implementadas en tema 6.1 ────────────────────

    @action(detail=True, methods=['post'], url_path='cambiar_estado')
    def cambiar_estado(self, request, pk=None, **kwargs):   # añade **kwargs para los test

        enc = self.get_object()

        nuevo_estado = request.data.get('estado')

        observacion = request.data.get('observacion', '')

        #se agrego de la pagina 102
        if enc.esta_entregada:
            raise EncomiendaYaEntregadaError()
        #
        if not nuevo_estado:

            return Response({'error': 'El campo estado es requerido.'},status=400)

        try:

            empleado = Empleado.objects.get(email=request.user.email)

            enc.cambiar_estado(nuevo_estado,empleado,observacion)

            # Invalidar caché de estadísticas al cambiar un estado
            cache.delete_many([
                f'estadisticas_empleado_{request.user.id}',
                f'encomienda_detalle_{pk}',
            ])
            
            return Response(
                EncomiendaSerializer(enc).data
            )

        except ValueError as e:

            #return Response({'error': str(e)},status=400) #pagina 102
            raise EstadoInvalidoError(detail=str(e))

    #pagina60 o 61
    @extend_schema(
        summary="Encomiendas con retraso",
        description=(
            "Lista todas las encomiendas activas cuya fecha "
            "estimada de entrega ya pasó."
        ),
        tags=["Encomiendas"],
        responses={
            200: EncomiendaSerializer(many=True),
        },
    )
    #
    @action(detail=False, methods=['get'], url_path='con_retraso')
    def con_retraso(self, request,**kwargs):# añade **kwargs para los test

        qs = (
            Encomienda.objects
            .con_retraso()
            .con_relaciones()
        )

        return Response(
            self.get_serializer(qs, many=True).data
        )

    #pagina60 o 61
    @extend_schema(
        summary="Encomiendas pendientes",
        description="Lista todas las encomiendas en estado Pendiente.",
        tags=["Encomiendas"],
    )
    #
    @action(detail=False, methods=['get'])
    def pendientes(self, request,**kwargs):# añade **kwargs para los test

        qs = (
            Encomienda.objects
            .pendientes()
            .con_relaciones()
        )

        return Response(
            self.get_serializer(qs, many=True).data
        )
    
    #pagina 61 o 62
    @extend_schema(
        summary="Historial de estados",
        description=(
            "Devuelve el historial de cambios de estado de una "
            "encomienda, paginado con limit/offset."
        ),
        parameters=[
            OpenApiParameter(
                "limit",
                type=int,
                description="Número de resultados",
                default=10,
            ),
            OpenApiParameter(
                "offset",
                type=int,
                description="Posición de inicio",
                default=0,
            ),
        ],
        tags=["Encomiendas"],
    )

    #

    # ── NUEVA accion: historial con paginacion propia ─────────────

    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None,**kwargs):
        """
        GET /api/v1/encomiendas/{pk}/historial/
        GET /api/v1/encomiendas/{pk}/historial/?limit=5&offset=10

        Devuelve el historial de cambios de estado paginado.
        """

        enc = self.get_object()

        qs = (
            enc.historial
            .select_related('empleado')
            .order_by('-fecha_cambio')
        )

        # Usar el paginador especifico para historial (LimitOffset)

        paginator = HistorialPagination()

        page = paginator.paginate_queryset(
            qs,
            request
        )

        if page is not None:

            #serializer = HistorialEstadoSerializer(page,many=True)

            return paginator.get_paginated_response(
                #serializer.data
                HistorialEstadoSerializer(page, many=True).data
            )

        #serializer = HistorialEstadoSerializer( qs,many=True)

        return Response(serializer.data)

    #pagina62 
    @extend_schema(
        summary="Estadísticas globales",
        description=(
            "Contadores del sistema: activas, en tránsito, "
            "con retraso y entregadas hoy."
        ),
        tags=["Encomiendas"],
        responses={
            200: OpenApiResponse(
                description="Objeto con contadores"
            ),
        },
    )
    #

    # ── NUEVA accion: estadisticas
    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request, **kwargs):
        """Estadísticas globales — se calculan cada 15 minutos (CACHE_TTL)"""
        cache_key = f'estadisticas_empleado_{request.user.id}'
        data = cache.get(cache_key)

        if data is None:
            # No está en caché: calcular y guardar
            from django.utils import timezone
            hoy = timezone.now().date()
            data = {
                'total_activas': Encomienda.objects.activas().count(),
                'en_transito': Encomienda.objects.en_transito().count(),
                'con_retraso': Encomienda.objects.con_retraso().count(),
                'entregadas_hoy': Encomienda.objects.filter(
                    estado='EN',
                    fecha_entrega_real=hoy
                ).count(),
            }
            cache.set(cache_key, data, CACHE_TTL)   # guardar por CACHE_TTL segundos
        return Response(data)
    
    #pagina 
    @extend_schema(
        summary='Crear multiples encomiendas',
        description='Crea varias encomiendas en una sola peticion. Body: lista de objetos.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request,**kwargs):
        """
        POST /api/v1/encomiendas/bulk_create/

        Body: [{enc1}, {enc2}, {enc3}]

        Crea todas las encomiendas con una sola query SQL.
        """

        # many=True activa EncomiendaBulkSerializer automaticamente
        serializer = self.get_serializer(
            data=request.data,
            many=True,
            context={'request': request} # esto se agrego
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Asignar el empleado a todas las encomiendas
        empleado = Empleado.objects.get(email=request.user.email)

        #encomiendas = serializer.save(empleado_registro=empleado)
        encomiendas = serializer.save()

        return Response(
            self.get_serializer(encomiendas, many=True).data,
            status=status.HTTP_201_CREATED
        )


    # ── Bulk estado: cambiar estado a multiples encomiendas ───────────

    @extend_schema(
        summary='Cambiar estado a multiples encomiendas',
        description='Cambia el estado de varias encomiendas. Reporta cuales tuvieron errores.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['patch'], url_path='bulk_estado')
    def bulk_estado(self, request, **kwargs):
        """
        PATCH /api/v1/encomiendas/bulk_estado/

        Body: {"ids": [1, 2, 3], "estado": "TR", "observacion": "..."}

        Procesa cada encomienda y reporta cuales tuvieron errores.
        """

        ids = request.data.get('ids', [])
        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')

        # Validar que llegaron los campos requeridos
        if not ids:
            return Response(
                {'error': 'El campo ids es requerido y no puede estar vacio.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not nuevo_estado:
            return Response(
                {'error': 'El campo estado es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            empleado = Empleado.objects.get(email=request.user.email)
        except Empleado.DoesNotExist:
            return Response(
                {'error': 'El usuario no tiene un empleado asociado.'},
                status=status.HTTP_403_FORBIDDEN
            )

        encomiendas = Encomienda.objects.filter(id__in=ids)

        actualizadas = []
        errores = []

        for enc in encomiendas:
            try:
                enc.cambiar_estado(nuevo_estado, empleado, observacion)
                actualizadas.append(enc.id)
            except ValueError as e:
                errores.append({'id': enc.id, 'error': str(e)})

        # Ids que no existen
        ids_procesados = list(encomiendas.values_list('id', flat=True))
        no_encontrados = [i for i in ids if i not in ids_procesados]

        return Response({
            'actualizadas': actualizadas,
            'errores': errores,
            'no_encontrados': no_encontrados,
            'total': len(actualizadas),
        })
    
class RutaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Las rutas cambian poco — cachear el listado 15 minutos
    """

    queryset = Ruta.objects.activas()
    serializer_class = RutaSerializer

    @method_decorator(cache_page(CACHE_TTL))
    @method_decorator(vary_on_headers('Authorization'))
    def list(self, request, *args, **kwargs):
        """
        Cache por usuario (vary_on_headers diferencia el token)
        """
        return super().list(request, *args, **kwargs)