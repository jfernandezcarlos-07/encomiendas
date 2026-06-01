# envios/async_services.py
# Corrutinas del proyecto

import asyncio

import httpx
from django.utils import timezone

from .models import Encomienda


async def verificar_estado_transportista(codigo: str) -> dict:
    """
    Corrutina que consulta la API del transportista.
    Puede pausarse mientras espera la respuesta HTTP.
    """
    url = f"https://api.transportista.pe/v1/track/{codigo}"

    try:
        async with httpx.AsyncClient() as client:
            # await: se pausa aquí. El event loop atiende otros requests.
            response = await client.get(url, timeout=5.0)

            data = response.json()

            return {
                "codigo": codigo,
                "encontrado": True,
                "estado_ext": data.get("status"),
                "ubicacion": data.get("location"),
                "timestamp": timezone.now().isoformat(),
            }

    except httpx.TimeoutException:
        return {
            "codigo": codigo,
            "encontrado": False,
            "error": "timeout",
        }

    except httpx.ConnectError:
        return {
            "codigo": codigo,
            "encontrado": False,
            "error": "conexion",
        }


async def actualizar_estados_en_transito() -> list:
    """
    Actualiza el estado de todas las encomiendas en tránsito
    consultando la API del transportista en paralelo.
    """

    # 1. Obtener encomiendas en tránsito (query async)
    encomiendas = await Encomienda.objects.en_transito().alist()

    if not encomiendas:
        return []

    # 2. Consultar el transportista para TODAS en paralelo
    #    Sin async: 50 enc * 1s = 50 segundos
    #    Con async: ~1 segundo (todas en paralelo)
    resultados = await asyncio.gather(
        *[
            verificar_estado_transportista(enc.codigo)
            for enc in encomiendas
        ],
        return_exceptions=True,
    )

    # 3. Procesar los resultados
    actualizadas = []

    for enc, resultado in zip(encomiendas, resultados):

        if isinstance(resultado, Exception):
            continue  # ignorar errores individuales

        if (
            resultado.get("encontrado")
            and resultado.get("estado_ext") == "DELIVERED"
        ):
            # La encomienda fue entregada según el transportista
            enc.estado = "EN"
            enc.fecha_entrega_real = timezone.now().date()

            await enc.asave()  # guardar async

            actualizadas.append(enc.codigo)

    return actualizadas

async def verificar_una(
    session: httpx.AsyncClient,
    codigo: str,
) -> dict:
    """
    Verifica UNA encomienda.
    Se ejecuta en paralelo con las demás.
    """

    try:
        response = await session.get(
            f"https://api.transportista.pe/track/{codigo}",
            timeout=5.0,
        )

        return {
            "codigo": codigo,
            "ok": True,
            "data": response.json(),
        }

    except httpx.TimeoutException:
        return {
            "codigo": codigo,
            "ok": False,
            "error": "timeout",
        }

    except Exception as e:
        return {
            "codigo": codigo,
            "ok": False,
            "error": str(e),
        }


async def verificar_lote_completo() -> dict:
    """
    Verifica TODAS las encomiendas en tránsito en paralelo.

    SINCRONO:
        50 encomiendas * 1s por consulta = 50 SEGUNDOS

    ASINCRONO:
        todas en paralelo = ~1 SEGUNDO
    """

    # 1. Obtener encomiendas en tránsito de la BD
    encomiendas = await Encomienda.objects.en_transito().alist()

    if not encomiendas:
        return {
            "verificadas": 0,
            "resultados": [],
        }

    print(
        f"Verificando {len(encomiendas)} encomiendas en paralelo..."
    )

    # 2. Abrir una sesión HTTP compartida para todas las consultas
    async with httpx.AsyncClient() as session:

        # 3. Lanzar TODAS las consultas a la vez
        tareas = [
            verificar_una(session, enc.codigo)
            for enc in encomiendas
        ]

        # gather:
        # las ejecuta en paralelo y espera a que todas terminen
        resultados = await asyncio.gather(
            *tareas,
            return_exceptions=True,
        )

    # 4. Separar exitosas de fallidas
    exitosas = [
        r for r in resultados
        if isinstance(r, dict) and r["ok"]
    ]

    fallidas = [
        r for r in resultados
        if isinstance(r, dict) and not r["ok"]
    ]

    errores = [
        r for r in resultados
        if isinstance(r, Exception)
    ]

    return {
        "verificadas": len(encomiendas),
        "exitosas": len(exitosas),
        "fallidas": len(fallidas),
        "errores": len(errores),
        "resultados": resultados,
    }


