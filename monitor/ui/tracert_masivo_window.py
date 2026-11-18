"""Ventana de resultados del tracert masivo (varias camaras)."""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..config import COLOR_ESTADO
from ..tracert import ResultadoMasivo, TracertMasivo

_COLUMNAS = ("Cámara", "IP", "Último salto (IP)", "Total de saltos respondidos", "Notas")
_ANCHOS = (210, 120, 130, 170, 330)


class VentanaTracertMasivo(tk.Toplevel):
    def __init__(self, parent, camaras: list[tuple[str, str]],
                 al_abrir_individual: Callable[[str, str], None],
                 masivo: TracertMasivo | None = None):
        super().__init__(parent)
        self.title(f"Tracert masivo - {len(camaras)} cámaras")
        self.geometry("1020x560")
        self._camaras = camaras
        self._al_abrir = al_abrir_individual
        self._masivo = masivo or TracertMasivo(camaras)
        self._en_curso = True
        self._after_id: str | None = None
        self._iid_indice: dict[str, int] = {}
        self._iids: list[str] = []
        self._hechos = self._exitosas = self._fallidas = 0
        self.v_estado = tk.StringVar()

        ttk.Label(self, textvariable=self.v_estado).pack(anchor="w", padx=8, pady=(8, 2))
        self.prog = ttk.Progressbar(self, mode="determinate", maximum=max(1, len(camaras)))
        self.prog.pack(fill="x", padx=8)

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree = ttk.Treeview(marco, columns=_COLUMNAS, show="headings")
        for col, ancho in zip(_COLUMNAS, _ANCHOS):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=ancho, anchor="w" if col in ("Cámara", "Notas") else "center")
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("exitoso", background="#" + COLOR_ESTADO["OK"])
        self.tree.tag_configure("fallo", background="#" + COLOR_ESTADO["Sin respuesta"])
        self.tree.tag_configure("cancelado", background="#" + COLOR_ESTADO["No hay IP"])
        self.tree.bind("<Double-1>", self._doble_click)

        for i, (nombre, ip) in enumerate(camaras):
            iid = self.tree.insert("", "end", values=(nombre, ip, "", "", "Pendiente..."))
            self._iid_indice[iid] = i
            self._iids.append(iid)

        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")
        self.btn_detener = ttk.Button(barra, text="Detener", command=self._detener)
        self.btn_detener.pack(side="left")
        ttk.Button(barra, text="Copiar", command=self._copiar).pack(side="left", padx=6)
        ttk.Label(barra, text="Doble clic en una cámara: abre su tracert individual").pack(side="left", padx=10)

        self.bind("<Destroy>", self._al_destruir)
        self._actualizar_estado()
        self._masivo.iniciar()
        self._after_id = self.after(150, self._sondear)

    def en_curso(self) -> bool:
        return self._en_curso

    # ---------- eventos
    def _sondear(self) -> None:
        self._after_id = None
        if not self.winfo_exists():
            return
        try:
            while True:
                tipo, *datos = self._masivo.cola.get_nowait()
                if tipo == "resultado":
                    self._mostrar(datos[0], datos[1])
                elif tipo == "progreso":
                    self._hechos = datos[0]
                    self.prog["value"] = datos[0]
                elif tipo == "fin":
                    self._en_curso = False
                    self.btn_detener.state(["disabled"])
        except queue.Empty:
            pass
        self._actualizar_estado()
        if self._en_curso or not self._masivo.cola.empty():
            self._after_id = self.after(150, self._sondear)

    def _mostrar(self, indice: int, r: ResultadoMasivo) -> None:
        if r.exitoso:
            tag, self._exitosas = "exitoso", self._exitosas + 1
        elif r.nota == "Cancelado":
            tag = "cancelado"
        else:
            tag, self._fallidas = "fallo", self._fallidas + 1
        self.tree.item(self._iids[indice], tags=(tag,), values=(
            r.nombre, r.ip, r.ultimo_salto or "-", r.respondidos, r.nota))

    def _actualizar_estado(self) -> None:
        total = len(self._camaras)
        estado = "En curso" if self._en_curso else "Terminado"
        self.v_estado.set(f"{estado}: {self._hechos}/{total} cámaras | "
                          f"Exitosas {self._exitosas} | No se pudo conectar {self._fallidas}")

    # ---------- acciones
    def _detener(self) -> None:
        self.btn_detener.state(["disabled"])
        self.v_estado.set("Deteniendo...")
        self._masivo.detener()

    def _al_destruir(self, evt) -> None:
        if evt.widget is self:        # no matar los procesos por destruccion de widgets hijos
            self._masivo.detener()

    def _doble_click(self, evt) -> None:
        iid = self.tree.identify_row(evt.y)
        if iid:
            nombre, ip = self._camaras[self._iid_indice[iid]]
            self._al_abrir(nombre, ip)       # reutiliza la ventana de tracert individual

    def _copiar(self) -> None:
        filas = ["\t".join(_COLUMNAS)] + [
            "\t".join(str(v) for v in self.tree.item(i, "values")) for i in self._iids]
        self.clipboard_clear()
        self.clipboard_append("\n".join(filas))
        self.v_estado.set("Tabla copiada al portapapeles")
