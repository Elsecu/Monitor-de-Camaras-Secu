"""Pruebas del reporte imprimible, sin abrir el navegador."""
from datetime import datetime

from monitor.tracert_print import crear_reporte_html


def test_reporte_contiene_filas_y_fecha():
    html = crear_reporte_html([("Cam 1", "10.0.0.1", "10.0.0.1", "2", "Exitoso")],
                             datetime(2026, 11, 22, 14, 30))
    assert "Cam 1" in html
    assert "22/11/2026 14:30:00" in html
    assert "window.print()" in html
    assert "Cámaras: 1" in html


def test_escapa_contenido_de_camaras():
    html = crear_reporte_html([("<script>alert(1)</script>", "1.2.3.4", "-", "0", "Sin respuesta")])
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
