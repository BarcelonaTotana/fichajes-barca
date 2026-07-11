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
import unicodedata
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
# Red de seguridad: máximo de alertas por ejecución (evita ráfagas por cualquier glitch).
MAX_ALERTAS_POR_EJECUCION = 10

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


def _es_femenino(texto):
    """Detecta fútbol femenino por marcas o por nombres de jugadoras del Barça Femení."""
    t = texto.lower()
    return (any(m in t for m in F.MARCAS_FEMENINO) or
            any(j in t for j in F.JUGADORAS_FEMENINO))


def _es_relevante(texto):
    """Verdadero si habla del Barça Y de un fichaje Y no está bloqueado NI es femenino."""
    t = texto.lower()
    if any(b in t for b in F.PALABRAS_BLOQUEO):
        return False
    if _es_femenino(texto):
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


def _tiene_movimiento(titulo):
    """Señal real de movimiento/interés (palabra completa: 'ficha' sí, 'fichajes' no)."""
    t = titulo.lower()
    return any(re.search(r"\b" + re.escape(w) + r"\b", t) for w in F.PALABRAS_MOVIMIENTO)


def apto_para_telegram(n):
    """PUNTO DE CONTROL: analiza la noticia y decide si puede enviarse a Telegram.
    Debe cumplir TODO: fuente fiable, PRIMER EQUIPO, movimiento real y no femenino.
    (La deduplicación por 'alertadas'/'cerradas' se aplica aparte, en el bucle.)"""
    if n["tier"] > TIER_ALERTA:            # solo fuentes fiables
        return False
    if n["categoria"] != "primer_equipo":  # solo primer equipo (nada de cantera)
        return False
    if not _tiene_movimiento(n["titulo"]):  # debe ser un movimiento de mercado, no análisis
        return False
    if _es_femenino(n["titulo"]):          # nada de fútbol femenino
        return False
    # Debe ser del CLUB, no de la ciudad de Barcelona (salvo fuente oficial, tier 0).
    if n["tier"] != 0 and not any(c in n["titulo"].lower() for c in F.PALABRAS_CLUB):
        return False
    return True


def _id_noticia(titulo):
    # ID estable basado en el título NORMALIZADO (sin acentos, sin puntuación,
    # minúsculas). Google News cambia el enlace en cada consulta y varía acentos/
    # puntuación, así que normalizamos a fondo para que la misma noticia dé el mismo id.
    s = unicodedata.normalize("NFD", (titulo or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:16]


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
            "id": _id_noticia(titulo),
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
    """Devuelve (noticias, cerradas, alertadas).
       cerradas = jugadores con operación oficial (no re-alertar).
       alertadas = ids de noticias ya avisadas por Telegram (nunca se reenvían)."""
    if os.path.exists(RUTA_DATOS):
        try:
            with open(RUTA_DATOS, "r", encoding="utf-8") as f:
                d = json.load(f)
                return (d.get("noticias", []), set(d.get("cerradas", [])),
                        set(d.get("alertadas", [])))
        except Exception:
            return [], set(), set()
    return [], set(), set()


def guardar(noticias, cerradas, alertadas):
    os.makedirs("docs", exist_ok=True)
    salida = {
        "actualizado": dt.datetime.utcnow().isoformat() + "Z",
        "total": len(noticias),
        "cerradas": sorted(cerradas),          # operaciones oficiales (no re-alertar por jugador)
        "alertadas": sorted(alertadas)[-5000:],  # ids ya avisados (tope para no crecer sin fin)
        "noticias": noticias,
    }
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


def main():
    print("== Recolector de fichajes FC Barcelona ==")
    noticias_previas, cerradas, alertadas = cargar_datos()
    existentes = {n["id"]: n for n in noticias_previas}
    arranque_en_frio = len(existentes) == 0 and not alertadas  # reinicio real -> no alertar
    print(f"Noticias previas: {len(existentes)} · Cerradas: {len(cerradas)} · Alertadas: {len(alertadas)}")

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
    # Universo: items ÚNICOS vistos en esta ejecución. Una noticia se avisa como
    # máximo UNA vez en la vida (registro persistente 'alertadas'), aunque reaparezca.
    vistos = {}
    for n in recolectadas:
        vistos.setdefault(n["id"], n)

    candidatas = [n for n in vistos.values()
                  if apto_para_telegram(n)          # PUNTO DE CONTROL (primer equipo, fiable, etc.)
                  and n["id"] not in alertadas]      # y que no se haya avisado ya
    # Oficiales/acuerdos primero (para que dentro del tope tengan prioridad).
    candidatas.sort(key=lambda n: 0 if n["estado"] in ESTADOS_CIERRE else 1)

    enviables = []
    for n in candidatas:
        clave = analisis.clave_operacion(analisis.extraer_jugador(n["titulo"]))
        if clave and clave in cerradas:
            alertadas.add(n["id"])   # operación cerrada -> no se avisa (la web sí la muestra)
            continue
        enviables.append((n, clave))

    if arranque_en_frio:
        for n, _ in enviables:
            alertadas.add(n["id"])   # tras un reinicio: se registran pero NO se envían
        print(f"Arranque en frío: se omiten {len(enviables)} alertas (evita ráfaga).")
    else:
        lote = enviables[:MAX_ALERTAS_POR_EJECUCION]
        for n, clave in lote:
            alertadas.add(n["id"])
            if n["estado"] in ESTADOS_CIERRE and clave:
                cerradas.add(clave)  # ese jugador queda cerrado para Telegram
        if len(enviables) > MAX_ALERTAS_POR_EJECUCION:
            print(f"AVISO: {len(enviables)} candidatas; se envían {MAX_ALERTAS_POR_EJECUCION} "
                  f"(el resto, en próximas ejecuciones).")
        if lote:
            print(f"Enviando {len(lote)} alertas a Telegram…")
            telegram_alertas.enviar_alertas([n for n, _ in lote])

    guardar(todas, cerradas, alertadas)
    print(f"Noticias nuevas: {len(nuevas)} · Total guardadas: {len(todas)}")


if __name__ == "__main__":
    main()
