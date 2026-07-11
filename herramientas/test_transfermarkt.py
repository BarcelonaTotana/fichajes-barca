# -*- coding: utf-8 -*-
"""Prueba: ¿se puede leer Transfermarkt desde GitHub Actions? (IPs de servidor)."""
import requests, re

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36",
     "Accept-Language": "es-ES,es;q=0.9"}
url = "https://www.transfermarkt.es/fc-barcelona/geruechte/verein/131"
try:
    r = requests.get(url, headers=H, timeout=30)
    jug = len(re.findall(r"/profil/spieler/", r.text))
    print(f"status={r.status_code} len={len(r.text)} enlaces_jugador={jug}")
    if r.status_code == 200 and jug > 3:
        print(">>> OK: Transfermarkt ACCESIBLE desde GitHub Actions")
    else:
        print(">>> BLOQUEADO o sin datos")
except Exception as e:
    print(">>> ERROR:", repr(e)[:150])
