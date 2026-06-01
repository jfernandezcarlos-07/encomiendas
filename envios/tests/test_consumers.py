# envios/tests/test_consumers.py

import json
import pytest
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import RefreshToken
from config.asgi import application
from .factories import UserFactory


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestEncomiendaConsumer:

    async def test_conexion_sin_autenticacion(self):
        """Sin token: el servidor debe rechazar con código 4001"""
        communicator = WebsocketCommunicator(application, "/ws/encomiendas/")
        connected, code = await communicator.connect()
        assert not connected
        assert code == 4001
        await communicator.disconnect()

    async def test_conexion_autenticada(self):
        """Con token válido: el servidor acepta y envía estadísticas iniciales"""
        user = await database_sync_to_async(UserFactory)()
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)

        communicator = WebsocketCommunicator(
            application, f"/ws/encomiendas/?token={token}"
        )
        connected, _ = await communicator.connect()
        assert connected

        response = await communicator.receive_json_from(timeout=3)
        assert response["tipo"] == "conectado"
        assert "stats" in response
        assert "activas" in response["stats"]

        await communicator.disconnect()

    async def test_ping_pong(self):
        """El consumer debe responder 'pong' al recibir 'ping'"""
        user = await database_sync_to_async(UserFactory)()
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)

        communicator = WebsocketCommunicator(
            application, f"/ws/encomiendas/?token={token}"
        )
        await communicator.connect()
        await communicator.receive_json_from(timeout=2)  # bienvenida
        await communicator.send_json_to({"tipo": "ping"})
        response = await communicator.receive_json_from(timeout=2)
        assert response["tipo"] == "pong"
        await communicator.disconnect()

    async def test_notificacion_via_channel_layer(self):
        """El consumer debe recibir eventos enviados al grupo del channel layer"""
        user = await database_sync_to_async(UserFactory)()
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)

        communicator = WebsocketCommunicator(
            application, f"/ws/encomiendas/?token={token}"
        )
        await communicator.connect()
        await communicator.receive_json_from(timeout=2)  # bienvenida

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "encomiendas_global",
            {
                "type": "encomienda_estado_cambio",
                "encomienda_id": 1,
                "codigo": "ENC-2026-001",
                "estado_anterior": "PE",
                "estado_nuevo": "TR",
                "empleado": "Mendoza Cruz, Luis",
                "timestamp": "2026-05-14T10:00:00Z",
            }
        )

        response = await communicator.receive_json_from(timeout=3)
        assert response["tipo"] == "estado_cambio"
        assert response["codigo"] == "ENC-2026-001"
        assert response["estado_nuevo"] == "TR"

        await communicator.disconnect()