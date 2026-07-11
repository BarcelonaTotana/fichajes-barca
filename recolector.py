# -*- coding: utf-8 -*-
"""
Recolector de fichajes del FC Barcelona — fuente ÚNICA: Transfermarkt.

Lee rumores (con % real) y fichajes/ventas cerrados del primer equipo y del
Barça Atlètic, guarda docs/fichajes.json (que alimenta la web) y envía alertas
a Telegram de lo NUEVO (una vez cada cosa).

Al ser Transfermarkt una fuente ya estructurada y limpia, no hacen falta filtros
de ruido: lo que hay son movimientos de mercado reales.

Uso:  python recolector.py   (en local: SSL_NO_VERIFY=1 python recolector.py)
"""
import os
import json
import datetime as dt

import fuente_transfermarkt as TM
import telegram_alertas

RUTA_DATOS = os.path.join("docs", "fichajes.json")
MAX_ALERTAS_POR_EJECUCION = 10

# SSL: en la nube se verifica; en local (proxy que intercepta TLS) usar SSL_NO_VERIFY=1.
TM.VERIFICAR_SSL = os.environ.get("SSL_NO_VERIFY", "").strip() != "1"
if not TM.VERIFICAR_SSL:
    import urllib3
    urllib3.disable_warnings()


def cargar_alertadas():
    if os.path.exists(RUTA_DATOS):
        try:
            with open(RUTA_DATOS, "r", encoding="utf-8") as f:
                return set(json.load(f).get("alertadas", []))
        except Exception:
            return set()
    return set()


def guardar(items, alertadas):
    os.makedirs("docs", exist_ok=True)
    salida = {
        "actualizado": dt.datetime.utcnow().isoformat() + "Z",
        "total": len(items),
        "alertadas": sorted(alertadas)[-5000:],
        "noticias": items,
    }
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


def ordenar(items):
    """Para la web: primero los cerrados (oficial), luego rumores por probabilidad."""
    return sorted(items, key=lambda n: (
        0 if n["estado"] == "oficial" else 1,
        -(n.get("probabilidad") or 0),
    ))


def main():
    print("== Recolector de fichajes FC Barcelona (Transfermarkt) ==")
    alertadas = cargar_alertadas()
    arranque_en_frio = not alertadas
    print(f"Alertas ya registradas: {len(alertadas)}")

    items = TM.recolectar()
    if not items:
        print("Transfermarkt no devolvió datos (posible bloqueo). Se conserva lo anterior.")
        return
    items = ordenar(items)

    # Novedades = lo que aún no se ha avisado (id estable por jugador+club+tipo).
    nuevos = [n for n in items if n["id"] not in alertadas]
    # Oficiales primero (prioridad dentro del tope de alertas).
    nuevos.sort(key=lambda n: 0 if n["estado"] == "oficial" else 1)

    if arranque_en_frio:
        for n in nuevos:
            alertadas.add(n["id"])
        print(f"Arranque en frío: {len(nuevos)} registradas SIN enviar (evita ráfaga).")
    else:
        lote = nuevos[:MAX_ALERTAS_POR_EJECUCION]
        for n in lote:
            alertadas.add(n["id"])
        if len(nuevos) > MAX_ALERTAS_POR_EJECUCION:
            print(f"AVISO: {len(nuevos)} novedades; se envían {MAX_ALERTAS_POR_EJECUCION} "
                  f"(el resto, en próximas ejecuciones).")
        if lote:
            print(f"Enviando {len(lote)} alertas a Telegram…")
            telegram_alertas.enviar_alertas(lote)

    guardar(items, alertadas)
    print(f"Total en web: {len(items)} · novedades detectadas: {len(nuevos)}")


if __name__ == "__main__":
    main()
