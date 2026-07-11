# Memoria del Proyecto — Monitor de Fichajes FC Barcelona (Fútbol Masculino)

> **Propósito de este archivo:** documento de continuidad. Permite cerrar la terminal y
> abrir otra sin perder el hilo del trabajo. Al retomar, lee este archivo primero.
>
> **Última actualización:** 2026-07-11

---

## 0. ÁMBITO ACTUAL (actualizado 2026-07-11, según petición del usuario)
- **Solo PRIMER EQUIPO y BARÇA ATLÈTIC** (filial). Se DESCARTA el resto de cantera
  (juvenil, cadete, infantil, La Masia…) tanto en web como en Telegram.
- **Barça Atlètic:** solo fichajes / cesiones / ventas. **Sin renovaciones.**
- **Primer equipo:** todo (fichajes, cesiones, VENTAS, renovaciones y sobre todo RUMORES/VÍNCULOS,
  ej. "Joao Félix vinculado al Barça" — es lo más importante para el usuario).
- **Disparo cada 10 min con cron-job.org** (el cron nativo de GitHub NO se dispara con fiabilidad
  en el plan gratis). cron-job.org hace POST al endpoint
  `api.github.com/repos/BarcelonaTotana/fichajes-barca/actions/workflows/actualizar.yml/dispatches`
  con body `{"ref":"main"}` y un token fine-grained (Actions: write) en sus headers. Funcionando
  desde 2026-07-11 19:27 UTC. El `schedule` del workflow se deja como backup (aunque casi no salta).
- Implementación: `recolector._clasificar` (primer_equipo / barca_atletic / None=descartar),
  keys en `config/fuentes.py` (ATLETIC_KEYS, YOUTH_KEYS, PALABRAS_ALTA_BAJA). Los vínculos/rumores
  se añadieron a PALABRAS_FICHAJE (relevancia) y PALABRAS_MOVIMIENTO (control Telegram).

## 1. Objetivo del proyecto

Construir un sistema que **controle en tiempo real y 100% en directo** todo el mercado de
fichajes del **FC Barcelona en fútbol masculino**:

- **Prioridad 1:** Primer equipo (altas, bajas, cesiones, renovaciones, cláusulas, negociaciones).
- **Prioridad 2:** Categorías inferiores / cantera (Barça Atlètic, juvenil, La Masia, canteranos con proyección).

**Requisitos clave del usuario:**
- Proceso **automático**, en vivo, sin perder información.
- Datos extraídos de **redes sociales, cuentas contrastadas y periódicos**.
- Enlazable con Claude (skills, MCP, webs, apps con las que se pueda trabajar).

---

## 2. Estado actual

- [x] Directorio de proyecto creado: `C:\Users\JORGE\Desktop\Juegos\FCBarcelona` (estaba vacío).
- [x] Investigación inicial de fuentes, herramientas y vías de automatización (ver secciones 4–6).
- [x] Creado este `Memoria.md`.
- [x] Decisiones grandes tomadas (presupuesto 0€, nube gratis, salida móvil+PC — ver sección 3).
- [x] Stack técnico elegido: Python + GitHub Actions + GitHub Pages + Telegram.
- [x] Recolector v1 (RSS Google News) + clasificador (tier/categoría/estado) — FUNCIONANDO.
- [x] Dashboard responsive + workflow cron (cada 20 min) — DESPLEGADO Y EN VIVO.
- [x] Repo público creado y subido bajo la cuenta BarcelonaTotana.
- [x] Secretos de Telegram configurados (TELEGRAM_TOKEN + TELEGRAM_CHAT_ID=1967570245).
- [x] Alerta de prueba enviada y recibida en el móvil — CIRCUITO COMPLETO Y VERIFICADO.

### ✅ PROYECTO COMPLETO Y OPERATIVO — nada pendiente crítico.
Bot Telegram: @fichajes_barca_bot · Chat ID: 1967570245 (no es secreto).
Herramientas manuales añadidas (workflows con "Run workflow" en la pestaña Actions):
- "Obtener Chat ID" (chat-id.yml) — vuelve a averiguar el Chat ID si hiciera falta.
- "Probar alerta Telegram" (probar-alerta.yml) — envía un mensaje de prueba.

