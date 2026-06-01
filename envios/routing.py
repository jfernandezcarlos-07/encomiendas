# envios/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ── Consumer general: todos los empleados conectados ───────── 
    # URL: ws://localhost:8000/ws/encomiendas/ 
    re_path(r'^ws/encomiendas/$', consumers.EncomiendaConsumer.as_asgi(),name="ws-encomiendas",),
     # ── Consumer de detalle: una encomienda específica ───────────
    # URL: ws://localhost:8000/ws/encomiendas/42/
    # El pk se extrae mediante (?P<pk>\d+)
    re_path(r"^ws/encomiendas/(?P<pk>\d+)/$",consumers.EncomiendaDetalleConsumer.as_asgi(),name="ws-encomienda-detalle",),
     # ── Consumer del dashboard: estadísticas en tiempo real ──────
    # URL: ws://localhost:8000/ws/dashboard/
    re_path(r"^ws/dashboard/$",consumers.DashboardConsumer.as_asgi(),name="ws-dashboard",),
]

# Nota:
# re_path permite capturar parámetros mediante expresiones regulares.
#
# Acceso desde el consumer:
# self.scope["url_route"]["kwargs"]["pk"]
#
# Ejemplo:
# ws://localhost:8000/ws/encomiendas/42/
# → self.scope["url_route"]["kwargs"]["pk"] == "42"