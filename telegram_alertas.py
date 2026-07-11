# -*- coding: utf-8 -*-
"""
Envío de alertas a Telegram con datos de Transfermarkt.

Credenciales por variables de entorno (nunca en el código):
  - TELEGRAM_TOKEN, TELEGRAM_CHAT_ID  (guardadas como Secrets en GitHub).
Si no hay credenciales, no falla: simplemente no envía (útil en local).
"""
import os
import requests

API = "https://api.telegram.org/bot{token}/sendMessage"

LEGIBLE = {"oficial": "Oficial", "here_we_go": "Acuerdo muy avanzado",
           "avanzado": "Avanzado", "rumor": "Rumor"}
EMOJI = {"oficial": "✅", "here_we_go": "🤝", "avanzado": "🔜", "rumor": "💬"}
EMOJI_CAT = {"barca_atletic": "🅱️ Barça Atlètic", "primer_equipo": "⭐ Primer equipo"}


def _escapar(texto):
    return (texto or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def construir_mensaje(n):
    est = n.get("estado", "rumor")
    prob = n.get("probabilidad")
    club = n.get("club")
    linea_club = f"🔁 {_escapar(club)}\n" if club and n["tipo"] == "rumor" else ""
    linea_prob = f"📊 {prob}%\n" if prob is not None else ""
    return (
        f"⚽ <b>{_escapar(n['titulo'])}</b>\n"
        f"{linea_club}"
        f"💰 {n.get('importe') or '—'}\n"
        f"{EMOJI.get(est, '💬')} {LEGIBLE.get(est, est)}\n"
        f"{linea_prob}"
        f"📰 Transfermarkt · {EMOJI_CAT.get(n.get('categoria'), '')}\n"
        f'🔗 <a href="{n["enlace"]}">Ver ficha</a>'
    )


def enviar_alertas(noticias):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("  [Telegram] Sin credenciales. No se envían alertas.")
        return
    for n in noticias:
        try:
            r = requests.post(
                API.format(token=token),
                data={"chat_id": chat_id, "text": construir_mensaje(n),
                      "parse_mode": "HTML", "disable_web_page_preview": "false"},
                timeout=15,
            )
            if r.status_code == 200:
                print(f"  [Telegram] Enviada: {n['titulo'][:50]}")
            else:
                print(f"  [Telegram] Error {r.status_code}: {r.text[:150]}")
        except Exception as e:
            print(f"  [Telegram] Excepción: {e}")
