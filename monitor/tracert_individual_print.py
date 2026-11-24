
"""Generación e impresión de reportes del Tracert individual."""

from __future__ import annotations

import webbrowser
from datetime import datetime
from html import escape
from pathlib import Path

from .config import DATA_DIR


# Encabezados de la tabla del reporte.
COLUMNAS = (
    "Salto",
    "Intento 1",
    "Intento 2",
    "Intento 3",
    "IP del salto",
    "Nota",
)


def crear_reporte_html(
    nombre: str,
    ip: str,
    filas: list[tuple[str, ...]],
    fecha: datetime | None = None,
) -> str:
    """Construye el reporte HTML del Tracert individual."""

    # Utilizar la fecha y hora actual si no se proporciona una.
    fecha = fecha or datetime.now()

    # Generar las filas de la tabla.
    # escape() evita que los datos se interpreten como código HTML.
    cuerpo = "\n".join(
        "<tr>"
        + "".join(
            f"<td>{escape(str(valor))}</td>"
            for valor in fila
        )
        + "</tr>"
        for fila in filas
    )

    # Generar los encabezados de la tabla.
    encabezados = "".join(
        f"<th>{escape(col)}</th>" for col in COLUMNAS
    )

    # Construir el documento HTML y sus estilos.
    return f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Resultados del Tracert individual</title>

<style>

    /* Estilo general del documento */
    body {{
        font-family: Arial, sans-serif;
        margin: 24px;
        color: #222;
    }}

    h1 {{
        font-size: 20px;
        margin-bottom: 6px;
    }}

    /* Información de la cámara */
    .meta {{
        color: #555;
        margin-bottom: 18px;
        font-size: 12px;
        line-height: 1.6;
    }}

    /* Configuración general de la tabla */
    table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 11px;
        table-layout: fixed;
    }}

    /* Estilo de las celdas */
    th, td {{
        border: 1px solid #bbb;
        padding: 6px;
        text-align: center;
        overflow-wrap: anywhere;
        box-sizing: border-box;
        vertical-align: middle;
    }}

    /* Color de los encabezados */
    th {{
        background: #eaeaea;
    }}

    /* Columna 1: Número de salto */
    th:nth-child(1) {{
        width: 7%;
    }}

    /* Columnas 2, 3 y 4: Intentos */
    th:nth-child(2),
    th:nth-child(3),
    th:nth-child(4) {{
        width: 12%;
    }}

    /* Columna 5: Dirección IP */
    th:nth-child(5) {{
        width: 22%;
    }}

    /* Columna 6: Notas */
    th:nth-child(6) {{
        width: 35%;
    }}

    /* Evitar que las direcciones IP se dividan */
    td:nth-child(5) {{
        white-space: nowrap;
        overflow-wrap: normal;
    }}

    /* Alinear las notas a la izquierda */
    td:nth-child(6) {{
        text-align: left;
    }}

    /* Espacio debajo del botón de impresión */
    .acciones {{
        margin-bottom: 18px;
    }}

    /* Tamaño carta en orientación horizontal */
    @page {{
        size: letter landscape;
        margin: 10mm;
    }}

    /* Configuración exclusiva para imprimir */
    @media print {{

        /* Ocultar el botón en el documento impreso */
        .acciones {{
            display: none;
        }}

        body {{
            margin: 0;
        }}

        /* Evitar dividir filas entre páginas */
        tr {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        /* Repetir encabezados en cada página */
        thead {{
            display: table-header-group;
        }}
    }}

</style>
</head>

<body>

<div class="acciones">
    <button type="button" onclick="window.print()">
        Imprimir / Guardar como PDF
    </button>
</div>

<h1>Resultados del Tracert individual</h1>

<div class="meta">
    <strong>Cámara:</strong> {escape(nombre)}<br>
    <strong>IP de destino:</strong> {escape(ip)}<br>
    <strong>Fecha:</strong> {fecha:%d/%m/%Y %H:%M:%S}<br>
    <strong>Total de saltos registrados:</strong> {len(filas)}
</div>

<table>
    <thead>
        <tr>{encabezados}</tr>
    </thead>
    <tbody>
        {cuerpo}
    </tbody>
</table>

</body>
</html>'''


def abrir_reporte(
    nombre: str,
    ip: str,
    filas: list[tuple[str, ...]],
) -> Path:
    """Guarda el reporte temporal y lo abre en el navegador."""

    # Utilizar la carpeta centralizada de la aplicación.
    carpeta = Path(DATA_DIR) / "temp"

    # Crear la carpeta si todavía no existe.
    carpeta.mkdir(parents=True, exist_ok=True)

    # Reutilizar el mismo archivo para evitar acumulaciones.
    ruta = carpeta / "tracert_individual.html"

    # Generar el contenido del reporte.
    html = crear_reporte_html(nombre, ip, filas)

    # Guardar el HTML, sobrescribiendo el reporte anterior.
    ruta.write_text(html, encoding="utf-8")

    # Abrir el navegador predeterminado.
    if not webbrowser.open(ruta.as_uri()):
        raise RuntimeError(
            f"No se pudo abrir el navegador. "
            f"Reporte disponible en: {ruta}"
        )

    return ruta
