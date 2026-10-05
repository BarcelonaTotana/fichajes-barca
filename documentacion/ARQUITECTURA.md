# Arquitectura

```
cron-job.org (cada 10 min) ──POST dispatch──► GitHub Actions "Actualizar fichajes"
                                                   │  python -m bot.recolector
                                                   ▼
   RSS (Google News, MD, SPORT) ──► filtros ──► clasificación ──► docs/fichajes.json ──► GitHub Pages (web)
                                                   │                       ▲ commit solo si cambia
                                                   └──► punto de control ──► Telegram
```

Todo es gratis: Actions (repo público), Pages, Telegram Bot API, cron-job.org.
El `schedule` del workflow existe como respaldo, pero GitHub lo dispara muy de tarde en tarde.

## Una ejecución, paso a paso (`bot/recolector.py → main`)

1. **Cargar** `docs/fichajes.json`: noticias previas, `cerradas` y `alertadas`.
   Se purgan de `cerradas` las claves que son clubes ("aston villa").
2. **Descargar** cada feed de `fuentes.BUSQUEDAS_POR_MEDIO` y luego `BUSQUEDAS_GENERALES`
   (1 s entre feeds; 3 reintentos con espera ante 429/503). User-Agent de navegador.
3. **Filtrar cada entrada** (`recolectar_feed`), en este orden:
   1. `FILTRO_ENLACE`: en feeds mixtos, solo la sección indicada (SPORT → `/noticias/barca/`).
   2. `_es_relevante` (título + resumen): sin `PALABRAS_BLOQUEO`, no femenino, no crónica de
      partido ("32-28: …"), no deportista de otra sección; nombra al Barça o a un jugador de
      la plantilla; y trae una palabra de fichaje (`PALABRAS_FICHAJE`).
   3. `_apto_feed_general` (solo feeds de todo el fútbol, `FEEDS_BARSA_EN_TITULO`): el
      **titular** nombra al Barça o a un jugador suyo como protagonista (se quitan antes
      `MENCIONES_BARSA_AJENAS` y `CONTEXTO_AJENO`) y trae un movimiento.
   4. `_clasificar`: `barca_atletic` (palabra del filial o solo jugadores del filial; sin
      renovaciones), descarte de cantera inferior, o `primer_equipo`.
4. **Clasificar**: tier (dominio → nombre del medio → mejora por periodista citado) y estado
   (`PALABRAS_ESTADO`, de más a menos certeza).
5. **Fusionar**: id = hash del título normalizado. Lo ya guardado se conserva tal cual.
6. **Recortar**: últimos 30 días, máx. 400, y **limpieza retroactiva** con los filtros de
   título actuales (por eso un filtro nuevo también limpia lo antiguo).
7. **Telegram**: de lo visto en ESTA ejecución, las que pasan `apto_para_telegram` y no están
   en `alertadas`; oficiales primero; se saltan jugadores en `cerradas`; máx. 10.
   Solo se marcan como avisadas las que Telegram acepta (o rechaza por formato).
   *Arranque en frío* (sin datos previos): se registran pero no se envían.
8. **Guardar** solo si cambia algo más que la hora → si no, no hay commit.
9. **RESUMEN**: línea JSON en el log + tabla en la página de la ejecución (ver DATOS.md).

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `bot/recolector.py` | Pipeline completo (pasos 1–9). |
| `bot/fuentes.py` | Configuración pura: feeds, tiers, listas de palabras, plantilla. Sin lógica. |
| `bot/analisis.py` | Heurísticas del mensaje: jugador (2+ palabras en mayúscula que no sean club/cargo), dirección, importe, % estimado, clave de operación. |
| `bot/telegram_alertas.py` | Formato HTML del mensaje y envío; devuelve los ids consumidos. |
| `docs/index.html` | Web estática; lee `fichajes.json`. |

## Decisiones de diseño (y por qué)

- **Sin IA ni APIs de pago**: presupuesto 0 €; heurísticas revisables y con tests.
- **RSS de sección en vez de Google News general**: Google News mezclaba baloncesto, balonmano…
- **`site:` simple en Google News**: con muchos OR, Google ignora el `site:`.
- **Id por título normalizado**: Google News cambia el enlace en cada consulta.
- **Una alerta por noticia, una por operación cerrada**: evita spam con el mismo fichaje.
- **Commit solo si hay cambios**: antes había un commit vacío cada 10 min.
- Transfermarkt se probó y se descartó (Cloudflare bloquea las IPs de Actions). Ver HISTORIAL.
