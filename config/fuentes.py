# -*- coding: utf-8 -*-
"""
Configuración de fuentes del monitor de fichajes del FC Barcelona.

Estrategia 100% gratuita, con clasificación mejorada:
- BÚSQUEDAS POR MEDIO FIABLE (site:relevo.com, sport.es…): sabemos con certeza
  de qué medio viene cada noticia -> tier real, no "Verificar".
- BÚSQUEDAS GENERALES (Google News): capturan todo lo demás; el tier se decide por
  el medio y, sobre todo, por el PERIODISTA citado en el texto.
- FILTRO DE RELEVANCIA: descarta lo que no es un fichaje del Barça (ruido).
- CANTERA por contenido: solo si hay una palabra de cantera de peso.

Ver Memoria.md, sección 4, para el contexto de la fiabilidad de cada fuente.
"""
from urllib.parse import quote


def _google_news(consulta):
    return f"https://news.google.com/rss/search?q={quote(consulta)}&hl=es&gl=ES&ceid=ES:es"


# Núcleo de la consulta: términos de fichaje. Se reutiliza en todas las búsquedas.
_FICHAJE = ('(fichaje OR fichajes OR traspaso OR cesión OR cedido OR renovación OR '
            'renueva OR acuerdo OR oferta OR firma OR fichar OR vende OR venta OR '
            'salida OR negocia OR refuerzo OR cláusula OR presentación OR oficial)')

# ---------------------------------------------------------------------------
# 1. BÚSQUEDAS POR MEDIO FIABLE (tier y medio GARANTIZADOS).
#    Formato: (medio, tier, categoria_hint, url)
# ---------------------------------------------------------------------------
def _feed_medio(medio, tier, dominio):
    # OJO: la consulta debe ser SIMPLE. Si se le añade el gran grupo de sinónimos
    # de fichaje, Google News IGNORA el operador site: y devuelve resultados generales.
    # Por eso aquí solo pedimos "Barça site:DOMINIO"; el filtro de relevancia
    # (_es_relevante) ya se encarga de quedarse solo con lo que es fichaje.
    url = _google_news(f'(Barça OR Barcelona) site:{dominio} when:30d')
    return (medio, tier, "auto", url)


# Solo medios que Google News (edición ES) indexa de verdad. Relevo, The Athletic
# y ccma.cat devuelven 0 resultados, así que no se incluyen (no aportan nada).
BUSQUEDAS_POR_MEDIO = [
    _feed_medio("RAC1", 1, "rac1.cat"),
    _feed_medio("SPORT", 2, "sport.es"),
    _feed_medio("Mundo Deportivo", 2, "mundodeportivo.com"),
    _feed_medio("Diari ARA", 2, "ara.cat"),
    _feed_medio("Cadena SER", 2, "cadenaser.com"),
    _feed_medio("FC Barcelona (oficial)", 0, "fcbarcelona.com"),
]

# ---------------------------------------------------------------------------
# 2. BÚSQUEDAS GENERALES (tier por medio + periodista).
#    Formato: (nombre, tier_forzado=None, categoria_hint, url)
# ---------------------------------------------------------------------------
BUSQUEDAS_GENERALES = [
    ("General primer equipo", None, "auto",
     _google_news(f'(Barça OR "FC Barcelona") {_FICHAJE} -femenino -baloncesto when:10d')),

    ("Cantera / La Masia", None, "auto",
     _google_news('(Barça OR Barcelona) (Masia OR canterano OR "Barça Atlètic" OR filial OR '
                  'juvenil OR cadete) ' + _FICHAJE + ' -femenino -baloncesto when:21d')),
]

# ---------------------------------------------------------------------------
# 3. TIER por dominio (para RSS directos, si algún día se usan).
# ---------------------------------------------------------------------------
TIER_POR_DOMINIO = {
    "fcbarcelona.com": 0, "fcbarcelona.cat": 0,
    "relevo.com": 1, "theathletic.com": 1, "rac1.cat": 1, "ccma.cat": 1,
    "sport.es": 2, "mundodeportivo.com": 2, "ara.cat": 2, "cadenaser.com": 2,
    "elnacional.cat": 3, "goal.com": 3,
    "marca.com": 4,
    "as.com": 5, "bild.de": 5, "thesun.co.uk": 5, "dailymail.co.uk": 5,
}
TIER_POR_DEFECTO = 3

