import sys
import time

from monitor import __version__
from monitor.about import componentes
from monitor.tracert import (ResultadoMasivo, SesionTracert, TracertMasivo, parsear_linea,
                             resumir)


def _saltos(*lineas):
    return [parsear_linea(l) for l in lineas]


def test_resumir_exitoso():
    s = _saltos("  1    <1 ms    <1 ms    <1 ms  192.168.1.1",
                "  2     *        *        *     Tiempo de espera agotado para esta solicitud.",
                "  3     5 ms     5 ms     5 ms  10.0.0.3")
    r = resumir("c1", "10.0.0.3", s)
    assert (r.ultimo_salto, r.respondidos, r.exitoso, r.nota) == ("10.0.0.3", 2, True, "Exitoso")


def test_resumir_no_se_pudo_conectar():
    s = _saltos("  1    <1 ms    <1 ms    <1 ms  192.168.1.1",
                "  2     *        *        *     Request timed out.")
    r = resumir("c1", "10.0.0.3", s)
    assert r.ultimo_salto == "192.168.1.1" and r.respondidos == 1 and not r.exitoso
    assert r.nota == "No se pudo conectar (destino no alcanzado)"
    assert resumir("c1", "10.0.0.3", []).nota == "No se pudo conectar (ningún salto respondió)"
    assert "tras 8 saltos" in resumir("c1", "10.0.0.3", s, "cortado", 8).nota


def _codigo(lineas, espera=0):
    return ("import time\n" + "".join(f"print({l!r}, flush=True)\n" for l in lineas)
            + (f"time.sleep({espera})\n" if espera else ""))


def _fabrica(guiones):
    """guiones: ip -> (lineas, espera). Simula tracert.exe con un script de Python."""
    def crear(ip, max_saltos, timeout_ms, silencio):
        lineas, espera = guiones[ip]
        return SesionTracert(ip, comando=[sys.executable, "-u", "-c", _codigo(lineas, espera)],
                             max_sin_respuesta=silencio)
    return crear


def _esperar(masivo, timeout=15):
    eventos, fin = [], time.time() + timeout
    while time.time() < fin:
        try:
            ev = masivo.cola.get(timeout=0.2)
        except Exception:
            continue
        eventos.append(ev)
        if ev[0] == "fin":
            break
    return eventos


def test_corte_tras_saltos_sin_respuesta():
    lineas = ["  1    <1 ms    <1 ms    <1 ms  192.168.1.1"] + \
             [f"  {i}     *        *        *     Request timed out." for i in range(2, 8)]
    s = SesionTracert("10.0.0.9", comando=[sys.executable, "-u", "-c", _codigo(lineas, 60)],
                      max_sin_respuesta=3)
    s.iniciar()
    t0, ev = time.time(), []
    while time.time() - t0 < 10:
        try:
            ev.append(s.cola.get(timeout=0.2))
        except Exception:
            continue
        if ev[-1][0] in ("fin", "error"):
            break
    assert ev[-1] == ("fin", "cortado") and time.time() - t0 < 8


def test_masivo_de_punta_a_punta():
    ok = ["  1    <1 ms    <1 ms    <1 ms  192.168.1.1", "  2     5 ms     5 ms     5 ms  10.0.0.1"]
    caida = ["  1    <1 ms    <1 ms    <1 ms  192.168.1.1",
             "  2     *        *        *     Request timed out.",
             "  3     *        *        *     Request timed out."]
    guiones = {"10.0.0.1": (ok, 0), "10.0.0.2": (caida, 0)}
    camaras = [("c1", "10.0.0.1"), ("c2", "10.0.0.2"), ("c3", "10.0.0"), ("c4", "")]
    m = TracertMasivo(camaras, concurrentes=2, fabrica=_fabrica(guiones), max_sin_respuesta=0)
    m.iniciar()
    ev = _esperar(m)
    res = {e[1]: e[2] for e in ev if e[0] == "resultado"}
    assert ev[-1] == ("fin", "completo") and [e for e in ev if e[0] == "progreso"][-1] == ("progreso", 4, 4)
    assert res[0] == ResultadoMasivo("c1", "10.0.0.1", "10.0.0.1", 2, True, "Exitoso")
    assert res[1].ultimo_salto == "192.168.1.1" and res[1].respondidos == 1 and not res[1].exitoso
    assert res[1].nota == "No se pudo conectar (destino no alcanzado)"
    assert res[2].nota == "No se pudo conectar (IP no válida)" and res[2].respondidos == 0
    assert res[3].nota == "No se pudo conectar (sin IP)"


def test_masivo_detener_cancela_pendientes_y_en_curso():
    lenta = (["  1    <1 ms    <1 ms    <1 ms  192.168.1.1"], 60)
    ips = [f"10.0.0.{i}" for i in range(1, 7)]
    m = TracertMasivo([(f"c{i}", ip) for i, ip in enumerate(ips)], concurrentes=2,
                      fabrica=_fabrica({ip: lenta for ip in ips}))
    m.iniciar()
    time.sleep(1.0)                      # ya hay 2 en curso y 4 pendientes
    t0 = time.time()
    m.detener()
    ev = _esperar(m, 10)
    resultados = [e[2] for e in ev if e[0] == "resultado"]
    assert ev[-1] == ("fin", "detenido") and time.time() - t0 < 8
    assert len(resultados) == 6 and all(r.nota == "Cancelado" for r in resultados)


def test_componentes_acerca_de():
    c = dict(componentes())
    assert c["Monitor de Cámaras"] == __version__ and "Python" in c and "SQLite (historial)" in c
