# conftest.py (raíz del proyecto)

import pytest

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    """Cliente de API sin autenticación"""
    return APIClient()


@pytest.fixture
def user(db):
    """Usuario de prueba"""
    return User.objects.create_user(
        username='test_empleado',
        email='empleado@encomiendas.pe',
        password='test1234',
    )


@pytest.fixture
def auth_client(api_client, user):
    """Cliente de API con JWT válido"""

    refresh = RefreshToken.for_user(user)

    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
    )

    return api_client

@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Permite acceso a la base de datos en todas las pruebas sin necesidad de marcador"""
    pass