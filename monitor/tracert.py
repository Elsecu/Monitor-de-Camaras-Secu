"""Tracert individual a un nodo: ejecuta tracert.exe y entrega los saltos en vivo.

Sin dependencias de UI. La ventana consulta `sesion.cola`:
  ("salto", Salto) | ("fin", "completo" | "detenido" | "cortado") | ("error", mensaje)
"cortado" = se detuvo solo tras N saltos seguidos sin respuesta (solo si max_sin_respuesta > 0).
"""
from __future__ import annotations

import ipaddress
import logging
import queue
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from .config import (TRACERT_MASIVO_CONCURRENTES, TRACERT_MASIVO_SALTOS_SIN_RESPUESTA,
                     TRACERT_MASIVO_TIMEOUT_MS, TRACERT_MAX_SALTOS, TRACERT_TIMEOUT_MS)
from .utils import normalizar_ip

log = logging.getLogger(__name__)

_RE_SALTO = re.compile(r"^\s*(\d+)\s+(.*\S)\s*$")
_RE_SONDEO = re.compile(r"(<\s*\d+|\d+)\s*ms|(\*)")


@dataclass(frozen=True)
class Salto:
    numero: int
    intentos: tuple[str, str, str]   # p. ej. ("1 ms", "<1 ms", "*")
    ip: str                          # "" si el salto no respondio
    nota: str                        # texto extra de tracert (timeouts, errores)


def parsear_linea(linea: str) -> Salto | None:
    """Convierte una linea de salida de tracert (es/en, con -d) en un Salto.
    Devuelve None para encabezados, lineas vacias y 'Traza completa'."""
    m = _RE_SALTO.match(linea)
    if not m:
        return None
    numero, resto = int(m.group(1)), m.group(2)

    sondeos = [("*" if g2 else g1.replace(" ", "") + " ms")
               for g1, g2 in _RE_SONDEO.findall(resto)]
    sondeos = (sondeos + ["", "", ""])[:3]

    residuo = _RE_SONDEO.sub(" ", resto)
    ip, notas = "", []
    for token in residuo.split():
        candidato = token.strip("[]")
        if not ip:
            try:
                ip = str(ipaddress.ip_address(candidato))
                continue
            except ValueError:
                pass
        notas.append(token)
    return Salto(numero, (sondeos[0], sondeos[1], sondeos[2]), ip, " ".join(notas))


def _codificacion() -> str:
    """tracert imprime en la pagina de codigos OEM de la consola (ej. cp850)."""
    if sys.platform == "win32":
        try:
            import ctypes
            cp = f"cp{ctypes.windll.kernel32.GetOEMCP()}"  # type: ignore[attr-defined]
            "".encode(cp)
            return cp
        except Exception:  # noqa: BLE001
            pass
    return "utf-8"


