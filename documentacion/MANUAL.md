# Manual de uso

## 1. Uso diario

**Web** — https://barcelonatotana.github.io/fichajes-barca/
- Muestra las noticias de los últimos 30 días (máximo 400), las más recientes primero.
- Filtros: equipo (primer equipo / Barça Atlètic), estado (oficial —incluye "here we go"—,
  avanzado, rumor), fiabilidad ("Todas" o "Solo fiables" = tier 0–2) y buscador.
  Las de tier 5 (clickbait) no se muestran nunca.
- Se actualiza sola. Si no ves cambios, recarga (la web pide el JSON sin caché).

**Telegram** — @fichajes_barca_bot
- Solo llegan **movimientos** (fichaje, cesión, venta, renovación, interés…) de fuentes con
  tier 0–2, del primer equipo o del Barça Atlètic, y que nombren al club o a un jugador suyo.
- Cada noticia llega **una sola vez**. Cuando una operación es oficial o "here we go", ese
  jugador queda "cerrado" y no vuelve a avisarse (la web sí lo sigue mostrando).
- Máximo 10 alertas por ejecución; el resto llega en la siguiente.
- Fuera de los mercados de fichajes (ene / jul–ago) es normal pasar días sin alertas.

## 2. Botones manuales (GitHub → pestaña Actions → elegir workflow → "Run workflow")

| Workflow | Para qué |
|---|---|
| Actualizar fichajes | Lanza el bot ahora mismo (sin esperar los 10 min). |
| Probar alerta Telegram | Envía un mensaje de prueba: confirma que token y chat id funcionan. |
| Obtener Chat ID | Muestra el chat id si hubiera que reconfigurarlo (escribe antes algo al bot). |
| Tests | Pasa las pruebas de los filtros (también se lanza solo al subir código). |
| Enviar noticia Adeyemi | Herramienta puntual de julio 2026. Ya no hace falta; se puede borrar. |

## 3. Tareas de mantenimiento

### Actualizar la plantilla (cada mercado: enero y septiembre)
En `bot/fuentes.py`, listas `JUGADORES_PRIMER_EQUIPO` y `JUGADORES_BARCA_ATLETIC`.
- Fuente: fcbarcelona.com → Plantilla, o Wikipedia ES/EN (la web oficial no lista todo el filial).
- Apellidos muy comunes, con nombre completo ("eric garcía"). Si un apellido choca con jugadores
  de otros equipos, mejor no ponerlo.
- Mover a "cedidos" a los que salen cedidos (su futuro sigue siendo noticia del Barça).
- **Próxima revisión: enero 2027.**

### Se cuela ruido en la web o en Telegram
1. Copia el titular exacto.
2. Añádelo como caso en `tests/test_filtros.py` (comprobando que debe quedar FUERA).
3. Añade la palabra o expresión a la lista adecuada de `bot/fuentes.py`:
   - otro deporte o tema → `PALABRAS_BLOQUEO`
   - deportista de otra sección → `JUGADORES_OTROS_DEPORTES`
   - fútbol femenino → `MARCAS_FEMENINO` o `JUGADORAS_FEMENINO`
   - "el ex del Barça X…" → `MENCIONES_BARSA_AJENAS`
   - "junto a / a falta de [jugador]" → `CONTEXTO_AJENO`
4. `python -m unittest discover -s tests` y subir. La limpieza es **retroactiva**: lo ya
   guardado que no pase el filtro desaparece de la web en la siguiente ejecución.

### Falta una noticia que debería estar
Ejecuta el diagnóstico de un titular (desde la raíz):
```bash
python -c "from bot import recolector as R; t='TITULAR'; print('relevante', R._es_relevante(t), '| categoría', R._clasificar(t), '| movimiento', R._tiene_movimiento(t))"
```
Lo normal es que falte una palabra en `PALABRAS_FICHAJE` / `PALABRAS_MOVIMIENTO` o el jugador
en la plantilla. Añade el caso a los tests igual que con el ruido.

### Añadir o cambiar una fuente
Ver `documentacion/FUENTES.md` → "Cómo probar una fuente nueva".

## 4. Si algo falla

| Síntoma | Dónde mirar | Causa habitual |
|---|---|---|
| La web no se actualiza | Actions → "Actualizar fichajes": ¿hay ejecuciones recientes? | cron-job.org parado o su token de GitHub caducado (ver HISTORIAL §0). |
| Ejecuciones en rojo | Abrir la ejecución → paso "Ejecutar recolector" | Error de código tras un cambio: revertir el último commit. |
| `[ERROR] <fuente>` en el log | `python herramientas/informe_ejecuciones.py` | 503 rate-limit de Google News (normal si es puntual); 403/406 = bloqueo (ver FUENTES). |
| No llegan alertas | Log: líneas `[Telegram]` | `Error 401`: token revocado → `gh secret set TELEGRAM_TOKEN`. Sin líneas: no hubo candidatas (normal fuera de mercado). |
| Alertas repetidas | `docs/fichajes.json` → `alertadas` | Cambio en cómo se construye el título (cambia el id). |

Las alertas que fallan por red, 401/403, 429 o 5xx **no se pierden**: se reintentan en la
siguiente ejecución. Solo se descartan las que Telegram rechaza por formato (400).

## 5. Credenciales

- Secretos del repo (Settings → Secrets → Actions): `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.
- cron-job.org guarda un token fine-grained de GitHub (permiso Actions: write) para lanzar
  el workflow cada 10 min. Si caduca, el bot solo correrá con el `schedule` de GitHub, que
  es muy irregular.
- Nunca pegar tokens en el código ni en el chat.
