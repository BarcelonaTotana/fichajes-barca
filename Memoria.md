# Memoria del Proyecto — Monitor de Fichajes FC Barcelona (Fútbol Masculino)

> **Propósito de este archivo:** documento de continuidad. Permite cerrar la terminal y
> abrir otra sin perder el hilo del trabajo. Al retomar, lee este archivo primero.
>
> **Última actualización:** 2026-07-11

---

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
- [ ] Crear repo GitHub y estructura del proyecto.
- [ ] Recolector v1 de RSS + clasificador.
- [ ] Dashboard + workflow cron + bot Telegram.

**Nada de código escrito todavía.** Siguiente paso: montar el recolector v1 (sección 9).

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
