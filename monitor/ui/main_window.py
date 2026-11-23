"""Ventana principal: compone módulos pequeños sin alterar sus controles."""
from __future__ import annotations

import threading
import time
import tkinter as tk

from ..config import Settings
from ..database import Repositorio
from ..models import ParametrosPing
from ..service import MonitorService
from ..utils import es_admin
from .worker import Trabajador
from .main_layout import LayoutMixin
from .main_navigation import NavigationMixin
from .main_scanning import ScanningMixin
from .main_exports import ExportsMixin


class VentanaPrincipal(LayoutMixin, NavigationMixin, ScanningMixin, ExportsMixin, tk.Tk):
    """Coordina la interfaz y delega cada responsabilidad a su módulo."""

    def __init__(self, settings: Settings, repo: Repositorio, service: MonitorService):
        super().__init__()
        self.settings = settings
        self.repo = repo
        self.service = service
        self.trabajador = Trabajador()
        self._ejecutando = False
        self._cancelar = threading.Event()
        self._ventanas: dict = {}          # ventanas secundarias abiertas (una por clave)
        self._exportando = False
        self._proxima_auto = 0.0

        self.title("Monitor de Cámaras - Latencia y Conexión")
        self.geometry("1100x720")
        self._crear_variables()
        self._crear_widgets()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.after(100, self._sondear_cola)
        self.after(1000, self._tick_auto)
        if not es_admin():
            self.v_status.set(
                "AVISO: no eres administrador. El ping puede fallar. "
                "Abre el programa con 'Ejecutar como administrador'."
            )

    def _leer_parametros(self) -> ParametrosPing | None:
        """Valida y convierte los parámetros numéricos introducidos."""
        try:
            p = ParametrosPing(
                count=int(self.v_count.get()), timeout=float(self.v_timeout.get()),
                concurrentes=int(self.v_conc.get()), lento_ms=float(self.v_lento.get()))
        except ValueError:
            return None
        if p.count < 1 or p.timeout <= 0 or p.concurrentes < 1:
            return None
        return p

    def _minutos_auto(self) -> int:
        """Obtiene el intervalo de escaneo automático."""
        try:
            return max(1, int(self.v_auto_min.get()))
        except ValueError:
            return 15

    def _cerrar(self) -> None:
        """Guarda las preferencias antes de cerrar la ventana."""
        s = self.settings
        s.excel = self.v_excel.get()
        s.auto = self.v_auto.get()
        s.auto_min = self._minutos_auto()
        p = self._leer_parametros()
        if p:
            s.count, s.timeout, s.conc, s.lento = p.count, p.timeout, p.concurrentes, p.lento_ms
        s.guardar()
        self.destroy()

