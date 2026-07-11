# -*- coding: utf-8 -*-
"""Envía una alerta de prueba a Telegram para confirmar que el circuito funciona."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import telegram_alertas

telegram_alertas.enviar_alertas([{
    "tier": 0,
    "categoria": "primer_equipo",
    "titulo": "✅ Alertas activadas: el monitor de fichajes del Barça ya está en marcha",
    "medio": "Sistema",
    "estado": "oficial",
    "enlace": "https://barcelonatotana.github.io/fichajes-barca/",
}])
