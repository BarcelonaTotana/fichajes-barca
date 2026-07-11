# -*- coding: utf-8 -*-
"""
Envío de alertas a Telegram.

Las credenciales se leen de variables de entorno (nunca se escriben en el código):
  - TELEGRAM_TOKEN    : token del bot (de @BotFather)
  - TELEGRAM_CHAT_ID  : tu chat id (de @userinfobot)

En GitHub las guardaremos como "Secrets". Si no hay credenciales, no falla:
simplemente no envía (útil para probar en local).
"""
import os
import requests

import analisis as A

API = "https://api.telegram.org/bot{token}/sendMessage"


def _escapar(texto):
    # Modo HTML de Telegram: escapamos los caracteres reservados.
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def construir_mensaje(n):
    """Mensaje decorado estilo: jugador / importe / estado / % / fuente."""
    texto = n["titulo"]
    jugador = A.extraer_jugador(texto)
    if jugador:
        primera = f"{jugador} {A.direccion(texto)}"
    else:
        primera = texto  # sin jugador claro -> el titular completo
    importe = A.extraer_importe(texto) or "—"
    estado = n["estado"]
    prob = A.probabilidad(estado, n["tier"])
    return (
        f"⚽ <b>{_escapar(primera)}</b>\n"
        f"💰 {importe}\n"
        f"{A.ESTADO_EMOJI.get(estado, '💬')} {A.ESTADO_LEGIBLE.get(estado, estado)}\n"
        f"📊 {prob}%\n"
        f"📰 Fuente: {_escapar(n['medio'])}\n"
        f'🔗 <a href="{n["enlace"]}">Ver noticia</a>'
    )


def enviar_alertas(noticias):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("  [Telegram] Sin credenciales (TELEGRAM_TOKEN/CHAT_ID). No se envían alertas.")
        return

    for n in noticias:
        mensaje = construir_mensaje(n)
        try:
            r = requests.post(
                API.format(token=token),
                data={
                    "chat_id": chat_id,
                    "text": mensaje,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": "false",
                },
                timeout=15,
            )
            if r.status_code == 200:
                print(f"  [Telegram] Alerta enviada: {n['titulo'][:60]}")
            else:
                print(f"  [Telegram] Error {r.status_code}: {r.text[:150]}")
        except Exception as e:
            print(f"  [Telegram] Excepción: {e}")
