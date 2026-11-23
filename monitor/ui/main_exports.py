"""Exportación de resultados e historial a Excel."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from ..config import DIAS_RETENCION
from ..excel_exporter import exportar_matriz, exportar_resultados
from .list_picker import elegir_lista


class ExportsMixin:
    """Agrupa responsabilidades; los métodos usan el estado de VentanaPrincipal."""

    def _pedir_ruta(self, nombre: str) -> str:
        """Solicita la ruta donde guardar un Excel."""
        return filedialog.asksaveasfilename(
            defaultextension=".xlsx", initialfile=nombre, filetypes=[("Excel", "*.xlsx")])

    def _exportar_actual(self) -> None:
        """Exporta el resultado visible del escaneo."""
        res = self.tabla.resultados
        if not res:
            messagebox.showinfo("Exportar", "Primero ejecuta una prueba.")
            return
        ts = res[0].ts
        ruta = self._pedir_ruta(f"resultado_{ts[:10]}_{ts[11:13]}{ts[14:16]}.xlsx")
        if not ruta:
            return
        try:
            exportar_resultados(ruta, res)
            self.v_status.set(f"Exportado: {ruta}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Exportar", str(e))

    def _exportar_mes(self) -> None:
        """Inicia la exportación del historial en segundo plano."""
        if self._exportando:
            return
        listas = self.repo.listas()
        if not listas:
            messagebox.showinfo("Exportar", "No hay historial todavia.")
            return
        actual = Path(self.v_excel.get()).stem
        lista = listas[0] if len(listas) == 1 else elegir_lista(
            self, listas, actual if actual in listas else listas[0])
        if lista is None:
            return
        params = self._leer_parametros()
        lento = params.lento_ms if params else 150.0
        ruta = self._pedir_ruta(
            f"historial_{lista or 'sin_lista'}_{DIAS_RETENCION}dias_{datetime.now():%Y-%m-%d}.xlsx")
        if not ruta:
            return
        self._exportando = True
        self.v_status.set("Generando historial (puede tardar unos segundos)...")
        self.trabajador.lanzar("exportar", self._tarea_exportar_mes, ruta, lento, lista)

    def _tarea_exportar_mes(self, ruta: str, lento: float, lista: str) -> str:
        """Construye el archivo Excel de historial."""
        timestamps, filas = self.repo.matriz(lista)
        exportar_matriz(ruta, timestamps, filas, lento)
        return ruta

