# envios/api_views.py — Generic Views

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Encomienda
from clientes.models import Cliente
from rutas.models import Ruta

from .serializers import (
    EncomiendaSerializer,
    EncomiendaDetailSerializer,
    ClienteSerializer,
    RutaSerializer,
)
from api.pagination import ClientePagination 

from drf_spectacular.utils import extend_schema #pagina 62

# ── Encomiendas: listar + crear ──────────────────────────────────

class EncomiendaListCreateView(generics.ListCreateAPIView):

    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        #serializer.save(empleado_registro=self.request.user.empleado)
        empleado = Empleado.objects.get(email=self.request.user.email)
        serializer.save(empleado_registro=empleado)


# ── Encomiendas: detalle + actualizar + eliminar ─────────────────

class EncomiendaDetailView(generics.RetrieveUpdateDestroyAPIView):

    queryset = Encomienda.objects.con_relaciones()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Usar serializer diferente según el método
        """

        if self.request.method == 'GET':
            return EncomiendaDetailSerializer  # con objetos anidados

        return EncomiendaSerializer  # solo IDs para escritura

#pagina62
@extend_schema(
    summary="Listar clientes activos",
    description=(
        "Devuelve todos los clientes con estado Activo, "
        "paginados de 20 en 20."
    ),
    tags=["Clientes"],
)

# ── Clientes: solo lectura ───────────────────────────────────────

class ClienteListView(generics.ListAPIView):

    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class= ClientePagination  # 20 por pagina 
    def get_queryset(self):

        return Cliente.objects.activos()

#pagina 63
@extend_schema(
    summary="Listar rutas activas",
    description=(
        "Devuelve todas las rutas con estado Activo. "
        "Sin paginación."
    ),
    tags=["Rutas"],
)

# ── Rutas: solo lectura ──────────────────────────────────────────

class RutaListView(generics.ListAPIView):

    serializer_class = RutaSerializer
    permission_classes = [IsAuthenticated]
    
    # Las rutas son pocas: no paginamos (None deshabilita la paginacion)
    pagination_class= None 
    
    def get_queryset(self):

        return Ruta.objects.activas()