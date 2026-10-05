# Fuentes

Configuración en `bot/fuentes.py`. Medición del 2026-10-05 (una ejecución local + logs de
las 300 ejecuciones anteriores). Actualiza esta tabla cuando cambie algo.

## Activas

| Feed | Tipo | Entradas | Relevantes | Estado / notas |
|---|---|---|---|---|
| Mundo Deportivo · Barça | RSS sección Barça | 100 | ~11–16 | **La fuente principal**: el 93 % de lo guardado (188 de 203). |
| Mundo Deportivo · Fichajes | RSS mercado general | 100 | ~1–3 | Exige Barça en el titular. Mucho ruido de otros clubes. |
| SPORT · Barça | RSS últimas noticias + filtro `/noticias/barca/` | 50 | ~2 | Nuevo (2026-10-05). El RSS `/rss/barca/` de SPORT sale vacío. |
| SPORT · Fútbol | RSS fútbol general | ~49 | 0 | Exige Barça en el titular. Aporta poco; candidato a quitar si sigue en 0. |
| FC Barcelona (oficial) | Google News `site:fcbarcelona.com` | 100 | 0 | Casi todo es tienda, peñas y entradas. Las 11 "oficiales" guardadas eran ruido (ya filtrado). Útil en mercado (anuncios oficiales). |
| RAC1 | Google News `site:rac1.cat` | 2 | 0 | Google News apenas indexa rac1.cat. Prácticamente muerta. |
| Barça Atlètic | Google News búsqueda | ~65 | 0 | 3 noticias en 30 días. Fuera de mercado casi no hay nada. |

## Incidencias conocidas

- **SPORT 406 "WAF Forbidden"**: el cortafuegos rechaza User-Agents que no parecen de
  navegador (también desde casa, no es la IP de GitHub). Se arregló el 2026-10-05 con un
  User-Agent de Chrome. Si vuelve, probar `curl -A "<UA de navegador>" <url>`.
- **Google News 503 rate-limit**: puntual (~15 % de ejecuciones en algún feed de Google News).
  Se reintenta 3 veces; si persiste, se pierde ese feed solo en esa ejecución. Normal.
- **Transfermarkt**: bloquea con 403 (Cloudflare) las IPs de Actions. Descartado (HISTORIAL §0-TER).
- **Relevo, The Athletic, ccma.cat**: 0 resultados en Google News ES. No se usan.

## Tiers (fiabilidad)

Orden de decisión: dominio del enlace (`TIER_POR_DOMINIO`) → nombre del medio en el título de
Google News (`TIER_POR_NOMBRE`, palabra completa) → por defecto 3. Si el texto cita a un
periodista de `PERIODISTAS_TIER` con mejor tier, se usa ese. En las búsquedas por medio
(`BUSQUEDAS_POR_MEDIO`) el tier es fijo.

Telegram solo usa tier ≤ 2 (`TIER_ALERTA` en `recolector.py`).

## Cómo probar una fuente nueva

1. ¿Responde y qué trae?
   ```bash
   python -c "import feedparser; from bot import recolector as R; f=feedparser.parse(R._descargar('URL')); print(len(f.entries)); [print(e.title, e.link) for e in f.entries[:15]]"
   ```
   (en este PC, anteponer `SSL_NO_VERIFY=1`)
2. ¿Cuántas pasarían el filtro?
   ```bash
   python -c "import feedparser; from bot import recolector as R; f=feedparser.parse(R._descargar('URL')); print([e.title for e in f.entries if R._es_relevante(e.title+' '+e.get('summary',''))])"
   ```
3. Añadir a `BUSQUEDAS_GENERALES` como `("Nombre", None, "auto", URL)`. Si es un feed de todo
   el fútbol, añadir el nombre a `FEEDS_BARSA_EN_TITULO`; si mezcla secciones, a `FILTRO_ENLACE`.
4. Si el dominio es nuevo, darle tier en `TIER_POR_DOMINIO`.
5. Probar en una copia (ver CLAUDE.md) y revisar las noticias nuevas antes de subir: en la
   primera ejecución puede mandar a Telegram hasta 10 alertas atrasadas de esa fuente.