### 🟢 EN PRODUCCIÓN (a fecha 2026-07-11)
- **Repo:** https://github.com/BarcelonaTotana/fichajes-barca
- **Web (móvil+PC):** https://barcelonatotana.github.io/fichajes-barca/
- **Automatización:** GitHub Actions ejecuta `recolector.py` cada 20 min y publica solo.
- Verificado: primera ejecución en la nube OK (207 noticias). Web sirve el JSON correctamente.

### Archivos del proyecto
- `recolector.py` — recolector principal (descarga RSS, clasifica, deduplica, guarda docs/fichajes.json).
- `config/fuentes.py` — búsquedas Google News + tabla de tiers por medio + palabras clave.
- `telegram_alertas.py` — envío de alertas (lee TELEGRAM_TOKEN/CHAT_ID de entorno).
- `docs/index.html` — dashboard responsive (lee fichajes.json).
- `docs/fichajes.json` — datos generados (servido por Pages).
- `.github/workflows/actualizar.yml` — cron en la nube cada 20 min.

### Único paso pendiente para acabar: alertas Telegram
1. Usuario hace `/revoke` en @BotFather y obtiene TOKEN nuevo (no pegarlo en el chat).
2. Usuario da su Chat ID (de @userinfobot).
3. Guardar como secretos del repo (NO en el código):
   `gh secret set TELEGRAM_TOKEN` y `gh secret set TELEGRAM_CHAT_ID`
   (o Settings → Secrets and variables → Actions en la web).
4. A partir de ahí, cada ejecución enviará alertas push de fuentes tier 0-1.

### Clasificador v2 (mejorado el 2026-07-11)
Tras revisar el usuario, se reconstruyó el clasificador (`recolector.py` + `config/fuentes.py`):
- **Relevancia (anti-ruido):** una noticia se guarda solo si menciona al Barça Y a un fichaje Y
  no contiene palabras de bloqueo (merch/camiseta, circuito, ajuntament, CEO, otros deportes…).
- **Fiabilidad real:** búsquedas por medio con `site:DOMINIO` (SPORT, MD, ARA, SER, RAC1, oficial)
  → tier garantizado. ⚠️ GOTCHA: la consulta `site:` debe ser SIMPLE (`Barça site:X`); si se le
  añade el gran grupo `(fichaje OR traspaso OR …)`, Google News IGNORA el `site:` y devuelve
  resultados generales. Relevo, The Athletic y ccma.cat dan 0 en Google News ES (no se usan).
- **Rescate por periodista:** si el texto cita a Romano/Moretto/Ornstein/Monfort… se sube el tier.
- **Cantera por contenido:** solo si hay palabra de cantera de peso (Masia, filial, juvenil, Barça Atlètic…).
- **Salvaguarda anti-ráfaga:** si la BD está vacía (reinicio), NO se envían alertas (arranque en frío).
- Resultado: "Verificar" 182→70; medios fiables (tier 2) 1→~72; ruido eliminado.

### Alertas de Telegram v2 (2026-07-11)
Solo se avisa de **movimientos de mercado** de fuentes **fiables** (tier ≤ 2). Formato decorado:
```
⚽ Ferran Torres al Barça
💰 22M
💬 Rumor
📊 45%
📰 Fuente: SPORT · ⭐ Primer equipo
🔗 Ver noticia
```
- `analisis.py`: extrae jugador (heurística ~50%; si no, usa el titular), dirección
  (al Barça / sale / cesión / renueva), importe (50M, 1.000M…) y % (estado + fiabilidad).
- **Rumores:** llegan todos (de fuentes fiables). **Operación oficial/acuerdo total:** se avisa
  una vez y el jugador se guarda en `cerradas` (en docs/fichajes.json) → no más Telegram de él
  (la web lo sigue mostrando). Config en recolector.py: `TIER_ALERTA=2`, `ESTADOS_CIERRE`.
- **Solo movimientos:** el titular debe tener señal de movimiento/interés (F.PALABRAS_MOVIMIENTO,
  por palabra completa: "ficha" sí, "fichajes" no) → corta análisis/retrospectivas.
