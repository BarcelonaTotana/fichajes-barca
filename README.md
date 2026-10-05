# Monitor de Fichajes · FC Barcelona (fútbol masculino)

Sistema **gratuito y automático** que vigila el mercado de fichajes del FC Barcelona
(**primer equipo** y **Barça Atlètic**), clasifica cada noticia por fiabilidad de la fuente
y estado de la operación, la publica en una web y avisa por **Telegram** de los movimientos
de fuentes fiables.

- **Web:** https://barcelonatotana.github.io/fichajes-barca/
- **Telegram:** @fichajes_barca_bot
- **Ejecución:** GitHub Actions cada 10 min (lo dispara cron-job.org).

## Estructura

| Carpeta | Contenido |
|---|---|
| `bot/` | Código del bot: `recolector.py` (principal), `fuentes.py` (configuración), `analisis.py`, `telegram_alertas.py` |
| `docs/` | La web publicada por GitHub Pages (`index.html` + `fichajes.json`). **No es documentación.** |
| `documentacion/` | Manuales y referencia (ver abajo) |
| `herramientas/` | Utilidades manuales: informe de ejecuciones, prueba de alerta, chat id |
| `tests/` | Pruebas de los filtros con titulares reales |
| `.github/workflows/` | Automatizaciones de GitHub Actions |

## Documentación

- [Manual de uso](documentacion/MANUAL.md): uso diario, tareas de mantenimiento y qué hacer si algo falla.
- [Arquitectura](documentacion/ARQUITECTURA.md): cómo funciona por dentro, paso a paso.
- [Datos](documentacion/DATOS.md): formato de `fichajes.json` y del registro de cada ejecución.
- [Fuentes](documentacion/FUENTES.md): fuentes activas, su rendimiento y las descartadas.
- [Patrones](documentacion/PATRONES.md): comportamiento observado, qué es normal y qué no.
- [Historial](documentacion/HISTORIAL.md): diario original del proyecto (decisiones de julio 2026).

## Comandos rápidos (desde la raíz del repo)

```bash
pip install -r requirements.txt
python -m unittest discover -s tests          # tests
python herramientas/informe_ejecuciones.py    # estado de las últimas 100 ejecuciones
SSL_NO_VERIFY=1 python -m bot.recolector      # ejecutar en local (modifica docs/fichajes.json)
```
