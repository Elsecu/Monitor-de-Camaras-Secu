"""Genera una vista imprimible del tracert masivo sin dependencias externas.

La vista se abre en el navegador predeterminado; el usuario decide si imprimir,
qué impresora usar o si guardar como PDF. No se envía nada a Internet.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
import tempfile
import webbrowser
import os
from .config import DATA_DIR


COLUMNAS = ("Cámara", "IP", "Último salto (IP)", "Total de saltos respondidos", "Notas")


def crear_reporte_html(filas: list[tuple[str, ...]], fecha: datetime | None = None) -> str:
    """Construye un HTML seguro para imprimir, respetando el orden de la tabla."""
    fecha = fecha or datetime.now()
    cuerpo = "\n".join(
        "<tr>" + "".join(f"<td>{escape(str(valor))}</td>" for valor in fila) + "</tr>"
        for fila in filas
    )
    encabezados = "".join(f"<th>{escape(col)}</th>" for col in COLUMNAS)
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Resultados del Tracert masivo</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
  h1 {{ font-size: 20px; margin-bottom: 6px; }}
  .meta {{ color: #555; margin-bottom: 18px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 11px; }}
  th, td {{ border: 1px solid #bbb; padding: 6px; text-align: left; overflow-wrap: anywhere; }}
  th {{ background: #eaeaea; }}
  tr {{ break-inside: avoid; }}
  .acciones {{ margin-bottom: 18px; }}
  @page {{ size: A4 landscape; margin: 12mm; }}
  @media print {{ .acciones {{ display: none; }} body {{ margin: 0; }} }}
</style></head><body>
<div class="acciones"><button type="button" onclick="window.print()">Imprimir / Guardar como PDF</button></div>
<h1>Resultados del Tracert masivo</h1>
<div class="meta">Fecha: {fecha:%d/%m/%Y %H:%M:%S} | Cámaras: {len(filas)}</div>
<table><thead><tr>{encabezados}</tr></thead><tbody>{cuerpo}</tbody></table>
</body></html>'''


def abrir_reporte(filas: list[tuple[str, ...]]) -> Path:
    """
    Genera el reporte HTML del Tracert masivo.

    Guarda el archivo temporal dentro de la carpeta de datos
    de la aplicación y lo abre en el navegador para imprimir.
    """

    # Carpeta centralizada de datos de la aplicación.
    carpeta = Path(DATA_DIR) / "temp"

    # Crear la carpeta si no existe.
    carpeta.mkdir(parents=True, exist_ok=True)

    # Archivo temporal reutilizable.
    ruta = carpeta / "tracert_masivo.html"

    # Generar el contenido HTML del reporte.
    html = crear_reporte_html(filas)

    # Sobrescribir el reporte anterior.
    ruta.write_text(html, encoding="utf-8")

    # Abrir el reporte en el navegador predeterminado.
    if not webbrowser.open(ruta.as_uri()):
        raise RuntimeError(
            f"No se pudo abrir el navegador. Reporte disponible en: {ruta}"
        )

    return ruta