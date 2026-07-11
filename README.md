# Monitor de Fichajes · FC Barcelona (fútbol masculino)

Sistema **gratuito y automático** que vigila el mercado de fichajes del FC Barcelona
(primer equipo + todas las categorías inferiores), clasifica cada noticia por
**fiabilidad de la fuente**, y lo muestra en una web accesible desde móvil y ordenador.
Además envía **alertas a Telegram** cuando hay noticias de fuentes fiables.

- **Recolector** (`recolector.py`): lee Google News RSS, filtra fichajes del Barça,
  clasifica (fiabilidad / categoría / estado), deduplica y guarda `docs/fichajes.json`.
- **Panel** (`docs/index.html`): web responsive que lee ese JSON. La sirve GitHub Pages.
- **Automatización** (`.github/workflows/actualizar.yml`): GitHub Actions lo ejecuta
  cada 20 min en la nube (sin ordenador encendido) y publica los cambios.
- **Alertas** (`telegram_alertas.py`): avisos push al móvil vía bot de Telegram.

## Cómo se pone en marcha (resumen)

1. **Subir este proyecto a un repo de GitHub** (rama `main`).
2. **Activar GitHub Pages**: Settings → Pages → "Deploy from a branch" → rama `main`, carpeta `/docs`.
   La web quedará en `https://TU_USUARIO.github.io/NOMBRE_REPO/`.
3. **Añadir los secretos de Telegram**: Settings → Secrets and variables → Actions → New secret:
   - `TELEGRAM_TOKEN` = token del bot (de @BotFather)
   - `TELEGRAM_CHAT_ID` = tu chat id (de @userinfobot)
4. **Actions** ejecutará el recolector cada 20 min. También puedes lanzarlo a mano
   desde la pestaña **Actions → Actualizar fichajes → Run workflow**.

## Probar en local

```bash
pip install -r requirements.txt
python recolector.py           # genera docs/fichajes.json
```

> Si tu Python local da error de certificados SSL, ejecuta con `SSL_NO_VERIFY=1`
> (solo para pruebas locales; en GitHub Actions no hace falta).

Para ver el panel en local, abre `docs/index.html` con un servidor simple:
```bash
python -m http.server -d docs 8000   # y abre http://localhost:8000
```

## Ajustar fuentes y fiabilidad

Todo está en `config/fuentes.py`: búsquedas de Google News, tabla de tiers por medio,
palabras clave de estado y de categoría (cantera). Ver `Memoria.md` para el contexto completo.
