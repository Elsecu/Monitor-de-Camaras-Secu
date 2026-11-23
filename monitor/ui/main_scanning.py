"""Ejecución, cancelación y eventos de los escaneos de ping."""
from __future__ import annotations

import os
import queue
import time
from pathlib import Path
from tkinter import messagebox
from ..excel_reader import leer_nodos
from .worker import es_error_permisos


class ScanningMixin:
    """Agrupa responsabilidades; los métodos usan el estado de VentanaPrincipal."""

    def _alternar_escaneo(self) -> None:
        """Un solo boton: ejecuta, y mientras corre cancela."""
        if self._ejecutando:
            self._cancelar.set()
            self.btn_run.state(["disabled"])
            self.v_status.set("Cancelando escaneo...")
        else:
            self._ejecutar()

    def _ejecutar(self, silencioso: bool = False) -> None:
        """Valida datos y delega el ping al trabajador en segundo plano."""
        if self._ejecutando:
            return
        ruta = self.v_excel.get().strip()
        if not ruta or not os.path.exists(ruta):
            if silencioso:
                self.v_status.set("Auto: archivo Excel no encontrado.")
            else:
                messagebox.showwarning("Excel", "Elige un archivo Excel valido.")
            return
        params = self._leer_parametros()
        if params is None:
            messagebox.showwarning("Parametros", "Revisa los parametros numericos.")
            return
        try:
            nodos = leer_nodos(ruta)
        except Exception as e:  # noqa: BLE001
            msg = f"No se pudo leer el Excel: {e}"
            self.v_status.set(msg) if silencioso else messagebox.showerror("Excel", msg)
            return
        if not nodos:
            self.v_status.set("El Excel no tiene nodos (A = nombre, B = IP, fila 1 = encabezado).")
            return
        self._ejecutando = True
        self._cancelar.clear()
        self.btn_run.config(text="Cancelar escaneo")
        self.prog["value"] = 0
        self.v_status.set(f"Probando {len(nodos)} nodos...")
        self.trabajador.lanzar("ping", self.service.ejecutar, nodos, params,
                               self.trabajador.progreso, Path(ruta).stem, self._cancelar)

    def _sondear_cola(self) -> None:
        """Lee eventos del trabajador sin bloquear la interfaz."""
        try:
            while True:
                self._procesar(*self.trabajador.cola.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._sondear_cola)

    def _procesar(self, tipo: str, tarea: str, dato) -> None:
        """Distribuye eventos de ping y exportación."""
        if tarea == "ping":
            self._evento_ping(tipo, dato)
        elif tarea == "exportar":
            self._exportando = False
            if tipo == "ok":
                self.v_status.set(f"Exportado: {dato}")
            else:
                self.v_status.set(f"Error al exportar: {dato}")
                messagebox.showerror("Exportar", str(dato))

    def _evento_ping(self, tipo: str, dato) -> None:
        """Actualiza progreso, tabla y estado al recibir eventos de ping."""
        if tipo == "prog":
            hecho, total = dato
            self.prog["maximum"] = max(total, 1)
            self.prog["value"] = hecho
            self.v_status.set(f"Probando... {hecho} / {total} IPs")
            return
        self._ejecutando = False
        self.btn_run.state(["!disabled"])
        self.btn_run.config(text=self._texto_ejecutar)
        self._proxima_auto = time.time() + self._minutos_auto() * 60
        if tipo == "cancel":
            self.prog["value"] = 0
            self.v_status.set("Escaneo cancelado. No se guardó ningún resultado.")
            return
        if tipo == "ok":
            self.prog["value"] = self.prog["maximum"]
            self.tabla.cargar(dato)
            self._aplicar_filtro()
            self._actualizar_contadores()
            v = self._ventanas.get(("escaneos",))      # refresca la lista si esta abierta
            if v is not None and v.winfo_exists():
                v.recargar()            
            self.v_status.set(f"Terminado: {dato[0].ts if dato else ''}")
        else:
            self.v_status.set(f"Error: {dato}")
            if es_error_permisos(dato):
                messagebox.showerror("Permisos", "Ejecuta el programa como administrador.")

    def _tick_auto(self) -> None:
        """Comprueba cuándo corresponde iniciar otro escaneo automático."""
        if self.v_auto.get() and not self._ejecutando and time.time() >= self._proxima_auto:
            self._ejecutar(silencioso=True)
        self.after(1000, self._tick_auto)

