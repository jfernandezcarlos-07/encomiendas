"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
#config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth import views as auth_views
from envios import views_auth

admin.site.site_header  = 'Sistema de Gestión de Encomiendas' 
admin.site.site_title   = 'Encomiendas Admin' 
admin.site.index_title  = 'Panel de Administración'

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)#se agrego de la pagina 45
from api.auth import EncomiendaTokenView  #se agrego de la pagina 46

from drf_spectacular.views import (
    SpectacularAPIView,       # endpoint schema OpenAPI
    SpectacularSwaggerView,   # Swagger UI interactivo
    SpectacularRedocView,     # ReDoc documentación limpia
)#pagina 54

from django.conf import settings #pagina 124
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('envios.urls')),
    #path('accounts/login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    #path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('login/',views_auth.login_view,name='login'),
    path('logout/', views_auth.logout_view,name='logout'),
    path('perfil/',views_auth.perfil_view,name='perfil'),

    #se agrego de la pagina 45
    path('api/v1/auth/token/',TokenObtainPairView.as_view(),name='token_obtain'),

    path('api/v1/auth/token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),

    path('api/v1/auth/token/blacklist/',TokenBlacklistView.as_view(),name='token_blacklist'),
    path('api/v1/auth/token/', EncomiendaTokenView.as_view()),
    #termina aqui

    #pagina 54, se comento por la pagina 69
    # Schema OpenAPI (JSON/YAML)
    #path('api/schema/',SpectacularAPIView.as_view(),name='schema'),

    # Swagger UI
    #path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'),name='swagger'),

    # ReDoc UI
    #path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'),name='redoc'),
    #termna aqui

    #path('accounts/perfil/', views_auth.perfil_view, name='perfil'),
    #path('accounts/', include('django.contrib.auth.urls')), # login/logout/incluidos

    # API REST
    #path('api/v1/', include('api.urls'))

    # API REST con versionado dinámico se agrego del apagina 69
    # <version> captura 'v1' o 'v2' de la URL
    path('api/<version>/', include('api.urls')),
    #path('api/', include('api.urls')),

    # Auth JWT (no tiene versionado, es igual para todos)
    path('api/v1/auth/token/', TokenObtainPairView.as_view(),),

    path('api/v1/auth/token/refresh/',TokenRefreshView.as_view(),),

    # Documentación
    path('api/schema/', SpectacularAPIView.as_view(), name='schema' ),

    path('api/docs/',SpectacularSwaggerView.as_view(url_name='schema'),name='swagger'),

    path('api/redoc/',SpectacularRedocView.as_view(url_name='schema'),name='redoc'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    from silk import urls as silk_urls
    urlpatterns += [path('silk/', include('silk.urls', namespace='silk')),]

    urlpatterns += static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)