# -*- coding: utf-8 -*-
"""Envía a Telegram la noticia real del fichaje de Adeyemi (de un medio fiable),
usando el mismo formato del sistema. Herramienta puntual, a petición."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import telegram_alertas
import analisis as A

RUTA = os.path.join("docs", "fichajes.json")
noticias = json.load(open(RUTA, encoding="utf-8")).get("noticias", [])

# Noticias de Adeyemi de fuente fiable (tier <= 2). Se prioriza la que da el mensaje
# MÁS COMPLETO: que se pueda extraer el nombre del jugador y el importe.
prioridad = {"oficial": 0, "here_we_go": 1, "avanzado": 2, "rumor": 3}
ade = [n for n in noticias if "adeyemi" in n["titulo"].lower() and n["tier"] <= 2]
ade.sort(key=lambda n: (
    0 if A.extraer_jugador(n["titulo"]) else 1,
    0 if A.extraer_importe(n["titulo"]) else 1,
    prioridad.get(n["estado"], 9),
    n["tier"],
))

if ade:
    telegram_alertas.enviar_alertas([ade[0]])
    print("Enviada:", ade[0]["titulo"])
else:
    print("No se encontró ninguna noticia de Adeyemi de fuente fiable en los datos.")
