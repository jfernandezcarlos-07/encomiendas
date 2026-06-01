# envios/consumers.py

import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class EncomiendaConsumer(AsyncWebsocketConsumer):
    """
    Consumer del canal global de encomiendas.
    Cada empleado conectado tiene una instancia de este consumer.
    """

    # ── connect: se ejecuta cuando el cliente abre la conexión ─────
    async def connect(self):
        """
        self.scope contiene:
            - self.scope['user']          : usuario autenticado
            - self.scope['url_route']     : parámetros de la URL
            - self.scope['headers']       : cabeceras HTTP del handshake
            - self.scope['path']          : ruta WebSocket
            - self.scope['query_string']  : query string
        """
        user = self.scope.get("user")
        # 1. Verificar autenticación
        if not user or not user.is_authenticated:#if not user.is_authenticated:
            await self.close(code=4001)
            return

        # 2. Grupo global
        self.group_name = "encomiendas_global"

        # 3. Unirse al grupo
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # 4. Aceptar conexión
        await self.accept()

        # 5. Enviar estadísticas iniciales
        stats = await self.get_estadisticas()

        await self.send(
            text_data=json.dumps({
                "tipo": "conectado",
                "usuario": user.username,
                "stats": stats,
            })
        )

    async def receive(self, text_data):
        # Siempre envolver en try/except para evitar que la conexión
        # se cierre por un error no controlado
        try:
            data = json.loads(text_data)
            await self.procesar_mensaje(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'tipo': 'error',
                'codigo': 'JSON_INVALIDO',
                'mensaje': 'El mensaje no es JSON válido',
            }))

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error en consumer: {e}', exc_info=True)

            await self.send(text_data=json.dumps({
                'tipo': 'error',
                'codigo': 'ERROR_INTERNO',
                'mensaje': 'Error interno del servidor',
            }))

    async def procesar_mensaje(self, data):
        tipo = data.get('tipo')

        if tipo == 'ping':
            await self.send(text_data=json.dumps({'tipo': 'pong'}))

        elif tipo == 'solicitar_stats':
            stats = await self.get_estadisticas()
            await self.send(text_data=json.dumps({
                'tipo': 'stats',
                'stats': stats
            }))

        else:
            await self.send(text_data=json.dumps({
                'tipo': 'error',
                'mensaje': f'Tipo desconocido: {tipo}'
            }))

    # ── disconnect: cierre de conexión ──────────────────────────────
    async def disconnect(self, close_code):
        """
        1000 = cierre normal
        1001 = navegación a otra página
        1006 = pérdida de conexión
        4001 = no autorizado
        """
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # ── Evento recibido desde Channel Layer ─────────────────────────
    async def encomienda_estado_cambio(self, event):
        """
        Maneja eventos enviados mediante:

        channel_layer.group_send(
            "encomiendas_global",
            {
                "type": "encomienda_estado_cambio",
                ...
            }
        )
        """

        await self.send(
            text_data=json.dumps({
                "tipo": "estado_cambio",
                "encomienda_id": event["encomienda_id"],
                "codigo": event["codigo"],
                "estado_anterior": event["estado_anterior"],
                "estado_nuevo": event["estado_nuevo"],
                "empleado": event["empleado"],
                "timestamp": event["timestamp"],
            })
        )

    # ── Consulta ORM desde contexto async ───────────────────────────
    @database_sync_to_async
    def get_estadisticas(self):
        from django.utils import timezone
        from .models import Encomienda

        hoy = timezone.now().date()

        return {
            "activas": Encomienda.objects.activas().count(),
            "en_transito": Encomienda.objects.en_transito().count(),
            "con_retraso": Encomienda.objects.con_retraso().count(),
            "entregadas_hoy": Encomienda.objects.filter(
                estado="EN",
                fecha_entrega_real=hoy
            ).count(),
        }
    
class DashboardConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        print("[DEBUG] DashboardConsumer.connect llamado")
        user = self.scope.get("user")
        print(f"[DEBUG] Usuario: {user}, autenticado: {user.is_authenticated if user else 'None'}")
        if not user or not user.is_authenticated:#if not user.is_authenticated:
            print("[DEBUG] Rechazando conexión - usuario no autenticado")
            await self.close(code=4001)
            return
        print("[DEBUG] Usuario autenticado, aceptando conexión")
        self.group_name = "dashboard"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Enviar estadísticas iniciales al conectarse
        stats = await self.get_stats()

        await self.send(
            text_data=json.dumps({
                "tipo": "stats_iniciales",
                "stats": stats,
            })
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def dashboard_actualizar(self, event):
        """
        Recibe eventos del Channel Layer y los reenvía al navegador.
        """
        await self.send(
            text_data=json.dumps({
                "tipo": "stats_actualizado",
                "stats": event["stats"],
            })
        )

    async def estado_cambio(self, event):
        """
        Recibe eventos de cambio de estado del channel layer
        y los reenvía al navegador para actualizar el feed y mostrar toast.
        """
        await self.send(text_data=json.dumps({
            "tipo": "estado_cambio",
            "encomienda_id": event["encomienda_id"],
            "codigo": event["codigo"],
            "estado_anterior": event["estado_anterior"],
            "estado_nuevo": event["estado_nuevo"],
            "empleado": event["empleado"],
            "timestamp": event["timestamp"],
        }))
    @database_sync_to_async
    def get_stats(self):
        from django.utils import timezone
        from .models import Encomienda

        hoy = timezone.now().date()

        return {
            "activas": Encomienda.objects.activas().count(),
            "en_transito": Encomienda.objects.en_transito().count(),
            "con_retraso": Encomienda.objects.con_retraso().count(),
            "entregadas_hoy": Encomienda.objects.filter(
                estado="EN",
                fecha_entrega_real=hoy
            ).count(),
        }
    
class EncomiendaDetalleConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")  #user = self.scope["user"]

        if not user or not user.is_authenticated:#if not user.is_authenticated:
            await self.close(code=4001)
            return

        # El pk viene de la URL: ws/encomiendas/<pk>/
        self.enc_pk = self.scope["url_route"]["kwargs"]["pk"]
        self.group_name = f"encomienda_{self.enc_pk}"

        # Verificar que la encomienda existe
        existe = await self.enc_existe(self.enc_pk)

        if not existe:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Enviar estado actual al conectarse
        enc_data = await self.get_encomienda(self.enc_pk)

        await self.send(
            text_data=json.dumps({
                "tipo": "estado_actual",
                "encomienda": enc_data,
            })
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        """
        Este consumer es de solo lectura.
        No procesa mensajes enviados desde el navegador.
        """
        pass

    async def encomienda_estado_cambio(self, event):
        """
        Recibe actualizaciones del grupo:
        encomienda_<id>
        """
        await self.send(
            text_data=json.dumps({
                "tipo": "estado_cambio",
                "estado_anterior": event["estado_anterior"],
                "estado_nuevo": event["estado_nuevo"],
                "empleado": event["empleado"],
                "timestamp": event["timestamp"],
            })
        )

    @database_sync_to_async
    def enc_existe(self, pk):
        from .models import Encomienda

        return Encomienda.objects.filter(pk=pk).exists()

    @database_sync_to_async
    def get_encomienda(self, pk):
        from .models import Encomienda
        from .serializers import EncomiendaDetailSerializer

        try:
            enc = Encomienda.objects.con_relaciones().get(pk=pk)

            return dict(
                EncomiendaDetailSerializer(enc).data
            )

        except Encomienda.DoesNotExist:
            return None