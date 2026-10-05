# Patrones de funcionamiento

Lo que se ha observado en producción: sirve para distinguir lo normal de un fallo.
Añadir una entrada con fecha cada vez que se mida algo nuevo
(`python herramientas/informe_ejecuciones.py 300`).

## Ritmo normal (medido el 2026-10-05, fuera de mercado)

| Métrica | Valor normal | Alarma si… |
|---|---|---|
| Ejecuciones | 1 cada 10 min (≈144/día), `workflow_dispatch` de cron-job.org; algún `schedule` suelto | pasan >30 min sin ejecuciones |
| Resultado | 300 de 300 `success` | aparece alguna `failure` |
| Commits del bot | irregulares, solo con novedades (5–34/día, mediana ≈14) | uno cada 10 min (vuelven los commits vacíos) |
| Noticias guardadas | ~200 en 30 días | baja de 100 o se dispara de 400 |
| Alertas Telegram | ~1/día (24 entre el 9-sep y el 2-oct) | 0 durante el mercado de invierno |
| Rate-limit Google News | ~6 de 40 ejecuciones con algún 503 | todas las fuentes de Google News fallan seguidas |

En mercado (enero, julio–agosto) hay que volver a medir: se esperan muchas más noticias y alertas.

## Reparto de lo guardado (2026-10-05, 203 noticias)

- Por fuente: MD · Barça 188 · oficial 11 (ruido, ya filtrado) · Barça Atlètic 3 · MD · Fichajes 1.
- Por tier: 2 → 187 · 0 → 11 · 3 → 3 · 1 → 2. Casi todo es "Bastante fiable" porque viene de MD.
- Por estado: rumor 178 · oficial 14 · avanzado 11.
- Por categoría: primer equipo 184 · Barça Atlètic 19.

**Dependencia**: si cae Mundo Deportivo, la web se queda casi vacía. Por eso importa SPORT.

## Ruido recurrente (y su filtro)

| Patrón | Ejemplo | Filtro |
|---|---|---|
| Taquilla / asamblea en la búsqueda oficial | "Preventa Entradas FC BARCELONA - …" | `PALABRAS_BLOQUEO` (2026-10-05) |
| Jugador del Barça como referencia | "jugará junto a Ter Stegen" | `CONTEXTO_AJENO` (2026-10-05) |
| Ex del Barça en otro club | "el ex del Barça X firma por…" | `MENCIONES_BARSA_AJENAS` |
| Femenino sin decir "femenino" | "incorpora a la delantera Giulia Galli" | `MARCAS_FEMENINO` / `JUGADORAS_FEMENINO` |
| Otras secciones del Barça | baloncesto, balonmano, fútbol sala | `PALABRAS_BLOQUEO` / `JUGADORES_OTROS_DEPORTES` |
| Club extraído como "jugador" | "aston villa" en `cerradas` | `analisis.NO_JUGADOR` + purga al cargar |

## Fallos detectados y corregidos

| Fecha | Fallo | Arreglo |
|---|---|---|
| 2026-09-11 | Commit vacío cada 10 min | Solo se guarda si cambia algo más que la hora. |
| ≤2026-10-03 → 10-05 | SPORT bloqueado (406) en todas las ejecuciones | User-Agent de navegador + feed SPORT · Barça. |
| 2026-10-05 | "Noticias nuevas: 2" sin cambios en cada ejecución | Eran noticias de >30 días que reaparecen en el feed; ya no cuentan. |
| 2026-10-05 | Enlaces con `&` (SPORT) habrían roto el mensaje de Telegram (400) | Se escapa el `href`. |
| 2026-10-05 | Una alerta fallida se marcaba como enviada y se perdía | Solo se marcan las aceptadas; el resto se reintenta. |
| 2026-10-05 | " - " en titulares de RSS directos partía el título | Solo se recorta en Google News. |

## Pendiente / a vigilar

- Plantilla: actualizar en enero 2027 (`bot/fuentes.py`).
- `cerradas` contiene nombres de jugadoras y de baloncesto de antes de los filtros (inofensivo).
- `alertadas` se recorta a 5000 por orden alfabético, no por antigüedad. Al ritmo actual
  (~1/día) no llega al tope en años; si algún día se acerca, guardar el orden de inserción.
- SPORT · Fútbol, RAC1 y la búsqueda oficial aportan ~0 fuera de mercado: decidir en febrero
  2027, con datos de enero, si se quitan.
