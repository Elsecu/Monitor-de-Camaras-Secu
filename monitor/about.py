"""Datos del cuadro 'Acerca de' (sin dependencias de UI)."""
from __future__ import annotations

import importlib
import importlib.metadata
import platform
import sqlite3
import sys

from . import __version__
from .config import PRODUCTO


def _version_modulo(nombre: str) -> str:
    try:
        modulo = importlib.import_module(nombre)
    except Exception:  # noqa: BLE001
        return "no disponible"
    version = getattr(modulo, "__version__", None)
    if version:
        return str(version)
    try:
        return importlib.metadata.version(nombre)
    except Exception:  # noqa: BLE001
        return "desconocida"


def componentes() -> list[tuple[str, str]]:
    """(nombre, version) del producto y de los componentes que usa."""
    try:
        import tkinter
        tk_version = str(tkinter.TkVersion)
    except Exception:  # noqa: BLE001
        tk_version = "no disponible"
    return [
        (PRODUCTO, __version__),
        ("Python", sys.version.split()[0]),
        ("Tk (GUI)", tk_version),
        ("icmplib", _version_modulo("icmplib")),
        ("openpyxl", _version_modulo("openpyxl")),
        ("SQLite", sqlite3.sqlite_version),
        ("Sistema operativo", "Windows 10 o superior"),
    ]
