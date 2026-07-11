# -*- coding: utf-8 -*-
"""
Configuración de fuentes del monitor de fichajes del FC Barcelona.

Estrategia 100% gratuita:
- Usamos Google News RSS con búsquedas (agrega TODOS los medios, formato estable).
- Añadimos algún RSS directo de medios clave.
- Cada noticia se PONDERA por el "tier" (fiabilidad) del medio del que procede.

La clasificación de tiers se basa en la guía comunitaria de fiabilidad de medios
del Barça (ver Memoria.md, sección 4.1). Es una heurística: el panel muestra el
tier de cada noticia para que el usuario juzgue.
"""

# ---------------------------------------------------------------------------
# 1. BÚSQUEDAS EN GOOGLE NEWS (RSS). hl=idioma, gl=país, ceid=edición.
#    Devuelven noticias de muchísimos medios en formato RSS estándar.
# ---------------------------------------------------------------------------
def _google_news(consulta):
    from urllib.parse import quote
    return f"https://news.google.com/rss/search?q={quote(consulta)}&hl=es&gl=ES&ceid=ES:es"


BUSQUEDAS_GOOGLE_NEWS = [
    # categoria "primer_equipo" o "cantera" para clasificar de origen
    ("Barça fichaje primer equipo", "primer_equipo",
     _google_news('(Barça OR Barcelona) (fichaje OR fichajes OR traspaso OR cesión OR '
                  'renovación OR acuerdo OR oferta OR firma) -femenino -baloncesto when:7d')),

    ("Barça salidas y renovaciones", "primer_equipo",
     _google_news('(Barça OR "FC Barcelona") (renueva OR vende OR negocia OR "aquí vamos" OR '
                  '"here we go" OR oficial) -femenino -baloncesto when:7d')),

    ("Barça cantera / La Masia fichajes", "cantera",
     _google_news('(Barça OR Barcelona) (Masia OR canterano OR juvenil OR "Barça Atlètic" OR '
                  'filial OR cadete OR infantil) (fichaje OR ficha OR promesa) '
                  '-femenino -baloncesto when:14d')),
]

# ---------------------------------------------------------------------------
# 2. RSS DIRECTOS de medios clave (se validan al ejecutar; si uno falla, se ignora).
#    Google News ya agrega SPORT, MD, etc., así que de momento no hacen falta.
#    Si encontramos un feed oficial estable del club, lo añadimos aquí.
# ---------------------------------------------------------------------------
RSS_DIRECTOS = []

# ---------------------------------------------------------------------------
# 3. TIER (fiabilidad) por dominio del medio.
#    0 = oficial (máxima) · 1 = fiable · 2 = bastante fiable · 3 = verificar ·
#    4 = poco fiable · 5 = ruido/clickbait. Desconocido -> 3 por defecto.
# ---------------------------------------------------------------------------
TIER_POR_DOMINIO = {
    "fcbarcelona.com": 0,
    "fcbarcelona.cat": 0,

    "relevo.com": 1,          # Matteo Moretto
    "theathletic.com": 1,     # David Ornstein
    "nytimes.com": 1,
    "rac1.cat": 1,            # Marta Ramon
    "rac1.com": 1,
    "ccma.cat": 1,            # Catalunya Ràdio / Xavi Campos

    "sport.es": 2,           # Carlos Monfort (Tier1) en medio grande -> 2
    "mundodeportivo.com": 2, # Fernando Polo (Tier1) en medio grande -> 2
    "ara.cat": 2,
    "cadenaser.com": 2,
    "tv3.cat": 2,

    "elnacional.cat": 3,
    "jijantes.com": 3,       # Gerard Romero: mucho volumen, baja precisión
    "gazzetta.it": 3,
    "goal.com": 3,

    "marca.com": 4,
    "lasexta.com": 4,
    "beinsports.com": 4,

    "as.com": 5,
    "bild.de": 5,
    "thesun.co.uk": 5,
    "dailymail.co.uk": 5,
    "elchiringuitotv.com": 5,
    "donbalon.com": 5,
}
TIER_POR_DEFECTO = 3

# Tier por NOMBRE de medio (como aparece en Google News, p. ej. "SPORT",
# "Mundo Deportivo", "Fichajes.com"). Se comprueba en orden: el primero que
# encaje como subcadena del nombre del medio gana. Pon los nombres más
# específicos ANTES que los genéricos (p. ej. "sports illustrated" antes que "sport").
TIER_POR_NOMBRE = [
    ("fc barcelona", 0),
    ("barça oficial", 0),

    ("relevo", 1),
    ("the athletic", 1),
    ("rac1", 1),
    ("catalunya ràdio", 1),
    ("catalunya radio", 1),
    ("catradio", 1),

    ("sports illustrated", 3),
    ("sport.es", 2),
    ("sport", 2),
    ("mundo deportivo", 2),
    ("cadena ser", 2),
    ("ara", 2),

    ("el nacional", 3),
    ("crónica global", 3),
    ("cronica global", 3),
    ("goal", 3),
    ("onefootball", 3),
    ("besoccer", 3),
    ("segre", 3),

    ("marca", 4),
    ("tribuna", 4),
    ("la sexta", 4),

    ("diario as", 5),
    ("fichajes", 5),     # fichajes.com / .net -> clickbait
    ("don balón", 5),
    ("don balon", 5),
    ("el chiringuito", 5),
    ("bild", 5),
    ("the sun", 5),
    ("daily mail", 5),
]

# Etiqueta legible por tier
ETIQUETA_TIER = {
    0: "OFICIAL",
    1: "Fiable",
    2: "Bastante fiable",
    3: "Verificar",
    4: "Poco fiable",
    5: "Ruido / clickbait",
}

# ---------------------------------------------------------------------------
# 4. ESTADO del fichaje según palabras clave (de menor a mayor certeza).
# ---------------------------------------------------------------------------
PALABRAS_ESTADO = [
    ("oficial",   ["oficial", "hecho oficial", "confirma el fichaje", "presentación"]),
    ("here_we_go", ["here we go", "aquí vamos", "acuerdo total", "acuerdo cerrado", "todo cerrado"]),
    ("avanzado",  ["acuerdo", "principio de acuerdo", "negociación avanzada", "cerca de", "reunión"]),
    ("rumor",     ["interés", "sondeo", "gusta", "podría", "suena", "en la agenda", "objetivo"]),
]
ESTADO_POR_DEFECTO = "rumor"

# Palabras que indican categoría inferior (si aparecen, es cantera).
PALABRAS_CANTERA = [
    "masia", "masía", "canterano", "cantera", "juvenil", "filial", "barça atlètic",
    "barca atletic", "atlètic", "cadete", "infantil", "alevín", "sub-19", "sub19",
    "sub-17", "juvenil a", "juvenil b", "promesa",
]

# Filtro de ruido: descartar si aparece alguna de estas (otras secciones).
PALABRAS_DESCARTE = [
    "femenino", "femení", "baloncesto", "basket", "bàsquet", "balonmano",
    "hockey", "futsal", "fútbol sala",
]
