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

Uso (desde la raíz del repo):  python -m bot.recolector
      (en local: SSL_NO_VERIFY=1 python -m bot.recolector)
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

from bot import fuentes as F
from bot import telegram_alertas
from bot import analisis

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
# User-Agent de navegador: el cortafuegos de sport.es responde 406 a los que no lo parecen.
CABECERAS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"}


def _ahora():
    """Hora UTC sin zona (mismo formato que siempre en el JSON)."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _descargar(url):
    """Descarga con reintentos. Google News limita por IP (503/429): esperamos y reintentamos."""
    ultima = None
    for intento in range(3):
        try:
            r = requests.get(url, headers=CABECERAS, timeout=25, verify=VERIFICAR_SSL)
            if r.status_code in (429, 503):
                ultima = requests.exceptions.HTTPError(f"{r.status_code} rate-limit")
                time.sleep(5 * (intento + 1))   # backoff: 5s, 10s
                continue
            r.raise_for_status()
            return r.content
        except requests.exceptions.RequestException as e:
            ultima = e
            time.sleep(3)
    raise ultima or Exception("descarga fallida")


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


def _normaliza(texto):
    """Minúsculas y sin acentos (para casar 'Cubarsi' con 'cubarsí')."""
    s = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _patron_nombres(nombres):
    """Regex de palabra completa para una lista de nombres (sin acentos)."""
    return re.compile(r"\b(?:" + "|".join(re.escape(_normaliza(n)) for n in nombres) + r")\b")


_RE_PRIMER_EQUIPO = _patron_nombres(F.JUGADORES_PRIMER_EQUIPO)
_RE_BARCA_ATLETIC = _patron_nombres(F.JUGADORES_BARCA_ATLETIC)
# Expresión de referencia + hasta dos palabras (el nombre que la sigue).
_RE_CONTEXTO_AJENO = re.compile(r"\b(?:" + "|".join(re.escape(c) for c in F.CONTEXTO_AJENO)
                                + r")\s+\S+(?:\s+\S+)?")


def _nombra_jugador(texto):
    """Verdadero si el texto nombra a un jugador de la plantilla (primer equipo o filial)."""
    t = _normaliza(texto)
    return bool(_RE_PRIMER_EQUIPO.search(t) or _RE_BARCA_ATLETIC.search(t))


def _es_femenino(texto):
    """Detecta fútbol femenino por marcas o por nombres de jugadoras del Barça Femení."""
    t = texto.lower()
    return (any(m in t for m in F.MARCAS_FEMENINO) or
            any(j in t for j in F.JUGADORAS_FEMENINO))


def _es_cronica_partido(texto):
    """Crónica de partido (empieza con un marcador tipo '32-28:'). No es mercado, y
    suele ser de otras secciones (balonmano, basket…) que no nombran el deporte."""
    return re.match(r"\s*\d{1,3}\s*[-–]\s*\d{1,3}\b", texto) is not None


def _es_otro_deporte(texto):
    """Deportista conocido de otra sección del Barça (balonmano, basket…)."""
    t = texto.lower()
    return any(j in t for j in F.JUGADORES_OTROS_DEPORTES)


def _es_relevante(texto):
    """Verdadero si habla del Barça Y de un fichaje Y no está bloqueado NI es femenino."""
    t = texto.lower()
    if any(b in t for b in F.PALABRAS_BLOQUEO):
        return False
    if _es_femenino(texto):
        return False
    if _es_cronica_partido(texto):
        return False
    if _es_otro_deporte(texto):
        return False
    if not any(b in t for b in F.PALABRAS_BARSA) and not _nombra_jugador(texto):
        return False
    if not any(f in t for f in F.PALABRAS_FICHAJE):
        return False
    return True


def _apto_feed_general(feed, titulo):
    """En los feeds de todo el fútbol (F.FEEDS_BARSA_EN_TITULO) el TITULAR debe nombrar
    al Barça o a un jugador de su plantilla (no basta el resumen: 'el exzaragocista…')
    y traer un movimiento de mercado. No cuentan menciones de terceros como
    'ex del Barça' o 'rival del Barça'."""
    if feed not in F.FEEDS_BARSA_EN_TITULO:
        return True
    t = titulo.lower()
    for m in F.MENCIONES_BARSA_AJENAS:
        t = t.replace(m, " ")
    # 'jugará junto a Ter Stegen', 'a falta de Gordon': el jugador es solo referencia.
    t = _RE_CONTEXTO_AJENO.sub(" ", t)
    # Palabra completa: 'cule' no debe casar con 'culebrón'.
    if (not any(re.search(r"\b" + re.escape(b) + r"\b", t) for b in F.PALABRAS_BARSA)
            and not _nombra_jugador(t)):
        return False
    return _tiene_movimiento(titulo)


def _estado(texto):
    t = texto.lower()
    for estado, claves in F.PALABRAS_ESTADO:
        if any(c in t for c in claves):
            return estado
    return F.ESTADO_POR_DEFECTO


def _es_renovacion(t):
    return "renov" in t or "renueva" in t


def _clasificar(texto):
    """Ámbito del proyecto: 'primer_equipo' o 'barca_atletic'. Devuelve None para
    DESCARTAR (cantera inferior, o renovaciones del Barça Atlètic)."""
    t = texto.lower()
    n = _normaliza(texto)
    primer_equipo = _RE_PRIMER_EQUIPO.search(n)
    # Filial: por palabra clave, o porque solo se nombra a jugadores del filial.
    if any(k in t for k in F.ATLETIC_KEYS) or (_RE_BARCA_ATLETIC.search(n) and not primer_equipo):
        # Barça Atlètic: solo fichajes / cesiones / ventas (fuera renovaciones).
        if _es_renovacion(t) and not any(k in t for k in F.PALABRAS_ALTA_BAJA):
            return None
        return "barca_atletic"
    if any(k in t for k in F.YOUTH_KEYS) and not primer_equipo:
        return None   # juvenil, cadete, infantil, La Masia… -> fuera del ámbito
                      # (salvo que nombre a un jugador del primer equipo: 'Lamine, joya de La Masia')
    return "primer_equipo"


def _valida_por_titulo(titulo):
    """Revalidación por TÍTULO (para limpiar retroactivamente lo ya guardado cuando
    mejoramos los filtros). Descarta otros deportes, femenino, crónicas, fuera de ámbito."""
    t = titulo.lower()
    if any(b in t for b in F.PALABRAS_BLOQUEO):
        return False
    if _es_femenino(titulo) or _es_cronica_partido(titulo) or _es_otro_deporte(titulo):
        return False
    if _clasificar(titulo) is None:
        return False
    return True


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
    if n["categoria"] not in ("primer_equipo", "barca_atletic"):  # solo estos dos ámbitos
        return False
    if not _tiene_movimiento(n["titulo"]):  # debe ser un movimiento de mercado, no análisis
        return False
    if _es_femenino(n["titulo"]):          # nada de fútbol femenino
        return False
    # Debe ser del CLUB, no de la ciudad de Barcelona (salvo fuente oficial, tier 0):
    # el titular nombra al club o a un jugador de la plantilla.
    if (n["tier"] != 0 and not any(c in n["titulo"].lower() for c in F.PALABRAS_CLUB)
            and not _nombra_jugador(n["titulo"])):
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


def _limpia_titulo(titulo, url_feed):
    # Google News añade " - Medio" al final del título. En los RSS directos no se
    # toca: 'Barça - Madrid: ...' partiría el titular.
    if "news.google.com" in url_feed and " - " in titulo:
        cuerpo, medio = titulo.rsplit(" - ", 1)
        return cuerpo.strip(), medio.strip()
    return titulo.strip(), ""


def _fecha_iso(entrada):
    for campo in ("published_parsed", "updated_parsed"):
        val = entrada.get(campo)
        if val:
            return dt.datetime(*val[:6]).isoformat()
    return _ahora().isoformat()


# ---------------------------------------------------------------------------
# Recolección
# ---------------------------------------------------------------------------
# Rendimiento de cada fuente en esta ejecución (va a la línea RESUMEN del log).
ESTADISTICAS = {}


def recolectar_feed(nombre, tier_forzado, url):
    """tier_forzado=int -> todas las noticias son de ese medio/tier (búsqueda por medio).
       tier_forzado=None -> se deduce el medio y el tier de cada noticia."""
    noticias = []
    try:
        feed = feedparser.parse(_descargar(url))
    except Exception as e:
        print(f"  [ERROR] {nombre}: {repr(e)[:150]}")
        ESTADISTICAS[nombre] = {"error": repr(e)[:80]}
        return noticias

    filtro_enlace = F.FILTRO_ENLACE.get(nombre)
    for entrada in feed.entries:
        titulo_bruto = entrada.get("title", "").strip()
        if not titulo_bruto:
            continue
        enlace = entrada.get("link", "")
        if filtro_enlace and filtro_enlace not in enlace:
            continue   # feed mixto: solo la sección indicada (p.ej. /noticias/barca/)
        resumen = re.sub("<[^>]+>", " ", entrada.get("summary", ""))
        texto = titulo_bruto + " " + resumen

        if not _es_relevante(texto):
            continue
        if not _apto_feed_general(nombre, titulo_bruto):
            continue
        categoria = _clasificar(texto)
        if categoria is None:      # cantera inferior o renovación del Atlètic -> fuera
            continue

        titulo, medio_en_titulo = _limpia_titulo(titulo_bruto, url)

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
            "categoria": categoria,
            "estado": _estado(texto),
            "fecha": _fecha_iso(entrada),
            "fuente_feed": nombre,
            "visto_por_primera_vez": _ahora().isoformat(),
        })
    print(f"  {nombre}: {len(noticias)} relevantes (de {len(feed.entries)} entradas)")
    ESTADISTICAS[nombre] = {"entradas": len(feed.entries), "relevantes": len(noticias)}
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
    """Guarda el JSON. Si solo cambiaría la hora de 'actualizado', no lo reescribe
    (así el workflow no hace un commit en cada ejecución). Devuelve True si guardó."""
    os.makedirs("docs", exist_ok=True)
    salida = {
        "actualizado": _ahora().isoformat() + "Z",
        "total": len(noticias),
        "cerradas": sorted(cerradas),          # operaciones oficiales (no re-alertar por jugador)
        "alertadas": sorted(alertadas)[-5000:],  # ids ya avisados (tope para no crecer sin fin)
        "noticias": noticias,
    }
    try:
        with open(RUTA_DATOS, "r", encoding="utf-8") as f:
            previo = json.load(f)
        previo.pop("actualizado", None)
        if previo == {k: v for k, v in salida.items() if k != "actualizado"}:
            return False
    except Exception:
        pass   # no existe o está corrupto -> se escribe
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    return True


def main():
    print("== Recolector de fichajes FC Barcelona ==")
    noticias_previas, cerradas, alertadas = cargar_datos()
    # Claves de 'cerradas' que en realidad son clubes ('aston villa'): bloquearían
    # cualquier alerta futura cuyo "jugador" se extraiga igual.
    cerradas = {c for c in cerradas
                if not any(p in analisis.NO_JUGADOR for p in c.split())}
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

    # Protección: si TODAS las fuentes fallaron (rate-limit/503), no tocar nada.
    if not recolectadas:
        print("Todas las fuentes fallaron (posible rate-limit de Google News). "
              "Se conserva lo anterior y no se envía nada.")
        _resumen(nuevas=0, guardadas=len(existentes), alertas=0, guardado=False)
        return

    nuevas = []
    for n in recolectadas:
        if n["id"] not in existentes:
            existentes[n["id"]] = n
            nuevas.append(n)

    limite = _ahora() - dt.timedelta(days=ANTIGUEDAD_DIAS)
    todas = []
    for n in existentes.values():
        try:
            f = dt.datetime.fromisoformat(n["fecha"].replace("Z", ""))
        except Exception:
            f = _ahora()
        if f >= limite:
            todas.append((f, n))
    todas.sort(key=lambda x: x[0], reverse=True)
    # Limpieza retroactiva: descarta lo ya guardado que ya no encaja con los filtros.
    todas = [n for _, n in todas if _valida_por_titulo(n["titulo"])
             and _apto_feed_general(n.get("fuente_feed"), n["titulo"])][:MAX_NOTICIAS]

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

    alertas_enviadas = 0
    if arranque_en_frio:
        for n, _ in enviables:
            alertadas.add(n["id"])   # tras un reinicio: se registran pero NO se envían
        print(f"Arranque en frío: se omiten {len(enviables)} alertas (evita ráfaga).")
    else:
        lote = enviables[:MAX_ALERTAS_POR_EJECUCION]
        if len(enviables) > MAX_ALERTAS_POR_EJECUCION:
            print(f"AVISO: {len(enviables)} candidatas; se envían {MAX_ALERTAS_POR_EJECUCION} "
                  f"(el resto, en próximas ejecuciones).")
        if lote:
            print(f"Enviando {len(lote)} alertas a Telegram…")
            # Solo se registran las que Telegram aceptó (o rechazó para siempre):
            # si falla la red o hay rate-limit, se reintentan en la próxima ejecución.
            consumidas = telegram_alertas.enviar_alertas([n for n, _ in lote])
            for n, clave in lote:
                if n["id"] not in consumidas:
                    continue
                alertadas.add(n["id"])
                if n["estado"] in ESTADOS_CIERRE and clave:
                    cerradas.add(clave)  # ese jugador queda cerrado para Telegram
            alertas_enviadas = len(consumidas)

    guardado = guardar(todas, cerradas, alertadas)
    # 'nuevas' solo cuenta las que llegan a guardarse (las de >30 días o que ya no
    # pasan los filtros reaparecen en cada ejecución y no son novedad).
    ids_guardadas = {n["id"] for n in todas}
    nuevas = [n for n in nuevas if n["id"] in ids_guardadas]
    print(f"Noticias nuevas: {len(nuevas)} · Total guardadas: {len(todas)}"
          + ("" if guardado else " · Sin cambios (JSON intacto)"))
    _resumen(nuevas=len(nuevas), guardadas=len(todas), alertas=alertas_enviadas,
             guardado=guardado)


def _resumen(**datos):
    """Línea RESUMEN en JSON (una por ejecución) para analizar patrones desde los logs
    de Actions (herramientas/informe_ejecuciones.py). En Actions, también una tabla en
    la página de la ejecución."""
    datos["fuentes"] = ESTADISTICAS
    print("RESUMEN " + json.dumps(datos, ensure_ascii=False))
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if not ruta:
        return
    filas = []
    for fuente, e in ESTADISTICAS.items():
        estado = e["error"] if "error" in e else f'{e["relevantes"]} de {e["entradas"]}'
        filas.append(f"| {fuente} | {estado} |")
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(f"### Fichajes: {datos['nuevas']} nuevas · {datos['alertas']} alertas · "
                f"{datos['guardadas']} guardadas\n\n| Fuente | Relevantes |\n|---|---|\n"
                + "\n".join(filas) + "\n")


if __name__ == "__main__":
    main()
