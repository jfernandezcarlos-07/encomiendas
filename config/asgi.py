"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import sys 
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter 
from channels.auth import AuthMiddlewareStack 
from channels.security.websocket import AllowedHostsOriginValidator
from channels_middleware import JWTAuthMiddlewareStack 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Importar DESPUES de django.setup() para evitar errores de inicializacion 
from envios.routing import websocket_urlpatterns



#application = get_asgi_application()
application = ProtocolTypeRouter({

    # Peticiones HTTP normales
    "http": get_asgi_application(),

    # Conexiones WebSocket
    "websocket": AllowedHostsOriginValidator(
        
        # Lee la sesión/cookies de Django y
        # llena self.scope["user"]
        AuthMiddlewareStack(URLRouter(websocket_urlpatterns))

        # Reemplazar AuthMiddlewareStack por JWTAuthMiddlewareStack 
        #JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)) 
        
    ),
})

# AllowedHostsOriginValidator: 
# Rechaza conexiones WebSocket de origenes no listados en ALLOWED_HOSTS. 
# Protege contra ataques CSRF en WebSockets. 
# AuthMiddlewareStack: 
# Combina SessionMiddleware + CookieMiddleware. 
# Lee la cookie de sesion de Django y popula self.scope['user']. 
# Si el usuario no esta logueado: self.scope['user'] = AnonymousUser

 