# ---------------------------------------------------------------------------
# 4. TIER por NOMBRE de medio (como aparece en Google News). Palabra completa.
# ---------------------------------------------------------------------------
TIER_POR_NOMBRE = [
    ("fc barcelona", 0),
    ("relevo", 1), ("the athletic", 1), ("rac1", 1), ("catalunya ràdio", 1), ("catradio", 1),
    ("sports illustrated", 3),
    ("sport.es", 2), ("sport", 2), ("mundo deportivo", 2), ("cadena ser", 2), ("diari ara", 2),
    ("el nacional", 3), ("crónica global", 3), ("cronica global", 3), ("goal", 3),
    ("onefootball", 3), ("besoccer", 3), ("segre", 3), ("infobae", 3), ("tudn", 3),
    ("marca", 4), ("tribuna", 4), ("la sexta", 4), ("bein", 4),
    ("diario as", 5), ("fichajes", 5), ("don balón", 5), ("don balon", 5),
    ("el chiringuito", 5), ("chiringuito", 5), ("bild", 5), ("the sun", 5), ("daily mail", 5),
]

# ---------------------------------------------------------------------------
# 5. PERIODISTAS: si el texto cita a uno, se usa su tier (el mejor, nº más bajo).
#    Esto rescata scoops fiables aunque los publique un medio menor.
# ---------------------------------------------------------------------------
PERIODISTAS_TIER = [
    ("fabrizio romano", 1), ("matteo moretto", 1), ("moretto", 1),
    ("david ornstein", 1), ("ornstein", 1), ("carlos monfort", 1), ("monfort", 1),
    ("fernando polo", 1), ("marta ramon", 1), ("xavi campos", 1),
    ("gerard romero", 3), ("di marzio", 3),
    ("guillem balagué", 4), ("balague", 4),
    ("pedrerol", 5), ("nicolò schira", 5), ("schira", 5),
]

# Etiqueta legible por tier
ETIQUETA_TIER = {0: "OFICIAL", 1: "Fiable", 2: "Bastante fiable",
                 3: "Verificar", 4: "Poco fiable", 5: "Ruido / clickbait"}

# ---------------------------------------------------------------------------
# 6. ESTADO del fichaje según palabras clave (de mayor a menor certeza).
# ---------------------------------------------------------------------------
PALABRAS_ESTADO = [
    ("oficial",    ["oficial", "hecho oficial", "confirma el fichaje", "presentación", "presenta a"]),
    ("here_we_go", ["here we go", "aquí vamos", "acuerdo total", "acuerdo cerrado", "todo cerrado", "acuerdo definitivo"]),
    ("avanzado",   ["acuerdo", "principio de acuerdo", "negociación avanzada", "cerca de", "reunión", "pacto"]),
    ("rumor",      ["interés", "sondeo", "gusta", "podría", "suena", "en la agenda", "objetivo", "seguimiento"]),
]
ESTADO_POR_DEFECTO = "rumor"

# ---------------------------------------------------------------------------
# 7. RELEVANCIA: una noticia se queda solo si (habla del Barça) Y (es de fichajes)
#    Y (no contiene ninguna palabra de bloqueo).
# ---------------------------------------------------------------------------
PALABRAS_BARSA = ["barça", "barsa", "barcelona", "culé", "cule", "blaugrana",
                  "azulgrana", "la masia", "masia", "masía", "barça atlètic"]

PALABRAS_FICHAJE = ["fichaje", "fichajes", "ficha ", "fichar", "fichado", "traspaso",
                    "cesión", "cesion", "cedido", "cede ", "préstamo", "prestamo",
                    "renueva", "renovación", "renovacion", "acuerdo", "oferta", "firma",
                    "firmar", "vende", "venta ", "salida", "negocia", "negociación",
                    "refuerzo", "contrato", "cláusula", "clausula", "presentación",
                    "presenta a", "llega al", "aterriza", "desembolsa"]

