"""Ventana de tracert para UNA camara: muestra los saltos conforme llegan."""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk, messagebox

from ..config import COLOR_ESTADO, TRACERT_MAX_SALTOS
from ..models import Estado
from ..tracert import Salto, SesionTracert
from ..tracert_individual_print import abrir_reporte

_COLUMNAS = ("Salto", "Intento 1", "Intento 2", "Intento 3", "IP del salto", "Nota")
_ANCHOS = (60, 85, 85, 85, 150, 280)


class VentanaTracert(tk.Toplevel):
    def __init__(self, parent, nombre: str, ip: str):
        super().__init__(parent)
        self._nombre, self._ip = nombre, ip
        self.title(f"Tracert - {nombre} ({ip})" if nombre else f"Tracert - {ip}")
        self.geometry("780x460")
        self._sesion: SesionTracert | None = None
        self._saltos: list[Salto] = []
        self._after_id: str | None = None
        self.v_estado = tk.StringVar()

        ttk.Label(self, textvariable=self.v_estado).pack(anchor="w", padx=8, pady=6)

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True, padx=8)
        self.tree = ttk.Treeview(marco, columns=_COLUMNAS, show="headings")
        for col, ancho in zip(_COLUMNAS, _ANCHOS):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=ancho, anchor="w" if col == "Nota" else "center")
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        for estado, color in COLOR_ESTADO.items():
            self.tree.tag_configure(estado, background="#" + color)

        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")
        self.btn_detener = ttk.Button(barra, text="Detener", command=self._detener)
        self.btn_detener.pack(side="left")
        self.btn_repetir = ttk.Button(barra, text="Repetir", command=self._iniciar)
        self.btn_repetir.pack(side="left", padx=6)
        ttk.Button(barra, text="Copiar", command=self._copiar).pack(side="left")
        # Botón para imprimir los resultados del Tracert individual.
        ttk.Button(
            barra,
            text="Imprimir resultados",
            command=self._imprimir
        ).pack(side="left", padx=6)

        self.bind("<Destroy>", self._al_destruir)
        self._iniciar()

    # ---------- control
    def _iniciar(self) -> None:
        self._detener(silencioso=True)
        self.tree.delete(*self.tree.get_children())
        self._saltos = []
        self._sesion = SesionTracert(self._ip)
        self._sesion.iniciar()
        self.btn_detener.state(["!disabled"])
        self.btn_repetir.state(["disabled"])
        self.v_estado.set(f"Ejecutando tracert a {self._ip} (máx. {TRACERT_MAX_SALTOS} saltos)...")
        if self._after_id is None:
            self._after_id = self.after(100, self._sondear)

    def _detener(self, silencioso: bool = False) -> None:
        if self._sesion is not None:
            self._sesion.detener()
        if not silencioso:
            self.btn_detener.state(["disabled"])
            self.v_estado.set("Deteniendo...")

    def _al_destruir(self, evt) -> None:
        if evt.widget is self:        # evita matar el proceso por destruccion de hijos
            self._detener(silencioso=True)

    # ---------- eventos
    def _sondear(self) -> None:
        self._after_id = None
        if not self.winfo_exists():
            return
        try:
            while self._sesion is not None:
                tipo, dato = self._sesion.cola.get_nowait()
                if tipo == "salto":
                    self._agregar(dato)
                else:
                    self._terminar(tipo, dato)
        except queue.Empty:
            pass
        self._after_id = self.after(100, self._sondear)

    def _agregar(self, s: Salto) -> None:
        self._saltos.append(s)
        sin_respuesta = not s.ip and all(i in ("*", "") for i in s.intentos)
        tag = (Estado.OK if s.ip and s.ip == self._ip
               else Estado.SIN_RESPUESTA if sin_respuesta else "")
        iid = self.tree.insert(
            "", "end", tags=(tag,) if tag else (),
            values=(s.numero, *s.intentos, s.ip or "*", s.nota))
        self.tree.see(iid)
        self.v_estado.set(f"Ejecutando... {len(self._saltos)} saltos")

    def _terminar(self, tipo: str, dato: str) -> None:
        self.btn_detener.state(["disabled"])
        self.btn_repetir.state(["!disabled"])
        n = len(self._saltos)
        llego = any(s.ip == self._ip for s in self._saltos)
        if tipo == "error":
            self.v_estado.set(f"Error: {dato}")
        elif dato == "detenido":
            self.v_estado.set(f"Detenido por el usuario ({n} saltos)")
        elif llego:
            self.v_estado.set(f"Completo: destino alcanzado en {n} saltos")
        else:
            self.v_estado.set(f"Terminó sin alcanzar el destino ({n} saltos)")

    def _copiar(self) -> None:
        filas = ["\t".join(_COLUMNAS)] + [
            "\t".join(str(v) for v in self.tree.item(i, "values"))
            for i in self.tree.get_children()]
        self.clipboard_clear()
        self.clipboard_append("\n".join(filas))
        self.v_estado.set("Tabla copiada al portapapeles")

    def _imprimir(self) -> None:
        """Abre un reporte imprimible de los resultados actuales."""

        # Obtener todas las filas de la tabla.
        filas = [
            tuple(
                str(valor)
                for valor in self.tree.item(i, "values")
            )
            for i in self.tree.get_children()
        ]

        # Evitar generar reportes vacíos.
        if not filas:
            messagebox.showwarning(
                "Imprimir resultados",
                "No hay resultados para imprimir.",
                parent=self
            )
            return

        try:
            # Generar y abrir el reporte de la cámara.
            abrir_reporte(
                nombre=self._nombre,
                ip=self._ip,
                filas=filas
            )

        except Exception as e:
            # Mostrar un mensaje si ocurre algún error.
            messagebox.showerror(
                "Error de impresión",
                f"No se pudo abrir el reporte:\n{e}",
                parent=self
            )