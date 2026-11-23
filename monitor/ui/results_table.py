"""Tabla de resultados con colores, filtro y ordenamiento."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ..config import COLOR_ESTADO
from ..models import Estado, Resultado
from ..utils import clave_ip, normalizar_ip

COLUMNAS = ("Cámara", "Dirección IP", "Latencia (ms)", "% Paquetes perdidos", "Estado")
_ATRIBUTO = {"Cámara": "nombre", "Dirección IP": "ip", "Latencia (ms)": "ms",
             "% Paquetes perdidos": "perdida", "Estado": "estado"}
_ANCHOS = (340, 120, 90, 100, 120)
_MARCADA, _DESMARCADA = "☑", "☐"     # casilla de la primera columna (tracert masivo)


class TablaResultados(ttk.Frame):
    def __init__(self, parent, al_abrir: Optional[Callable[[str, str], None]] = None,
                 al_tracert: Optional[Callable[[str, str], None]] = None,
                 al_seleccionar: Optional[Callable[[], None]] = None,
                 al_cambiar_marcas: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self._al_abrir = al_abrir
        self._al_tracert = al_tracert
        self._al_seleccionar = al_seleccionar
        self._resultados: list[Resultado] = []
        self._orden_inverso: dict[str, bool] = {}
        self._filtro_estado = "Todos"
        self._filtro_texto = ""
        self._al_cambiar_marcas = al_cambiar_marcas
        self._marcadas: set[tuple[str, str]] = set()          # camaras marcadas (nombre, ip)
        self._iid_clave: dict[str, tuple[str, str]] = {}      # fila de la tabla -> camara

        self.tree = ttk.Treeview(self, columns=COLUMNAS, show="tree headings")
        for col, ancho in zip(COLUMNAS, _ANCHOS):
            self.tree.heading(col, text=col, command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=ancho,
                             anchor="w" if col in ("Cámara") else "center")
        # columna #0 = casilla de seleccion (no altera las columnas de datos)
        self.tree.heading("#0", text=_MARCADA, command=self._alternar_visibles)
        self.tree.column("#0", width=42, stretch=False, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        for estado, color in COLOR_ESTADO.items():
            self.tree.tag_configure(estado, background="#" + color)
        self.tree.bind("<Double-1>", self._doble_click)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._notificar_seleccion())
        self._menu = tk.Menu(self.tree, tearoff=0)
        self._menu.add_command(label="Tracert a esta cámara", command=self._tracert_seleccionado)
        self._menu.add_command(label="Ver historial de la cámara", command=self._historial_seleccionado)
        self._menu.add_separator()
        self._menu.add_command(label="Copiar nombre de la cámara", command=lambda: self._copiar_seleccionado(0))
        self._menu.add_command(label="Copiar IP", command=lambda: self._copiar_seleccionado(1))
        self.tree.bind("<Button-3>", self._menu_contextual)
        self.tree.bind("<Button-1>", self._click_casilla)
        self.tree.bind("<space>", self._tecla_espacio)

    # ---------- API publica
    @property
    def resultados(self) -> list[Resultado]:
        return self._resultados

    def seleccionado(self) -> Optional[tuple[str, str]]:
        """(nombre, ip) de la fila seleccionada, o None."""
        sel = self.tree.selection()
        if not sel:
            return None
        v = self.tree.item(sel[0], "values")
        return str(v[0]), str(v[1])

    def cargar(self, resultados: list[Resultado]) -> None:
        self._resultados = list(resultados)
        self._marcadas &= {self._clave(r) for r in self._resultados}   # conserva las que siguen en la lista
        self._render()
        self._notificar_marcas()

    def filtrar(self, estado: str, texto: str) -> None:
        self._filtro_estado = estado
        self._filtro_texto = texto.strip().lower()
        self._render()

    def conteo(self) -> dict[str, int]:
        c = {e: 0 for e in Estado.TODOS}
        for r in self._resultados:
            c[r.estado] = c.get(r.estado, 0) + 1
        return c

    # ---------- seleccion para el tracert masivo
    @staticmethod
    def _clave(r: Resultado) -> tuple[str, str]:
        return (r.nombre, r.ip)

    def marcadas(self) -> list[Resultado]:
        """Camaras marcadas, en el orden de la tabla."""
        return [r for r in self._resultados if self._clave(r) in self._marcadas]

    def contar_marcadas(self) -> int:
        return len(self.marcadas())

    def contar_visibles(self) -> int:
        return len(self._visibles())

    def marcar_visibles(self) -> None:
        """Marca solo las que se muestran en pantalla (respeta filtro de estado y busqueda)."""
        self._marcadas = {self._clave(r) for r in self._visibles()}
        self._render()
        self._notificar_marcas()

    def marcar_por_estado(self, estado: str) -> None:
        """Marca solo las de ese estado (sobre todas las cargadas, aunque el filtro oculte algunas)."""
        self._marcadas = {self._clave(r) for r in self._resultados if r.estado == estado}
        self._render()
        self._notificar_marcas()

    def desmarcar_todo(self) -> None:
        self._marcadas = set()
        self._render()
        self._notificar_marcas()

    def _alternar_visibles(self) -> None:
        """Clic en el encabezado de la casilla: marca todas las visibles, o las desmarca si ya lo estaban."""
        claves = {self._clave(r) for r in self._visibles()}
        if claves and claves <= self._marcadas:
            self._marcadas -= claves
        else:
            self._marcadas |= claves
        self._render()
        self._notificar_marcas()

    def _alternar(self, iids) -> None:
        for iid in iids:
            clave = self._iid_clave.get(iid)
            if clave is None:
                continue
            if clave in self._marcadas:
                self._marcadas.discard(clave)
            else:
                self._marcadas.add(clave)
            self.tree.item(iid, text=_MARCADA if clave in self._marcadas else _DESMARCADA)
        self._notificar_marcas()

    def _click_casilla(self, evt):
        if self.tree.identify_column(evt.x) != "#0":
            return None
        iid = self.tree.identify_row(evt.y)
        if not iid:                      # encabezado: lo atiende su propio comando
            return None
        self._alternar([iid])
        return "break"                   # no cambia la fila seleccionada

    def _tecla_espacio(self, _evt):
        self._alternar(self.tree.selection())
        return "break"

    def _notificar_marcas(self) -> None:
        if self._al_cambiar_marcas:
            self._al_cambiar_marcas()

    # ---------- interno
    def _visibles(self) -> list[Resultado]:
        """Resultados que pasan el filtro de estado y la busqueda (lo que se ve en pantalla)."""
        salida = []
        for r in self._resultados:
            if self._filtro_estado != "Todos" and r.estado != self._filtro_estado:
                continue
            if self._filtro_texto and self._filtro_texto not in f"{r.nombre} {r.ip}".lower():
                continue
            salida.append(r)
        return salida

    def _render(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._iid_clave = {}
        for r in self._visibles():
            clave = self._clave(r)
            iid = self.tree.insert(
                "", "end",
                text=_MARCADA if clave in self._marcadas else _DESMARCADA,
                values=(r.nombre, r.ip,
                        "" if r.ms is None else r.ms,
                        "" if r.perdida is None else r.perdida,
                        r.estado),
                tags=(r.estado,),
            )
            self._iid_clave[iid] = clave
        self._notificar_seleccion()

    def _ordenar(self, columna: str) -> None:
        attr = _ATRIBUTO[columna]
        inverso = self._orden_inverso.get(columna, False)

        def clave(r: Resultado):
            v = getattr(r, attr)
            if attr == "ip":
                return clave_ip(v)
            if attr in ("ms", "perdida"):
                return (v is None, v if v is not None else 0)
            return str(v).lower()

        self._resultados.sort(key=clave, reverse=inverso)
        self._orden_inverso[columna] = not inverso
        self._render()

    def _doble_click(self, _evt):
        if self.tree.identify_column(_evt.x) == "#0":      # doble clic sobre la casilla: solo marca/desmarca
            iid = self.tree.identify_row(_evt.y)
            if iid:
                self._alternar([iid])
            return "break"
        sel = self.tree.selection()
        if sel and self._al_abrir:
            v = self.tree.item(sel[0], "values")
            self._al_abrir(v[0], v[1])

    def _notificar_seleccion(self) -> None:
        if self._al_seleccionar:
            self._al_seleccionar()

    def _menu_contextual(self, evt) -> None:
        iid = self.tree.identify_row(evt.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        sel = self.seleccionado()
        valido = bool(sel and normalizar_ip(sel[1]))
        self._menu.entryconfig(0, state="normal" if valido else "disabled")
        self._menu.entryconfig(3, state="normal" if sel and sel[0] else "disabled")   # copiar nombre
        self._menu.entryconfig(4, state="normal" if sel and sel[1] else "disabled")   # copiar IP
        try:
            self._menu.tk_popup(evt.x_root, evt.y_root)
        finally:
            self._menu.grab_release()

    def _tracert_seleccionado(self) -> None:
        sel = self.seleccionado()
        if sel and self._al_tracert:
            self._al_tracert(*sel)

    def _historial_seleccionado(self) -> None:
        sel = self.seleccionado()
        if sel and self._al_abrir:
            self._al_abrir(*sel)

    def _copiar_seleccionado(self, indice: int) -> None:
        """Copia al portapapeles el nombre (0) o la IP (1) de la fila seleccionada."""
        sel = self.seleccionado()
        if sel and sel[indice]:
            self.clipboard_clear()
            self.clipboard_append(sel[indice])
