# -*- coding: utf-8 -*-
"""
Recolector de fichajes del FC Barcelona (fútbol masculino).

Flujo:
1. Descarga RSS de: búsquedas por medio fiable (tier garantizado) + búsquedas generales.
2. FILTRA por relevancia: solo fichajes reales del Barça (descarta ruido).
3. CLASIFICA cada noticia: fiabilidad (tier del medio, mejorado por el periodista citado),
   categoría (cantera por contenido) y estado del fichaje.
4. Deduplica y guarda docs/fichajes.json.
5. Envía alertas a Telegram de las noticias NUEVAS de fuentes fiables (tier 0 ó 1).

Uso:  python recolector.py   (en local: SSL_NO_VERIFY=1 python recolector.py)
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
import analisis

# Fiabilidad mínima para avisar por Telegram (0=oficial,1=fiable,2=bastante fiable).
TIER_ALERTA = 2
# Estados que "cierran" una operación (ya no se vuelve a avisar de ese jugador).
ESTADOS_CIERRE = ("oficial", "here_we_go")

# El JSON vive dentro de docs/ para que GitHub Pages lo sirva junto al panel.
RUTA_DATOS = os.path.join("docs", "fichajes.json")
MAX_NOTICIAS = 400
ANTIGUEDAD_DIAS = 30

VERIFICAR_SSL = os.environ.get("SSL_NO_VERIFY", "").strip() != "1"
if not VERIFICAR_SSL:
    urllib3.disable_warnings()
CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; MonitorFichajesBarca/1.0)"}


def _descargar(url):
    r = requests.get(url, headers=CABECERAS, timeout=25, verify=VERIFICAR_SSL)
    r.raise_for_status()
    return r.content


# ---------------------------------------------------------------------------
# Clasificación
# ---------------------------------------------------------------------------
def _dominio(url):
    try:
        d = urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""


def _tier_medio(dominio, medio):
    """Tier según el dominio o el nombre del medio (palabra completa)."""
    if dominio and dominio in F.TIER_POR_DOMINIO:
        return F.TIER_POR_DOMINIO[dominio]
    nombre = (medio or "").lower()
    for clave, tier in F.TIER_POR_NOMBRE:
        if re.search(r"\b" + re.escape(clave) + r"\b", nombre):
            return tier
    return F.TIER_POR_DEFECTO


def _tier_periodista(texto):
    """Mejor tier (nº más bajo) de los periodistas citados en el texto, o None."""
    t = texto.lower()
    tiers = [tier for nombre, tier in F.PERIODISTAS_TIER if nombre in t]
    return min(tiers) if tiers else None


def _es_relevante(texto):
    """Verdadero si habla del Barça Y de un fichaje Y no está bloqueado."""
    t = texto.lower()
    if any(b in t for b in F.PALABRAS_BLOQUEO):
        return False
    if not any(b in t for b in F.PALABRAS_BARSA):
        return False
    if not any(f in t for f in F.PALABRAS_FICHAJE):
        return False
    return True


def _estado(texto):
    t = texto.lower()
    for estado, claves in F.PALABRAS_ESTADO:
        if any(c in t for c in claves):
            return estado
    return F.ESTADO_POR_DEFECTO


def _es_cantera(texto):
    t = texto.lower()
    return any(re.search(r"\b" + re.escape(p) + r"\b", t) for p in F.PALABRAS_CANTERA)


def _id_noticia(enlace, titulo):
    base = (enlace or "") + "|" + (titulo or "")
    return hashlib.sha1(base.encode("utf-8", "ignore")).hexdigest()[:16]


def _limpia_titulo(titulo):
    # Google News añade " - Medio" al final del título.
    if " - " in titulo:
        cuerpo, medio = titulo.rsplit(" - ", 1)
        return cuerpo.strip(), medio.strip()
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
def recolectar_feed(nombre, tier_forzado, url):
    """tier_forzado=int -> todas las noticias son de ese medio/tier (búsqueda por medio).
       tier_forzado=None -> se deduce el medio y el tier de cada noticia."""
    noticias = []
    try:
        feed = feedparser.parse(_descargar(url))
    except Exception as e:
        print(f"  [ERROR] {nombre}: {repr(e)[:150]}")
        return noticias

    for entrada in feed.entries:
        titulo_bruto = entrada.get("title", "").strip()
        if not titulo_bruto:
            continue
        enlace = entrada.get("link", "")
        resumen = re.sub("<[^>]+>", " ", entrada.get("summary", ""))
        texto = titulo_bruto + " " + resumen

        if not _es_relevante(texto):
            continue

        titulo, medio_en_titulo = _limpia_titulo(titulo_bruto)

        if tier_forzado is not None:
            medio = nombre
            tier = tier_forzado
        else:
            medio = medio_en_titulo or _dominio(enlace) or nombre
            tier = _tier_medio(_dominio(enlace), medio)
            # Rescate por periodista: si citan a alguien más fiable, mejora el tier.
            tp = _tier_periodista(texto)
            if tp is not None:
                tier = min(tier, tp)

        noticias.append({
            "id": _id_noticia(enlace, titulo),
            "titulo": titulo,
            "enlace": enlace,
            "medio": medio,
            "tier": tier,
            "tier_etiqueta": F.ETIQUETA_TIER.get(tier, "?"),
            "categoria": "cantera" if _es_cantera(texto) else "primer_equipo",
            "estado": _estado(texto),
            "fecha": _fecha_iso(entrada),
            "fuente_feed": nombre,
            "visto_por_primera_vez": dt.datetime.utcnow().isoformat(),
        })
    print(f"  {nombre}: {len(noticias)} relevantes")
    return noticias


def cargar_datos():
    """Devuelve (noticias, cerradas) desde el JSON. cerradas = jugadores ya fichados/oficiales."""
    if os.path.exists(RUTA_DATOS):
        try:
            with open(RUTA_DATOS, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("noticias", []), set(d.get("cerradas", []))
        except Exception:
            return [], set()
    return [], set()


def guardar(noticias, cerradas):
    os.makedirs("docs", exist_ok=True)
    salida = {
        "actualizado": dt.datetime.utcnow().isoformat() + "Z",
        "total": len(noticias),
        "cerradas": sorted(cerradas),   # operaciones ya cerradas (no re-alertar en Telegram)
        "noticias": noticias,
    }
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


def main():
    print("== Recolector de fichajes FC Barcelona ==")
    noticias_previas, cerradas = cargar_datos()
    existentes = {n["id"]: n for n in noticias_previas}
    arranque_en_frio = len(existentes) == 0   # tras un reinicio, no alertar (evita ráfaga)
    print(f"Noticias previas: {len(existentes)} · Operaciones cerradas: {len(cerradas)}")

    recolectadas = []
    # Primero los medios fiables (así ganan en la deduplicación).
    for medio, tier, _cat, url in F.BUSQUEDAS_POR_MEDIO:
        recolectadas += recolectar_feed(medio, tier, url)
        time.sleep(1)
    for nombre, tier_forzado, _cat, url in F.BUSQUEDAS_GENERALES:
        recolectadas += recolectar_feed(nombre, tier_forzado, url)
        time.sleep(1)

    nuevas = []
    for n in recolectadas:
        if n["id"] not in existentes:
            existentes[n["id"]] = n
            nuevas.append(n)

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

    # ---- Alertas de Telegram ----
    # Candidatas: noticias NUEVAS de fuentes fiables (tier <= TIER_ALERTA).
    # Se procesan primero las "de cierre" (oficial/acuerdo total) para que, si en
    # la misma tanda hay varias del mismo jugador, solo avise la primera.
    candidatas = [n for n in nuevas if n["tier"] <= TIER_ALERTA]
    candidatas.sort(key=lambda n: 0 if n["estado"] in ESTADOS_CIERRE else 1)

    a_enviar = []
    for n in candidatas:
        clave = analisis.clave_operacion(analisis.extraer_jugador(n["titulo"]))
        if clave and clave in cerradas:
            continue  # operación ya cerrada -> no se re-alerta (la web sí la sigue mostrando)
        a_enviar.append(n)
        if n["estado"] in ESTADOS_CIERRE and clave:
            cerradas.add(clave)  # a partir de ahora, ese jugador queda cerrado en Telegram

    guardar(todas, cerradas)
    print(f"\nNoticias nuevas: {len(nuevas)} · Total guardadas: {len(todas)}")

    if arranque_en_frio:
        print(f"Arranque en frío: se omiten {len(a_enviar)} alertas (evita ráfaga).")
    elif a_enviar:
        print(f"Enviando {len(a_enviar)} alertas a Telegram…")
        telegram_alertas.enviar_alertas(a_enviar)


if __name__ == "__main__":
    main()
