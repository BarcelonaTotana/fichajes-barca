# -*- coding: utf-8 -*-
"""
Herramienta de un solo uso: muestra el/los Chat ID que han escrito al bot.
Se ejecuta en GitHub Actions (donde está el token como secreto) mediante el
workflow "Obtener Chat ID". Lee los mensajes recientes del bot (getUpdates)
e imprime el chat id de cada uno.
"""
import os
import requests

token = os.environ.get("TELEGRAM_TOKEN", "").strip()
if not token:
    print("No hay TELEGRAM_TOKEN configurado como secreto.")
    raise SystemExit(0)

r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20)
data = r.json()
print("HTTP", r.status_code, "| ok:", data.get("ok"), "| descripción:", data.get("description", "-"))

chats = {}
for u in data.get("result", []):
    msg = u.get("message") or u.get("edited_message") or u.get("channel_post") or {}
    chat = msg.get("chat")
    if chat:
        chats[chat["id"]] = chat.get("first_name") or chat.get("title") or chat.get("username") or ""

if chats:
    print("\n===== CHAT ID ENCONTRADO(S) =====")
    for cid, name in chats.items():
        print(f">>> CHAT_ID = {cid}   (nombre: {name})")
else:
    print("\nNo hay mensajes recientes. Escribe algo a tu bot @fichajes_barca_bot y reintenta.")
