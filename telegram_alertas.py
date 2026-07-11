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

API = "https://api.telegram.org/bot{token}/sendMessage"

EMOJI_TIER = {0: "🔵 OFICIAL", 1: "🟢 Fiable"}


def _escapar(texto):
    # Modo HTML de Telegram: escapamos los caracteres reservados.
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def enviar_alertas(noticias):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("  [Telegram] Sin credenciales (TELEGRAM_TOKEN/CHAT_ID). No se envían alertas.")
        return

    for n in noticias:
        cabecera = EMOJI_TIER.get(n["tier"], "🟢")
        cat = "🌱 Cantera" if n["categoria"] == "cantera" else "⭐ Primer equipo"
        mensaje = (
            f"<b>{cabecera}</b> · {cat}\n"
            f"<b>{_escapar(n['titulo'])}</b>\n"
            f"Medio: {_escapar(n['medio'])} · Estado: {n['estado']}\n"
            f'<a href="{n["enlace"]}">Abrir noticia</a>'
        )
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
