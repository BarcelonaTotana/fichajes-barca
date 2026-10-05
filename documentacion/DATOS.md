# Datos

## `docs/fichajes.json`

Lo escribe el bot y lo lee la web. Se reescribe solo si cambia algo más que `actualizado`.

```json
{
  "actualizado": "2026-10-05T09:20:39.123456Z",
  "total": 193,
  "cerradas": ["gabriel jesus", "ter stegen"],
  "alertadas": ["0a1b2c3d4e5f6a7b"],
  "noticias": [ { ... } ]
}
```

| Campo | Significado |
|---|---|
| `actualizado` | Última escritura (UTC). |
| `total` | Nº de noticias guardadas. |
| `cerradas` | Claves de jugador (minúsculas, sin acentos) con operación oficial / here we go ya avisada. No se vuelve a avisar de ellos. |
| `alertadas` | Ids ya enviados (o descartados) por Telegram. Tope 5000. |
| `noticias` | Lista, de la más reciente a la más antigua. |

### Cada noticia

| Campo | Ejemplo | Notas |
|---|---|---|
| `id` | `"9f2c…"` | sha1 (16 hex) del título sin acentos, puntuación ni mayúsculas. |
| `titulo` | `"Bierhoff coloca a Florian Wirtz en el Barça"` | En Google News, sin el " - Medio" final. |
| `enlace` | URL | De Google News es un enlace de redirección. |
| `medio` | `"mundodeportivo.com"` | Nombre del medio o dominio. |
| `tier` / `tier_etiqueta` | `2` / `"Bastante fiable"` | 0 OFICIAL · 1 Fiable · 2 Bastante fiable · 3 Verificar · 4 Poco fiable · 5 Ruido. |
| `categoria` | `"primer_equipo"` | o `"barca_atletic"`. |
| `estado` | `"rumor"` | `oficial`, `here_we_go`, `avanzado`, `rumor`. |
| `fecha` | `"2026-10-05T08:27:24"` | Publicación según el feed (UTC). Si no viene, la de primera vista. |
| `fuente_feed` | `"SPORT · Barça"` | Nombre del feed en `fuentes.py` que la trajo. |
| `visto_por_primera_vez` | ISO UTC | Cuándo la vio el bot por primera vez. |

`visto_por_primera_vez - fecha` = retraso del bot respecto a la publicación (útil para medir).

## Línea `RESUMEN` (log de cada ejecución)

Al final del paso "Ejecutar recolector":

```
RESUMEN {"nuevas": 2, "guardadas": 193, "alertas": 0, "guardado": true,
         "fuentes": {"SPORT · Barça": {"entradas": 50, "relevantes": 2},
                     "RAC1": {"error": "HTTPError('503 rate-limit')"}}}
```

- `nuevas`: noticias nuevas que se han guardado (no cuenta las de más de 30 días que
  reaparecen en los feeds).
- `alertas`: mensajes de Telegram aceptados en esta ejecución.
- `guardado`: si hubo cambios → commit.
- `fuentes`: por feed, entradas descargadas y relevantes, o el error.

`herramientas/informe_ejecuciones.py [N]` agrega estas líneas de las últimas N ejecuciones.
La misma información sale como tabla en la página de cada ejecución de Actions.
Las ejecuciones anteriores al 2026-10-05 no tienen esta línea.

## Dónde más hay datos

- **Historial de git** de `docs/fichajes.json`: un commit por cambio → evolución de noticias,
  `alertadas` (≈ alertas enviadas por día) y `cerradas`.
- **Logs de Actions**: GitHub los guarda 90 días.