# Si aparece alguna de estas, se descarta (otras secciones / no fútbol / otros clubes).
PALABRAS_BLOQUEO = [
    "femenino", "femení", "baloncesto", "basket", "bàsquet", "balonmano", "hockey",
    "futsal", "fútbol sala", "waterpolo", "rugby", "nba", "tenis",
    "circuit", "circuito", "ajuntament", "ayuntamiento", "fórmula 1", "formula 1",
    "motogp", "moto gp", "como ceo", "nuevo ceo", "elecciones", "eurolliga", "euroliga",
    "presupuesto municipal",
    # merchandising de la tienda oficial (se colaba como tier 0)
    "camiseta", "official store", "megastore", "sudadera", "bufanda", "firmada por",
    "summer camp", "summer cump",
    # fútbol femenino (el proyecto es masculino) y ruido ciudad/política
    "femen", "women", "womens", "wsl", "liga f", "uwcl",
    "área metropolitana", "metropolitana", "alcalde", "generalitat",
    # análisis / retrospectivas / partidos (no son movimientos de mercado)
    "1x1", "uno a uno", "cómo han rendido", "han rendido", "siguiendo el partido",
    "amistoso", "pretemporada", "resumen del partido",
    # ruido de Barcelona-ciudad (tiempo, tráfico…)
    "meteocat", "ola de calor", "lluvias", "temperaturas", "previsión del tiempo",
]

# Señal de que la noticia es del CLUB (no de la ciudad de Barcelona). Para Telegram
# se exige una de estas en el titular (salvo fuente oficial, tier 0, que ya es del club).
PALABRAS_CLUB = ["barça", "barsa", "blaugrana", "azulgrana", "culé", "cule", "fc barcelona"]

# ---------------------------------------------------------------------------
# 9. MOVIMIENTO: para avisar por Telegram, el titular debe contener una señal
#    real de movimiento o interés (no basta con la palabra "fichajes").
#    Esto separa los movimientos/rumores de los análisis retrospectivos.
# ---------------------------------------------------------------------------
PALABRAS_MOVIMIENTO = [
    "ficha", "fichará", "fichar", "firma", "firmará", "renueva", "renovará", "renovación",
    "cede", "cedido", "cesión", "cesion", "traspaso", "traspasa", "vende", "venderá",
    "acuerdo", "oferta", "oficial", "presenta", "rescinde", "rescisión", "aterriza",
    "se marcha", "adiós", "negocia", "quiere", "interesa", "gusta", "sigue a", "sondea",
    "puja", "va a por", "apuesta por", "en la agenda", "objetivo", "pretende", "ofrece",
    "cláusula", "clausula", "llega al", "cierra el fichaje", "cierra la",
]

# ---------------------------------------------------------------------------
# 10. FÚTBOL FEMENINO: el proyecto es MASCULINO. Se descarta todo lo femenino,
#     tanto en la web como en Telegram. Marcas + nombres de jugadoras del Barça
#     Femení (para cazar las noticias que no dicen "femenino" explícitamente).
# ---------------------------------------------------------------------------
MARCAS_FEMENINO = ["femen", "femení", "women", "womens", "wsl", "liga f",
                   "uwcl", "champions femenina", "barça femen"]

JUGADORAS_FEMENINO = [
    "aitana", "bonmatí", "bonmati", "alexia", "putellas", "paralluelo", "salma",
    "guijarro", "patri guijarro", "mapi león", "mapi leon", "ona batlle", "cata coll",
    "fridolina", "rolfö", "rolfo", "ewa pajor", "claudia pina", "vicky lópez",
    "vicky lopez", "torrejón", "torrejon", "graham hansen", "kika nazareth",
    "ainoa gómez", "ainoa gomez", "brugts", "engen", "schertenleib", "caroline graham",
    "jana fernández", "alba caño", "clàudia pina",
]


# ---------------------------------------------------------------------------
# 8. CANTERA: solo si aparece una palabra de cantera DE PESO (no de pasada).
# ---------------------------------------------------------------------------
PALABRAS_CANTERA = [
    "masia", "masía", "la masia", "barça atlètic", "barça b", "filial",
    "juvenil", "cadete", "infantil", "alevín", "alevin", "canterano", "cantera",
    "sub-19", "sub19", "sub-17", "sub17", "sub-16", "sub-14", "juvenil a", "juvenil b",
]
