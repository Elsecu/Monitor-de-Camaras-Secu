"""Cuadro de dialogo 'Acerca de' (menu Ayuda)."""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import ttk

from .. import __version__
from ..about import componentes
from ..config import COPYRIGHT, PRODUCTO, URL_NOTAS_VERSION


class VentanaAcercaDe(tk.Toplevel):
    def __init__(self, parent, lista: str, dispositivos: list[tuple[str, str]]):
        super().__init__(parent)
        self.title(f"Acerca de {PRODUCTO}")
        self.geometry("560x640")
        self.transient(parent)

        ttk.Label(self, text=PRODUCTO, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=14, pady=(14, 0))
        ttk.Label(self, text=f"Versión {__version__}").pack(anchor="w", padx=14)
        ttk.Label(self, text=COPYRIGHT).pack(anchor="w", padx=14, pady=(6, 0))

        fila = ttk.Frame(self)
        fila.pack(anchor="w", padx=14, pady=(6, 10))
        ttk.Label(fila, text="Notas de la versión: ").pack(side="left")
        enlace = tk.Label(fila, text=URL_NOTAS_VERSION, fg="#0563C1", cursor="hand2",
                          font=("Segoe UI", 9, "underline"))
        enlace.pack(side="left")
        enlace.bind("<Button-1>", lambda e: webbrowser.open(URL_NOTAS_VERSION))

        # ---- componentes: nombre y version
        marco = ttk.LabelFrame(self, text="Producto y componentes")
        marco.pack(fill="x", padx=14, pady=4)
        arbol = ttk.Treeview(marco, columns=("Nombre", "Versión"), show="headings",
                             height=len(componentes()))
        arbol.heading("Nombre", text="Nombre")
        arbol.heading("Versión", text="Versión")
        arbol.column("Nombre", width=200)
        arbol.column("Versión", width=300)
        for nombre, version in componentes():
            arbol.insert("", "end", values=(nombre, version))
        arbol.pack(fill="x", padx=6, pady=6)

        ttk.Button(self, text="Cerrar", command=self.destroy).pack(pady=10)
