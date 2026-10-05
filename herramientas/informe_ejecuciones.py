# -*- coding: utf-8 -*-
"""Informe de funcionamiento a partir de los logs de GitHub Actions.

Lee la línea RESUMEN que el recolector imprime en cada ejecución y agrega:
ejecuciones, fallos, noticias nuevas, alertas, y por fuente: errores y relevantes.
Sirve para detectar patrones (una fuente que se cae, horas sin noticias, rate-limits).

Requiere GitHub CLI con la cuenta BarcelonaTotana activa.
Uso (desde la raíz del repo):
    python herramientas/informe_ejecuciones.py            # últimas 100 ejecuciones
    python herramientas/informe_ejecuciones.py 300        # últimas 300
"""
import json
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

WORKFLOW = "actualizar.yml"


def _gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.stdout


def _resumen_de(run_id):
    """Devuelve el dict RESUMEN de una ejecución, o None (ejecución antigua o fallida)."""
    for linea in _gh("run", "view", str(run_id), "--log").splitlines():
        i = linea.find("RESUMEN {")
        if i >= 0:
            return json.loads(linea[i + len("RESUMEN "):])
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")   # consola de Windows (cp1252)
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    runs = json.loads(_gh("run", "list", "-w", WORKFLOW, "-L", str(limite), "--json",
                          "databaseId,createdAt,conclusion,event"))
    if not runs:
        print("No hay ejecuciones (¿gh autenticado con BarcelonaTotana?).")
        return
    with ThreadPoolExecutor(max_workers=12) as ex:
        resumenes = list(ex.map(_resumen_de, [r["databaseId"] for r in runs]))

    print(f"Ejecuciones: {len(runs)}  ({runs[-1]['createdAt']} → {runs[0]['createdAt']})")
    print("  Resultado:", dict(Counter(r["conclusion"] for r in runs)))
    print("  Disparo:  ", dict(Counter(r["event"] for r in runs)))

    validos = [(r, s) for r, s in zip(runs, resumenes) if s]
    print(f"  Con línea RESUMEN: {len(validos)}"
          + ("" if validos else "  (las anteriores al cambio de octubre 2026 no la tienen)"))
    if not validos:
        return

    print(f"\nNoticias nuevas: {sum(s['nuevas'] for _, s in validos)}"
          f" · Alertas enviadas: {sum(s['alertas'] for _, s in validos)}"
          f" · Ejecuciones con commit: {sum(1 for _, s in validos if s['guardado'])}")

    errores, relevantes, entradas, caidas = Counter(), Counter(), Counter(), defaultdict(Counter)
    for _, s in validos:
        for fuente, e in s["fuentes"].items():
            if "error" in e:
                errores[fuente] += 1
                caidas[fuente][e["error"][:60]] += 1
            else:
                relevantes[fuente] += e["relevantes"]
                entradas[fuente] += e["entradas"]

    print("\nPor fuente (sobre las ejecuciones con RESUMEN):")
    # Medias por ejecución correcta (cada ejecución vuelve a ver casi las mismas entradas).
    print(f"  {'fuente':30} {'errores':>8} {'entradas/ejec':>14} {'relevantes/ejec':>16}")
    for fuente in sorted(set(errores) | set(entradas)):
        ok = len(validos) - errores[fuente]
        media_e = entradas[fuente] / ok if ok else 0
        media_r = relevantes[fuente] / ok if ok else 0
        print(f"  {fuente:30} {errores[fuente]:>8} {media_e:>14.0f} {media_r:>16.1f}")
    for fuente, motivos in caidas.items():
        for motivo, n in motivos.most_common(3):
            print(f"    · {fuente}: {n}× {motivo}")

    alertas = [(r["createdAt"], s["alertas"]) for r, s in validos if s["alertas"]]
    if alertas:
        print("\nEjecuciones con alertas:")
        for cuando, n in alertas[:15]:
            print(f"  {cuando}  {n}")


if __name__ == "__main__":
    main()
