# -*- coding: utf-8 -*-
"""
Fuente ÚNICA de datos: Transfermarkt (tiro fijo, sin ruido).

Lee, para el primer equipo (id 131) y el Barça Atlètic (id 2464):
  - Rumores  (…/geruechte/verein/ID): jugador, club, valor, fecha y % REAL.
  - Fichajes cerrados (…/transfers/verein/ID): Altas y Bajas con importe (oficial).

Devuelve una lista de noticias ya estructuradas (sin necesidad de filtros de ruido).
"""
import re
import time
import datetime as dt
import hashlib
import unicodedata

import requests
import urllib3

VERIFICAR_SSL = None  # lo fija recolector según el entorno (local vs nube)
BASE = "https://www.transfermarkt.es"
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

# (id de club en Transfermarkt, slug, categoría del proyecto)
CLUBS = [("131", "fc-barcelona", "primer_equipo"),
         ("2464", "fc-barcelona-b", "barca_atletic")]


def _descargar(url):
    ultima = None
    for intento in range(3):
        try:
            r = requests.get(url, headers=CABECERAS, timeout=30, verify=bool(VERIFICAR_SSL))
            if r.status_code in (429, 503):
                ultima = requests.exceptions.HTTPError(f"{r.status_code}")
                time.sleep(5 * (intento + 1))
                continue
            r.raise_for_status()
            return r.text
        except requests.exceptions.RequestException as e:
            ultima = e
            time.sleep(3)
    raise ultima or Exception("descarga fallida")


def _norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _id(jugador, club, tipo):
    return hashlib.sha1(_norm(f"{jugador}|{club}|{tipo}").encode()).hexdigest()[:16]


def _importe(texto):
    """'40,00 mill. €' -> '40M'; 'gratis'/'cesión' -> etiqueta; '-'/'?' -> None."""
    t = (texto or "").lower()
    m = re.search(r"([\d.,]+)\s*mill", t)
    if m:
        n = m.group(1).rstrip("0").rstrip(",").rstrip(".") or m.group(1)
        return n + "M"
    if "mil" in t and "€" in t:
        m = re.search(r"([\d.,]+)\s*mil", t)
        if m:
            return m.group(1) + "K"
    if "gratis" in t or "libre" in t:
        return "Gratis"
    if "cesión" in t or "cesion" in t or "préstamo" in t or "prestamo" in t:
        return "Cesión"
    return None


def _fecha_iso(texto):
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", texto or "")
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo}-{d}T00:00:00"
    return dt.datetime.utcnow().isoformat()


def _estado(prob):
    if prob is None:
        return "rumor"
    if prob >= 85:
        return "here_we_go"
    if prob >= 60:
        return "avanzado"
    return "rumor"


def _sopa(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")


def _club_de_fila(tr):
    a = tr.select_one('a[href*="/verein/"]')
    if not a:
        return ""
    img = a.find("img")
    if img and img.get("alt"):
        return img["alt"].strip()
    return (a.get("title") or a.get_text(strip=True) or "").strip()


def _rumores(club_id, slug, categoria):
    noticias = []
    try:
        soup = _sopa(_descargar(f"{BASE}/{slug}/geruechte/verein/{club_id}"))
    except Exception as e:
        print(f"  [TM rumores {club_id}] ERROR: {repr(e)[:120]}")
        return noticias
    tabla = soup.find("table", class_="items")
    if not tabla or not tabla.find("tbody"):
        return noticias
    for tr in tabla.find("tbody").find_all("tr", recursive=False):
        ja = tr.select_one('a[href*="/profil/spieler/"]')
        if not ja:
            continue
        jugador = ja.get_text(strip=True)
        texto = tr.get_text(" ", strip=True)
        club = _club_de_fila(tr)
        mp = re.search(r"(\d{1,3})\s*%", texto)
        prob = int(mp.group(1)) if mp else None
        estado = _estado(prob)
        noticias.append({
            "id": _id(jugador, club, "rumor"),
            "jugador": jugador,
            "club": club,
            "tipo": "rumor",
            "titulo": f"{jugador} ⇄ Barça",
            "enlace": BASE + ja.get("href", ""),
            "medio": "Transfermarkt",
            "tier": 1,
            "categoria": categoria,
            "estado": estado,
            "probabilidad": prob,
            "importe": _importe(texto),
            "fecha": _fecha_iso(texto),
        })
    print(f"  TM rumores {categoria}: {len(noticias)}")
    return noticias


def _transfers(club_id, slug, categoria):
    noticias = []
    try:
        soup = _sopa(_descargar(f"{BASE}/{slug}/transfers/verein/{club_id}"))
    except Exception as e:
        print(f"  [TM fichajes {club_id}] ERROR: {repr(e)[:120]}")
        return noticias
    tablas = soup.select("table.items")
    # [0] = Altas (llegadas), [1] = Bajas (salidas)
    for idx, tipo in ((0, "llegada"), (1, "salida")):
        if idx >= len(tablas):
            continue
        tbody = tablas[idx].find("tbody")
        if not tbody:
            continue
        for tr in tbody.find_all("tr", recursive=False):
            ja = tr.select_one('a[href*="/profil/spieler/"]')
            if not ja:
                continue
            jugador = ja.get_text(strip=True)
            club = _club_de_fila(tr)
            # Descarta promociones/movimientos internos del juvenil (no son mercado).
            if "juvenil" in _norm(club):
                continue
            celdas = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            importe = _importe(" ".join(celdas[-2:]))
            flecha = "→ Barça" if tipo == "llegada" else f"→ {club}"
            noticias.append({
                "id": _id(jugador, club, tipo),
                "jugador": jugador,
                "club": club,
                "tipo": tipo,
                "titulo": f"{jugador} {flecha}",
                "enlace": BASE + ja.get("href", ""),
                "medio": "Transfermarkt",
                "tier": 0,                 # fichaje cerrado = oficial
                "categoria": categoria,
                "estado": "oficial",
                "probabilidad": 100,
                "importe": importe,
                "fecha": dt.datetime.utcnow().isoformat(),
            })
        print(f"  TM {tipo} {categoria}: {sum(1 for n in noticias if n['tipo']==tipo)}")
    return noticias


def recolectar():
    todo = []
    for club_id, slug, categoria in CLUBS:
        todo += _rumores(club_id, slug, categoria)
        time.sleep(1)
        todo += _transfers(club_id, slug, categoria)
        time.sleep(1)
    return todo