- **Anti-repetidos (clave):** ID de noticia = título NORMALIZADO (sin acentos/puntuación), porque
  Google News cambia el enlace en cada consulta. Registro persistente `alertadas` (ids ya avisados,
  en docs/fichajes.json) → una noticia se avisa como MÁXIMO una vez en la vida. `MAX_ALERTAS_POR_EJECUCION=10`
  como red de seguridad anti-ráfaga.
- **PUNTO DE CONTROL** (`recolector.apto_para_telegram`): toda noticia pasa este filtro único
  antes de enviarse. Debe cumplir TODO: fuente fiable (tier≤2), **PRIMER EQUIPO** (categoria),
  movimiento real, **no femenino**, y ser del **club** (menciona "Barça/blaugrana…", no la
  ciudad "Barcelona"; salvo tier 0 oficial). Si no encaja, se descarta.
- **Femenino:** `_es_femenino` (marcas + lista de jugadoras del Femení en F.JUGADORAS_FEMENINO)
  excluye femenino de web Y Telegram (proyecto masculino).
- **Formato mensaje:** jugador / importe / estado / % / Fuente (SIN etiqueta de categoría,
  porque en Telegram todo es primer equipo).
- **Limitaciones conocidas:** el nombre del jugador no siempre se extrae bien (usa el titular);
  el % es estimación simple. Ajustar F.JUGADORAS_FEMENINO si aparece alguna jugadora nueva.

### Nota técnica (SSL en local)
El PC del usuario intercepta TLS (proxy) y Python local falla al validar certificados.
Para pruebas LOCALES: `SSL_NO_VERIFY=1 python recolector.py`. En GitHub Actions NO hace falta.

---

## 3. Decisiones tomadas

Confirmadas con el usuario el 2026-07-11:

1. **Presupuesto: 0 € (todo gratis / scraping).** Nada de APIs de pago (ni X API ni Sportmonks).
2. **Salida: accesible en móvil y ordenador, misma información en ambos, un solo sitio.**
   → Elegido: **dashboard web responsive en GitHub Pages** (URL fija, se ve igual en móvil y PC)
   + **bot de Telegram** para alertas push al móvil. El usuario delegó la elección concreta.
3. **Infraestructura: nube gratuita.** → Elegido: **GitHub Actions** como cron en la nube
   (ejecuta el recolector cada ~20 min sin PC encendido). Es la opción "24/7 gratis" real.

**Stack elegido:** Python (recolector) + GitHub Actions (cron nube gratis) +
GitHub Pages (dashboard responsive gratis) + Telegram Bot API (alertas gratis).

**Limitación asumida:** X/Twitter en tiempo real queda fuera al ser de pago / scraping inestable.
Se cubre vía **RSS de las webs de los periodistas Tier 1** (Sport, MD, Relevo, RAC1), con unos
minutos de retraso frente al tweet, pero gratis y estable.

4. **Prioridad: PRECISIÓN sobre velocidad.** El usuario es aficionado, no medio; un retraso de
   minutos es irrelevante. Objetivo: información fiable y bien clasificada, no ser el primero.
5. **Alcance de cantera: TODAS las categorías inferiores** (Barça Atlètic, juveniles, cadetes,
   infantiles… toda la base masculina), no solo los cercanos al primer equipo.
6. **Cuenta GitHub:** se crea con el email `jorgepele11@gmail.com`. Copilot NO es necesario
   (usamos Claude); se puede omitir en el registro.
7. **Cuenta a usar: `BarcelonaTotana`** (la nueva, dedicada al Barça). ⚠️ NO usar la cuenta
   `Jorgepele` (Jorge Pelegrín, de 2023): esa se usa en OTRO proyecto de Claude y no se debe
   tocar. En este PC, GitHub CLI tiene ambas cuentas conectadas a la vez (multi-cuenta);
   para este proyecto hay que tener ACTIVA `BarcelonaTotana` (`gh auth switch -u BarcelonaTotana`).

---

## 4. Fuentes de información (catálogo)

