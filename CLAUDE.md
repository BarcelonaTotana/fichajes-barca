# CLAUDE.md — Monitor de fichajes FC Barcelona

Bot gratuito que cada 10 min lee RSS de prensa, filtra los fichajes del Barça (primer equipo
y Barça Atlètic, fútbol masculino), publica la web y avisa por Telegram.

## Lo primero al retomar
1. `git pull` (el bot hace commits de `docs/fichajes.json` continuamente).
2. Estado real: `python herramientas/informe_ejecuciones.py 150` (fuentes caídas, alertas, rate-limits).
3. Leer `documentacion/PATRONES.md` (qué es normal y qué no) antes de "arreglar" nada.

## Mapa
- `bot/recolector.py` — punto de entrada (`python -m bot.recolector`). Filtros, clasificación, alertas.
- `bot/fuentes.py` — TODA la configuración editable: feeds, tiers, palabras clave, plantilla.
- `bot/analisis.py` — jugador / importe / % para el mensaje de Telegram.
- `bot/telegram_alertas.py` — envío. Devuelve los ids enviados; los fallos se reintentan.
- `docs/` — la WEB (GitHub Pages sirve esta carpeta). No es documentación: no mover ni renombrar.
- `documentacion/` — manuales: MANUAL, ARQUITECTURA, DATOS, FUENTES, PATRONES, HISTORIAL.
- `herramientas/` — utilidades manuales. `tests/` — regresiones con titulares reales.

## Reglas del proyecto
- Cuenta GitHub: **BarcelonaTotana** (`gh auth switch -u BarcelonaTotana`). Nunca Jorgepele.
- Presupuesto 0 €: nada de APIs de pago. Precisión antes que velocidad.
- Cada push a `main` lanza el bot en producción: correr los tests antes de subir:
  `python -m unittest discover -s tests`
- Prueba en local SIN tocar los datos reales: copiar `bot/` y `docs/` a una carpeta temporal y
  ejecutar allí `SSL_NO_VERIFY=1 python -m bot.recolector` (el PC del usuario intercepta TLS).
- Ruido nuevo o noticia perdida → añadir el titular real a `tests/test_filtros.py` y luego el filtro.
- Cambiar cómo se construye `titulo` cambia los ids → posibles duplicados y alertas repetidas.
- Al cerrar una sesión con cambios: actualizar `documentacion/PATRONES.md` con lo observado.
