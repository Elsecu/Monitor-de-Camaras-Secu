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


COLUMNAS = ("Cámara", "Dirección IP", "Último salto (IP)", "Total de saltos respondidos", "Notas")


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
<title>Resultados del Tracert grupal</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
  h1 {{ font-size: 20px; margin-bottom: 6px; }}
  .meta {{ color: #555; margin-bottom: 18px; }}
  /* Configuración general de la tabla */
table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 11px;
    table-layout: fixed;
}}

/* Estilo general de las celdas */
th, td {{
    border: 1px solid #bbb;
    padding: 6px;
    text-align: left;
    overflow-wrap: anywhere;
}}

/* Color de los encabezados */
th {{
    background: #eaeaea;
}}

/* Columna 1: Nombre de la cámara */
th:nth-child(1) {{
    width: 35%;
}}

/* Columna 2: Dirección IP */
th:nth-child(2) {{
    width: 15%;
}}

/* Columna 3: Último salto (IP) */
th:nth-child(3) {{
    width: 15%;
}}

/* Columna 4: Total de saltos respondidos */
th:nth-child(4) {{
    width: 10%;
}}

/* Columna 5: Notas */
th:nth-child(5) {{
    width: 25%;
}}

/* Evitar que las direcciones IP se dividan */
td:nth-child(2),
td:nth-child(3) {{
    white-space: nowrap;
    overflow-wrap: normal;
}}

/* Centrar el total de saltos respondidos */
th:nth-child(4),
td:nth-child(4) {{
    text-align: center;
}}
  .acciones {{ margin-bottom: 18px; }}
  @page {{ size: letter landscape; margin: 10mm; }}
  @media print {{ .acciones {{ display: none; }} body {{ margin: 0; }} }}
</style></head><body>
<div class="acciones"><button type="button" onclick="window.print()">Imprimir / Guardar como PDF</button></div>
<h1>Resultados del Tracert grupal</h1>
<div class="meta">Fecha: {fecha:%d/%m/%Y %H:%M:%S} | Cámaras: {len(filas)}</div>
<table><thead><tr>{encabezados}</tr></thead><tbody>{cuerpo}</tbody></table>
</body></html>'''


def abrir_reporte(filas: list[tuple[str, ...]]) -> Path:
    """
    Genera el reporte HTML del Tracert grupal.

    Guarda el archivo temporal dentro de la carpeta de datos
    de la aplicación y lo abre en el navegador para imprimir.
    """

    # Carpeta centralizada de datos de la aplicación.
    carpeta = Path(DATA_DIR) / "temp"

    # Crear la carpeta si no existe.
    carpeta.mkdir(parents=True, exist_ok=True)

    # Archivo temporal reutilizable.
    ruta = carpeta / "tracert_grupal.html"

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