class SesionTracert:
    """Un tracert en un hilo propio. Una sesion por nodo (independientes entre si)."""

    def __init__(
        self,
        ip: str,
        max_saltos: int = TRACERT_MAX_SALTOS,
        timeout_ms: int = TRACERT_TIMEOUT_MS,
        comando: list[str] | None = None,   # solo para pruebas
        max_sin_respuesta: int = 0,         # 0 = no cortar nunca (tracert individual)
    ):
        norm = normalizar_ip(ip)
        if norm is None:
            raise ValueError(f"IP invalida: {ip!r}")   # evita pasar texto libre al comando
        self.ip = norm
        self.cola: queue.Queue = queue.Queue()
        self._comando = comando or ["tracert", "-d", "-h", str(max_saltos),
                                    "-w", str(timeout_ms), norm]
        self._proc: subprocess.Popen | None = None
        self._detenido = False
        self._cortado = False
        self._max_silencio = max_sin_respuesta

    def iniciar(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def correr(self) -> None:
        """Igual que iniciar() pero bloquea hasta que termine (lo usa el tracert masivo)."""
        self._run()

    def detener(self) -> None:
        self._detenido = True
        p = self._proc
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def _run(self) -> None:
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # sin ventana de consola
            self._proc = subprocess.Popen(
                self._comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=flags)
            if self._detenido:
                self._proc.terminate()
            codif = _codificacion()
            seguidos = 0
            for crudo in iter(self._proc.stdout.readline, b""):
                salto = parsear_linea(crudo.decode(codif, errors="replace"))
                if salto:
                    self.cola.put(("salto", salto))
                    seguidos = 0 if salto.ip else seguidos + 1
                    if self._max_silencio and seguidos >= self._max_silencio and not self._cortado:
                        self._cortado = True        # destino inalcanzable: no esperar los saltos restantes
                        self._proc.terminate()
            rc = self._proc.wait()
            if self._detenido:
                self.cola.put(("fin", "detenido"))
            elif self._cortado:
                self.cola.put(("fin", "cortado"))
            elif rc != 0:
                self.cola.put(("error", f"tracert termino con codigo {rc}"))
            else:
                self.cola.put(("fin", "completo"))
        except FileNotFoundError:
            self.cola.put(("error", "No se encontro tracert.exe (solo disponible en Windows)."))
        except Exception as e:  # noqa: BLE001
            log.exception("Fallo el tracert a %s", self.ip)
            self.cola.put(("error", str(e)))


# ======================================================================
# Tracert masivo: varias camaras, con limite de simultaneos
# ======================================================================
@dataclass(frozen=True)
class ResultadoMasivo:
    nombre: str
    ip: str
    ultimo_salto: str    # IP del ultimo salto que respondio ("" si ninguno)
    respondidos: int     # total de saltos que respondieron
    exitoso: bool
    nota: str            # "Exitoso" | "No se pudo conectar (motivo)" | "Cancelado"


def resumir(nombre: str, ip: str, saltos: list[Salto], fin: str = "completo",
            max_sin_respuesta: int = 0) -> ResultadoMasivo:
    """Convierte los saltos de un tracert en una fila del resultado masivo (funcion pura)."""
    destino = normalizar_ip(ip) or ip
    con_ip = [s for s in saltos if s.ip]
    ultimo = con_ip[-1].ip if con_ip else ""
    if any(s.ip == destino for s in con_ip):
        return ResultadoMasivo(nombre, ip, ultimo, len(con_ip), True, "Exitoso")
    if fin == "cortado":
        motivo = f"sin respuesta tras {max_sin_respuesta} saltos seguidos"
    elif not con_ip:
        motivo = "ningún salto respondió"
    else:
        motivo = "destino no alcanzado"
    return ResultadoMasivo(nombre, ip, ultimo, len(con_ip), False, f"No se pudo conectar ({motivo})")


def _fabrica_real(ip: str, max_saltos: int, timeout_ms: int, max_sin_respuesta: int) -> SesionTracert:
    return SesionTracert(ip, max_saltos, timeout_ms, max_sin_respuesta=max_sin_respuesta)


class TracertMasivo:
    """Ejecuta un tracert por camara con un maximo de simultaneos.

    La ventana consulta `cola`:
      ("resultado", indice, ResultadoMasivo) | ("progreso", hechos, total)
      ("fin", "completo" | "detenido")
    """

    def __init__(
        self,
        camaras: list[tuple[str, str]],               # [(nombre, ip), ...]
        concurrentes: int = TRACERT_MASIVO_CONCURRENTES,
        max_saltos: int = TRACERT_MAX_SALTOS,
        timeout_ms: int = TRACERT_MASIVO_TIMEOUT_MS,
        max_sin_respuesta: int = TRACERT_MASIVO_SALTOS_SIN_RESPUESTA,
        fabrica: Callable[[str, int, int, int], SesionTracert] = _fabrica_real,  # inyectable en pruebas
    ):
        self.camaras = camaras
        self.cola: queue.Queue = queue.Queue()
        self._concurrentes = max(1, concurrentes)
        self._max_saltos, self._timeout_ms = max_saltos, timeout_ms
        self._max_silencio = max_sin_respuesta
        self._fabrica = fabrica
        self._detenido = threading.Event()
        self._activas: set[SesionTracert] = set()
        self._lock = threading.Lock()

    def iniciar(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def detener(self) -> None:
        """Cancela: las pendientes no arrancan y los tracert en curso se terminan."""
        self._detenido.set()
        with self._lock:
            for s in list(self._activas):
                s.detener()

    # ---------- interno
    def _run(self) -> None:
        total, hechos = len(self.camaras), 0
        with ThreadPoolExecutor(max_workers=self._concurrentes) as pool:
            futuros = [pool.submit(self._una, i, n, ip) for i, (n, ip) in enumerate(self.camaras)]
            for _ in as_completed(futuros):
                hechos += 1
                self.cola.put(("progreso", hechos, total))
        self.cola.put(("fin", "detenido" if self._detenido.is_set() else "completo"))

    def _una(self, i: int, nombre: str, ip: str) -> None:
        try:
            res = self._ejecutar(nombre, ip)
        except Exception as e:  # noqa: BLE001
            log.exception("Fallo el tracert masivo a %s", ip)
            res = ResultadoMasivo(nombre, ip, "", 0, False, f"No se pudo conectar (error: {e})")
        self.cola.put(("resultado", i, res))

    def _ejecutar(self, nombre: str, ip: str) -> ResultadoMasivo:
        cancelado = ResultadoMasivo(nombre, ip, "", 0, False, "Cancelado")
        if self._detenido.is_set():
            return cancelado
        if not ip:
            return ResultadoMasivo(nombre, ip, "", 0, False, "No se pudo conectar (sin IP)")
        norm = normalizar_ip(ip)
        if norm is None:
            return ResultadoMasivo(nombre, ip, "", 0, False, "No se pudo conectar (IP no válida)")

        sesion = self._fabrica(norm, self._max_saltos, self._timeout_ms, self._max_silencio)
        with self._lock:
            self._activas.add(sesion)
        try:
            if self._detenido.is_set():
                sesion.detener()       # carrera: se cancelo justo antes de arrancar
            sesion.correr()
        finally:
            with self._lock:
                self._activas.discard(sesion)

        saltos: list[Salto] = []
        fin, error = "completo", ""
        while True:
            try:
                tipo, dato = sesion.cola.get_nowait()
            except queue.Empty:
                break
            if tipo == "salto":
                saltos.append(dato)
            elif tipo == "fin":
                fin = dato
            elif tipo == "error":
                error = dato
        res = resumir(nombre, ip, saltos, fin, self._max_silencio)
        if res.exitoso:
            return res
        if fin == "detenido":
            return ResultadoMasivo(nombre, ip, res.ultimo_salto, res.respondidos, False, "Cancelado")
        if error:
            return ResultadoMasivo(nombre, ip, res.ultimo_salto, res.respondidos, False,
                                   f"No se pudo conectar (error: {error})")
        return res
