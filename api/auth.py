
#api/auth.py
# JWT personalizado con datos del empleado

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView
)

from envios.models import Empleado

from api.throttles import LoginRateThrottle#pagina 99

class EncomiendaTokenSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):

        token = super().get_token(user)

        # Agregar datos del empleado al payload del JWT
        token['username'] = user.username
        token['email'] = user.email

        try:
            #emp = user.empleado
            emp = Empleado.objects.get(email=user.email)

            token['empleado_id'] = emp.id
            token['empleado_cod'] = emp.codigo
            token['cargo'] = emp.cargo

        except Exception:
            pass

        return token


class EncomiendaTokenView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]#pagina99
    serializer_class = EncomiendaTokenSerializer