### 4.1 Clasificación de fiabilidad de periodistas del Barça
Fuente base: guía comunitaria de fiabilidad de medios (barca-reddit.github.io, act. 28-may-2026).
**Ojo:** esta guía es de la comunidad; hay debate. Se cruza con el consenso internacional.

**Tier 1 — Fiables (prioridad máxima):**
| Periodista | Medio | X/Twitter |
|---|---|---|
| Carlos Monfort | Sport | @monfortcarlos |
| David Ornstein | The Athletic / NYT | @david_ornstein |
| Fernando Polo | Mundo Deportivo | @ffpolo |
| Marta Ramon | RAC1 / ARA | @Marta_Ramon |
| Matteo Moretto | Relevo | @MatteMoretto |
| Xavi Campos | CatRadio | @xavicampos |
| Fabrizio Romano | Independiente (consenso internacional, 10/10) | @FabrizioRomano |

**Tier 2 — Bastante fiables:** Achraf Ben Ayad, Adrià Albets, Albert Rogé, Gabriel Sans,
Jose Alvarez Haya. Medios: Cadena SER, Catalunya Ràdio, RAC1, TV3.

**Tier 3 — Poco fiables (verificar siempre):** Gerard Romero (@gerardromero, Jijantes —
mucho volumen pero baja tasa de acierto según la guía), Gianluca Di Marzio (@DiMarzio),
Miguel Rico.

**Tier 4 — Muy poco fiables:** Guillem Balagué (@GuillemBalague); tratar con cautela titulares
de Marca, La Sexta, beIN.

**Tier 5 — Extremadamente poco fiables (ruido/clickbait):** Josep Pedrerol (@jpedrerol),
Nicolò Schira (@NicoSchira); AS, Bild, Daily Mail, The Sun, Don Balón.

> **Regla operativa:** ponderar cada rumor por el tier de su fuente. Marcar como "confirmado"
> solo con Tier 1 o "Here we go" de Romano / anuncio oficial del club.

### 4.2 Fuentes oficiales (máxima autoridad)
- **fcbarcelona.com** (web oficial, sección noticias y Barça Academy) — anuncios definitivos.
- Cuentas oficiales del club en X/Instagram.
- LaLiga (documentos de inscripción / límite salarial).

### 4.3 Periódicos / medios (RSS y web)
- **Catalanes pro-Barça:** Sport, Mundo Deportivo, ARA.
- **Generalistas ES:** AS, Marca (sesgo, usar con cautela).
- **Internacionales:** The Athletic, Goal.com, Sports Illustrated (Barça), CaughtOffside.
- **Blogs/comunidad:** Barça Blaugranes, Barça Universal, BarçaBuzz (cantera).

### 4.4 Agregadores
- NewsNow (Barcelona Transfer News), TransferFeed, Football Transfer League (puntúan rumores).

### 4.5 Cantera / La Masia
- fcbarcelona.com → sección Barça Academy.
- BarçaBuzz (categoría La Masia), Barça Universal, ESPN "next gen".
- Transfermarkt (valoraciones y movimientos de juveniles).

---

## 5. Herramientas / APIs de datos (para automatizar)

| Herramienta | Uso | Notas |
|---|---|---|
| **Sportmonks — Transfer Rumours API** | Rumores estructurados en tiempo real, ligados a jugador/equipo | De pago. Datos limpios y estructurados. Buen candidato principal. |
| **API-Football** (api-football.com) | Datos de jugadores, transfers, actualización cada ~15s | Plan gratuito limitado + planes de pago. Vía RapidAPI también. |
| **Sportradar** | Feeds push en tiempo real, partner FIFA | Enterprise, caro. Overkill salvo escala grande. |
| **Transfermarkt (no oficial)** | Valores de mercado, historial de traspasos, fichas | APIs comunitarias en GitHub (felipeall/transfermarkt-api, otaviofbrito) o scraping (ScrapingBee). Sin API oficial. |
| **RSS de medios** | Titulares en directo de periódicos/blogs | Gratis. Base de la ingesta de prensa. |
| **X/Twitter API** | Tweets de cuentas Tier 1/2 en tiempo real | De pago (Basic ~coste mensual). Clave para "en directo". |

