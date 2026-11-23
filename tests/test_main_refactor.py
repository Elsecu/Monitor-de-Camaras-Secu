"""Comprueba que la división en módulos conserva los métodos públicos internos."""
from monitor.ui.main_window import VentanaPrincipal


def test_main_window_preserves_callbacks():
    for name in (
        "_crear_widgets", "_tracert_masivo", "_abrir_tracert", "_ejecutar",
        "_alternar_escaneo", "_exportar_actual", "_exportar_mes",
        "_sondear_cola", "_evento_ping", "_cerrar",
    ):
        assert callable(getattr(VentanaPrincipal, name))
