# -*- coding: utf-8 -*-
"""
Análisis simple de una noticia de fichaje para construir la alerta de Telegram:
- extraer_jugador: nombre propio protagonista (heurística; el club/entidades se filtran).
- direccion: "al Barça" / "sale del Barça" / "(cesión)" / "renueva con el Barça".
- extraer_importe: cifra del traspaso (150M, 20 millones…).
- probabilidad: % estimado a partir del estado + la fiabilidad de la fuente.
- clave_operacion: clave normalizada (por jugador) para no repetir alertas de operaciones cerradas.

Todo son heurísticas sencillas a propósito (sin IA, gratis en GitHub Actions).
"""
import re
import unicodedata

# Palabras que NO son jugadores (clubes, entidades, cargos, comunes) -> se filtran.
NO_JUGADOR = {
    "barça", "barca", "barcelona", "fc", "fc barcelona", "barsa", "atlètic", "atletic",
    "real", "madrid", "atlético", "atletico", "psg", "manchester", "city", "united",
    "chelsea", "arsenal", "liverpool", "bayern", "múnich", "munich", "dortmund",
    "juventus", "inter", "milan", "milán", "napoli", "roma", "lazio", "sevilla",
    "valencia", "betis", "villarreal", "girona", "espanyol", "athletic", "bilbao",
    "lyngby", "boldklub", "borussia", "leipzig", "mónaco", "monaco", "porto", "benfica",
    "la masia", "masia", "masía", "deco", "flick", "hansi", "laporta", "xavi", "yamal",
    "la liga", "laliga", "champions", "europa league", "mundial", "premier",
    "mundo", "deportivo", "sport", "relevo", "cadena", "ser", "ara", "rac1", "the athletic",
    "el", "la", "los", "las", "un", "una", "del", "al", "según", "oficial",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
}

_MAY = "A-ZÁÉÍÓÚÜÑÀÈÌÒÙÇ"
_MIN = "a-záéíóúüñàèìòùç"
# Secuencia de 2+ palabras Capitalizadas (posible nombre propio).
_RE_NOMBRE = re.compile(rf"\b[{_MAY}][{_MIN}]+(?:\s+[{_MAY}][{_MIN}]+)+\b")


def _sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def extraer_jugador(titulo):
    """Devuelve el nombre propio protagonista, o None si no se identifica con claridad."""
    for cand in _RE_NOMBRE.findall(titulo):
        palabras = cand.lower().split()
        # Descarta si alguna palabra está en la lista de no-jugadores.
        if any(p in NO_JUGADOR for p in palabras):
            continue
        return cand
    return None


def clave_operacion(jugador):
    """Clave normalizada (sin acentos, minúsculas) para deduplicar por jugador."""
    if not jugador:
        return None
    return _sin_acentos(jugador).lower().strip()


def direccion(texto):
    t = texto.lower()
    if "renov" in t or "renueva" in t:
        return "renueva con el Barça"
    if "cedido" in t or "cesión" in t or "cesion" in t or "préstamo" in t or "prestamo" in t:
        return "(cesión)"
    if any(w in t for w in ["vende", "venta", "traspaso de", "sale del", "deja el barça", "adiós"]):
        return "sale del Barça"
    return "al Barça"


def extraer_importe(texto):
    """Busca la cifra del traspaso. Devuelve p.ej. '150M', '20M', o None."""
    m = re.search(r"(\d[\d.,]*\d|\d)\s*(?:millones|m euros|kilos|m€|m\b)", texto, re.I)
    if m:
        return m.group(1) + "M"
    return None


ESTADO_LEGIBLE = {"oficial": "Oficial", "here_we_go": "Acuerdo total",
                  "avanzado": "Avanzado", "rumor": "Rumor"}
ESTADO_EMOJI = {"oficial": "✅", "here_we_go": "🤝", "avanzado": "🔜", "rumor": "💬"}


def probabilidad(estado, tier):
    """% estimado simple a partir del estado y la fiabilidad de la fuente."""
    if estado == "oficial":
        return 100
    if estado == "here_we_go":
        return 92
    if estado == "avanzado":
        return {0: 85, 1: 80, 2: 70}.get(tier, 60)
    # rumor
    return {0: 65, 1: 60, 2: 45}.get(tier, 35)