async def enviar_notificacion_email(
    enc,
    nuevo_estado: str,
):
    """
    Envía un email de notificación.
    Puede tardar 500ms.
    """

    # Simula el envío del email
    await asyncio.sleep(0.5)

    print(
        f"Email enviado: {enc.codigo} -> {nuevo_estado}"
    )


async def registrar_en_log_externo(
    enc,
    estado: str,
):
    """
    Registra el cambio en un sistema de logs externo.
    """

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://logs.empresa.pe/api/encomiendas",
            json={
                "codigo": enc.codigo,
                "estado": estado,
            },
            timeout=3.0,
        )


async def cambiar_estado_vista(
    request,
    pk: int,
):
    """
    Vista async que cambia el estado y lanza las notificaciones
    en background sin hacer esperar al cliente.
    """

    enc = await Encomienda.objects.aget(pk=pk)

    nuevo_estado = request.data.get("estado")

    # Paso 1: cambiar el estado
    # (CRÍTICO - el cliente espera esto)
    enc.estado = nuevo_estado

    await enc.asave()

    # Paso 2: lanzar notificaciones en BACKGROUND
    # (no críticas)
    # El cliente recibe la respuesta ANTES
    # de que los emails terminen

    asyncio.create_task(
        enviar_notificacion_email(
            enc,
            nuevo_estado,
        )
    )

    asyncio.create_task(
        registrar_en_log_externo(
            enc,
            nuevo_estado,
        )
    )

    # Esta respuesta llega al cliente inmediatamente
    # Los emails y logs se envían en segundo plano
    return {
        "ok": True,
        "estado": nuevo_estado,
    }




async def verificar_con_timeout(enc) -> dict:
    """
    Verifica una encomienda en la API del transportista.

    Si no responde en 3 segundos, devuelve
    el último estado conocido.
    """

    try:
        # Máximo 3 segundos para la API externa
        resultado = await asyncio.wait_for(
            verificar_api_externa(enc.codigo),
            timeout=3.0,
        )

        return resultado

    except asyncio.TimeoutError:
        # La API tardó más de 3s
        # -> devolver datos de nuestra BD
        return {
            "codigo": enc.codigo,
            "estado": enc.get_estado_display(),
            "fuente": "cache_local",
            "advertencia": (
                "API del transportista no disponible"
            ),
        }


async def verificar_lote_con_timeout(
    codigos: list,
) -> list:
    """
    Verifica múltiples encomiendas,
    cada una con su propio timeout.

    Las que fallen (timeout, error de red)
    devuelven datos del cache.
    """

    encomiendas = await Encomienda.objects.filter(
        codigo__in=codigos
    ).alist()

    resultados = await asyncio.gather(
        *[
            verificar_con_timeout(enc)
            for enc in encomiendas
        ],
        return_exceptions=True,
    )

    return [
        (
            r
            if not isinstance(r, Exception)
            else {"error": str(r)}
        )
        for r in resultados
    ]


#son opcionales pagina 16
async def procesar_encomiendas_en_transito():
    """
    Itera todas las encomiendas en tránsito y actualiza
    las retrasadas.

    async for no bloquea:
    cada iteración cede control al event loop.
    """

    encomiendas_retrasadas = []

    async for enc in (
        Encomienda.objects
        .en_transito()
        .select_related("ruta")
    ):
        if enc.tiene_retraso:  # @property del modelo
            encomiendas_retrasadas.append(enc)

    # Notificar todas las retrasadas en paralelo
    if encomiendas_retrasadas:
        await asyncio.gather(
            *[
                notificar_retraso(enc)
                for enc in encomiendas_retrasadas
            ]
        )

    return len(encomiendas_retrasadas)


# ── sync_to_async:
#    si Django < 4.1 o el ORM no tiene método async ────────────────

# Decorador:
# convierte una función síncrona en una async
#@sync_to_async
#def get_encomiendas_activas():
    #return list(Encomienda.objects.activas().con_relaciones())


# Uso:
    #encomiendas = await get_encomiendas_activas()


# Alternativa en línea (sin decorador):
    #encomiendas = await sync_to_async(
        #lambda: list(
            #Encomienda.objects
            #.activas()
            #.con_relaciones()
        #)
    #)()