# api/urls.py  

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

#from django.urls import path

from envios import api_views
from envios.viewsets import EncomiendaViewSet

router = DefaultRouter()

# Aquí se registrarán los ViewSets en los siguientes pasos
router.register('encomiendas', EncomiendaViewSet, basename='encomienda')

urlpatterns = [
    # Endpoints de autenticación JWT
    path('auth/token/',TokenObtainPairView.as_view(),name='token_obtain'),
    path('auth/token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    # Documentación interactiva
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/',SpectacularSwaggerView.as_view(),name='swagger'),

    # URLs del router (ViewSets)
    path('', include(router.urls)),
    path('clientes/',api_views.ClienteListView.as_view() ),
    path('rutas/',api_views.RutaListView.as_view()),
    #se borraron en la pagina 30
    #path('encomiendas/',api_views.EncomiendaListCreateView.as_view()),
    #path('encomiendas/<int:pk>/',api_views.EncomiendaDetailView.as_view()),
]