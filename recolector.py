# -*- coding: utf-8 -*-
"""
Recolector de fichajes del FC Barcelona (fútbol masculino).

Lee las fuentes RSS (Google News + medios directos), filtra lo relacionado con
fichajes del Barça, clasifica cada noticia (tier de fiabilidad, categoría,
estado del fichaje), deduplica y guarda todo en data/fichajes.json.

Si hay noticias NUEVAS de fuentes fiables (tier 0 ó 1) y hay credenciales de
Telegram, envía una alerta al móvil.

Uso:  python recolector.py
"""
import os
import re
import json
import time
import hashlib
import datetime as dt
from urllib.parse import urlparse

import feedparser
import requests
import urllib3

import config.fuentes as F
import telegram_alertas

# El JSON vive dentro de docs/ para que GitHub Pages lo sirva junto al panel.
RUTA_DATOS = os.path.join("docs", "fichajes.json")
MAX_NOTICIAS = 400          # límite para no crecer sin fin
ANTIGUEDAD_DIAS = 30        # descarta noticias más viejas de N días

# En GitHub Actions los certificados funcionan (verify=True, lo normal).
# Solo en local, si tu Python no tiene los certificados bien, exporta
# SSL_NO_VERIFY=1 para saltar la verificación (NO usar en producción).
VERIFICAR_SSL = os.environ.get("SSL_NO_VERIFY", "").strip() != "1"
if not VERIFICAR_SSL:
    urllib3.disable_warnings()

CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; MonitorFichajesBarca/1.0)"}


def _descargar(url):
    """Descarga el XML del feed con User-Agent de navegador y lo devuelve en bytes."""
    r = requests.get(url, headers=CABECERAS, timeout=25, verify=VERIFICAR_SSL)
    r.raise_for_status()
    return r.content


# ---------------------------------------------------------------------------
# Utilidades de clasificación
# ---------------------------------------------------------------------------
def _dominio(url):
    try:
        d = urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""


def _tier(dominio, medio):
    """Tier por dominio (RSS directo) o por nombre de medio (Google News)."""
    if dominio and dominio in F.TIER_POR_DOMINIO:
        return F.TIER_POR_DOMINIO[dominio]
    nombre = (medio or "").lower()
    for clave, tier in F.TIER_POR_NOMBRE:
        # Coincidencia por palabra completa: "sport" casa con el diario "SPORT"
        # pero NO con "beIN Sports" ni "Motorcycle Sports".
        if re.search(r"\b" + re.escape(clave) + r"\b", nombre):
            return tier
    return F.TIER_POR_DEFECTO


def _estado(texto):
    t = texto.lower()
    for estado, claves in F.PALABRAS_ESTADO:
        if any(c in t for c in claves):
            return estado
    return F.ESTADO_POR_DEFECTO


def _es_cantera(texto, categoria_origen):
    if categoria_origen == "cantera":
        return True
    t = texto.lower()
    return any(p in t for p in F.PALABRAS_CANTERA)


def _es_descartable(texto):
    t = texto.lower()
    return any(p in t for p in F.PALABRAS_DESCARTE)


def _id_noticia(enlace, titulo):
    base = (enlace or "") + "|" + (titulo or "")
    return hashlib.sha1(base.encode("utf-8", "ignore")).hexdigest()[:16]


def _limpia_titulo(titulo):
    # Google News añade " - Medio" al final del título. Lo separamos.
    if " - " in titulo:
        partes = titulo.rsplit(" - ", 1)
        return partes[0].strip(), partes[1].strip()
    return titulo.strip(), ""


def _fecha_iso(entrada):
    for campo in ("published_parsed", "updated_parsed"):
        val = entrada.get(campo)
        if val:
            return dt.datetime(*val[:6]).isoformat()
    return dt.datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Recolección
# ---------------------------------------------------------------------------
def recolectar_feed(nombre, categoria_origen, url):
    noticias = []
    try:
        contenido = _descargar(url)
        feed = feedparser.parse(contenido)
    except Exception as e:
        print(f"  [ERROR] {nombre}: {repr(e)[:150]}")
        return noticias

    if getattr(feed, "bozo", 0) and not feed.entries:
        print(f"  [aviso] {nombre}: feed vacío o no válido")
        return noticias

    for entrada in feed.entries:
        titulo_bruto = entrada.get("title", "").strip()
        if not titulo_bruto:
            continue
        enlace = entrada.get("link", "")
        resumen = re.sub("<[^>]+>", " ", entrada.get("summary", ""))
        texto = titulo_bruto + " " + resumen

        if _es_descartable(texto):
            continue

        titulo, medio_en_titulo = _limpia_titulo(titulo_bruto)
        dominio = _dominio(enlace)
        # En Google News el enlace es news.google.com; el medio real va en el título.
        fuente_medio = medio_en_titulo or dominio or nombre
        tier = _tier(dominio, fuente_medio)

        noticias.append({
            "id": _id_noticia(enlace, titulo),
            "titulo": titulo,
            "enlace": enlace,
            "medio": fuente_medio,
            "tier": tier,
            "tier_etiqueta": F.ETIQUETA_TIER.get(tier, "?"),
            "categoria": "cantera" if _es_cantera(texto, categoria_origen) else "primer_equipo",
            "estado": _estado(texto),
            "fecha": _fecha_iso(entrada),
            "fuente_feed": nombre,
            "visto_por_primera_vez": dt.datetime.utcnow().isoformat(),
        })
    print(f"  {nombre}: {len(noticias)} noticias")
    return noticias


def cargar_existentes():
    if os.path.exists(RUTA_DATOS):
        try:
            with open(RUTA_DATOS, "r", encoding="utf-8") as f:
                return json.load(f).get("noticias", [])
        except Exception:
            return []
    return []


def guardar(noticias):
    os.makedirs("docs", exist_ok=True)
    salida = {
        "actualizado": dt.datetime.utcnow().isoformat() + "Z",
        "total": len(noticias),
        "noticias": noticias,
    }
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


def main():
    print("== Recolector de fichajes FC Barcelona ==")
    existentes = {n["id"]: n for n in cargar_existentes()}
    print(f"Noticias previas en base de datos: {len(existentes)}")

    recolectadas = []
    for nombre, categoria, url in F.BUSQUEDAS_GOOGLE_NEWS:
        recolectadas += recolectar_feed(nombre, categoria, url)
        time.sleep(1)
    for nombre, categoria, url in F.RSS_DIRECTOS:
        recolectadas += recolectar_feed(nombre, categoria, url)
        time.sleep(1)

    nuevas = []
    for n in recolectadas:
        if n["id"] not in existentes:
            existentes[n["id"]] = n
            nuevas.append(n)

    # Ordena por fecha (más reciente primero) y recorta antigüedad/tamaño.
    limite = dt.datetime.utcnow() - dt.timedelta(days=ANTIGUEDAD_DIAS)
    todas = []
    for n in existentes.values():
        try:
            f = dt.datetime.fromisoformat(n["fecha"].replace("Z", ""))
        except Exception:
            f = dt.datetime.utcnow()
        if f >= limite:
            todas.append((f, n))
    todas.sort(key=lambda x: x[0], reverse=True)
    todas = [n for _, n in todas][:MAX_NOTICIAS]

    guardar(todas)
    print(f"\nNoticias nuevas: {len(nuevas)} · Total guardadas: {len(todas)}")

    # Alertas: solo noticias NUEVAS de fuentes fiables (tier 0 ó 1).
    alertar = [n for n in nuevas if n["tier"] <= 1]
    if alertar:
        telegram_alertas.enviar_alertas(alertar)


if __name__ == "__main__":
    main()