---

## 6. Integración con Claude (skills, MCP, apps)

**MCP servers relevantes:**
- **feed-mcp** (richardwooding/feed-mcp): lee RSS/Atom/JSON → base para prensa y blogs. Gratis/self-host.
- **Twitter/X MCP**: varias opciones — TwitterAPI.io (MCP listo), Composio Twitter toolkit,
  Octolens (monitorización de menciones por keywords con filtrado IA). Requieren API de X.
- **Skill "RSS Reader / Feed Parser"** (mcpmarket): extrae titulares/enlaces/resúmenes.

**Automatización dentro de Claude Code:**
- **Skill `/loop`**: ejecutar un prompt/comando en intervalos (p.ej. cada 5 min) para sondear fuentes.
- **Skill `/schedule` (routines / cron)**: agentes en la nube en horario cron para ingestas programadas.
- **Herramientas del harness**: `ScheduleWakeup`, `CronCreate`/`CronList` para tareas recurrentes.

**Apps/servicios de pegamento (fuera de Claude):** n8n / Make / Zapier para orquestar webhooks
(X → base de datos → Claude) sin programar mucho. n8n es self-host y el más flexible.

---

## 7. Arquitectura propuesta (borrador, a validar)

```
FUENTES                      INGESTA (tiempo real)        PROCESADO            SALIDA
─────────                    ────────────────────         ─────────            ──────
X/Twitter (Tier 1/2)  ─┐
RSS prensa (Sport, MD) ─┤──►  Recolector (MCP/n8n)  ──►  Clasificador IA  ──► Base de datos
API fichajes (Sportmonks)┤     - poll/stream            - dedup                (SQLite/Notion)
Web oficial FCB        ─┘                                - pondera por tier    │
                                                         - resume              ▼
                                                                          Panel / alertas
                                                                          (dashboard + avisos)
```

**Principios:**
1. Cada noticia guarda: texto, fuente, tier, timestamp, jugador(es), categoría (1er equipo/cantera),
   estado (rumor / avanzado / here-we-go / oficial).
2. Deduplicar: un mismo fichaje reportado por varios → 1 registro con lista de fuentes.
3. Estado de fichaje sube de nivel solo con fuente de tier alto u oficial.
4. Alertas inmediatas cuando aparece fuente Tier 1 u oficial.

---

## 8. Decisiones pendientes (preguntar al usuario)

Las 3 grandes ya resueltas (ver sección 3). Quedan menores, a confirmar sobre la marcha:

1. **Alcance de cantera:** ¿solo canteranos con opción a primer equipo o todas las categorías?
   (Por defecto se asume: Barça Atlètic + juveniles destacados / con proyección.)
2. **Cuenta de Telegram:** el usuario deberá crear un bot con @BotFather y dar el token (gratis).
3. **Cuenta de GitHub:** hace falta un repo (puede ser privado) para Actions + Pages.

---

## 9. Próximos pasos sugeridos

1. Crear repo de GitHub y estructura del proyecto Python.
2. Recolector v1: RSS de Sport + Mundo Deportivo + ARA + web oficial FCB → guardar en JSON.
3. Clasificador: ponderar por tier de fuente (sección 4.1), detectar jugador y categoría (1er equipo/cantera),
   asignar estado (rumor / avanzado / here-we-go / oficial), deduplicar.
4. Dashboard responsive (HTML/CSS/JS estático) servido por GitHub Pages, leyendo el JSON.
5. Workflow de GitHub Actions con cron cada ~20 min que ejecuta el recolector y publica.
6. Bot de Telegram para alertas push de fuentes Tier 1 / oficiales.
7. (Opcional futuro) explorar X/Twitter si en algún momento hay presupuesto.

---

## 10. Notas de continuidad

- Al abrir una terminal nueva: **leer este archivo antes de actuar.**
- Registrar cada decisión en la sección 3 y cada avance en la sección 2.
- Convertir fechas relativas a absolutas al anotar.
- Entorno: Windows 11, PowerShell, sin repositorio git aún (proyecto local).
