"""Construcción de controles de la ventana principal, sin lógica de escaneo."""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from ..config import DIAS_RETENCION
from ..models import Estado
from .results_table import TablaResultados


class LayoutMixin:
    """Agrupa responsabilidades; los métodos usan el estado de VentanaPrincipal."""

    def _crear_variables(self) -> None:
        """Inicializa las variables de Tkinter usando la configuración guardada."""
        s = self.settings
        self.v_excel = tk.StringVar(value=s.excel)
        self.v_count = tk.StringVar(value=str(s.count))
        self.v_timeout = tk.StringVar(value=str(s.timeout))
        self.v_conc = tk.StringVar(value=str(s.conc))
        self.v_lento = tk.StringVar(value=str(s.lento))
        self.v_auto = tk.BooleanVar(value=s.auto)
        self.v_auto_min = tk.StringVar(value=str(s.auto_min))
        self.v_filtro = tk.StringVar(value="Todos")
        self.v_buscar = tk.StringVar()
        self.v_status = tk.StringVar(value="Listo.")
        self.v_cont = tk.StringVar()

    def _crear_widgets(self) -> None:
        """Construye la ventana y conecta cada botón con su acción."""
        self._crear_menu()
        self._barra_excel()
        self._barra_parametros()
        self._barra_botones()
        self.prog = ttk.Progressbar(self, mode="determinate")
        self.prog.pack(fill="x", padx=8)
        self._barra_filtros()
        self._barra_tracert_masivo()
        self.tabla = TablaResultados(
            self, al_abrir=self._abrir_historial, al_tracert=self._abrir_tracert,
            al_seleccionar=self._actualizar_boton_tracert, al_cambiar_marcas=self._actualizar_marcas)
        self.tabla.pack(fill="both", expand=True, padx=8)
        ttk.Label(self, textvariable=self.v_status, relief="sunken", anchor="w").pack(
            fill="x", side="bottom")

    def _barra_excel(self) -> None:
        """Muestra la ruta del listado de cámaras."""
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        ttk.Label(f, text="Excel del listado de cámaras:").pack(side="left")
        ttk.Entry(f, textvariable=self.v_excel).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(f, text="Elegir...", command=self._elegir_excel).pack(side="left")

    def _barra_parametros(self) -> None:
        """Dibuja los parámetros del ping y del escaneo automático."""
        f = ttk.Frame(self, padding=(8, 0))
        f.pack(fill="x")
        for txt, var, ancho in (("Intentos (Pings)", self.v_count, 4), ("Tiempo de espera (s)", self.v_timeout, 5),
                                ("Dispositivos simultáneos", self.v_conc, 6), ("Lento > (ms)", self.v_lento, 6)):
            ttk.Label(f, text=txt).pack(side="left", padx=(0, 3))
            ttk.Entry(f, textvariable=var, width=ancho).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(f, text="Repetir cada", variable=self.v_auto,
                        command=lambda: setattr(self, "_proxima_auto", time.time())).pack(side="left")
        ttk.Entry(f, textvariable=self.v_auto_min, width=4).pack(side="left", padx=3)
        ttk.Label(f, text="min").pack(side="left")

    def _barra_botones(self) -> None:
        """Crea botones de escaneo, exportación, ayuda y acceso a datos."""
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        self.btn_run = ttk.Button(f, text="Ejecutar escaneo", command=self._alternar_escaneo)
        self._texto_ejecutar = "Ejecutar escaneo"
        self.btn_run.pack(side="left")
        ttk.Button(f, text="Exportar (Escaneo actual)", command=self._exportar_actual).pack(side="left", padx=6)
        ttk.Button(f, text=f"Exportar historial ({DIAS_RETENCION} dias)",
                   command=self._exportar_mes).pack(side="left")
        ttk.Button(f, text="Ver historial de escaneos", command=self._abrir_escaneos).pack(side="left", padx=6)
        self.btn_tracert = ttk.Button(f, text="Tracert individual", command=self._abrir_tracert, state="disabled")
        self.btn_tracert.pack(side="left")
        ttk.Menubutton(f, text="Ayuda", menu=self._menu_ayuda).pack(side="right", padx=6)
        ttk.Button(f, text="Carpeta de datos", command=self._abrir_datos).pack(side="right", padx=(6, 0))

    def _barra_filtros(self) -> None:
        """Crea filtros por estado y búsqueda por texto."""
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        ttk.Label(f, text="Estado:").pack(side="left")
        cb = ttk.Combobox(f, textvariable=self.v_filtro, state="readonly", width=14,
                          values=("Todos",) + Estado.TODOS)
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro())
        ttk.Label(f, text="Buscar:").pack(side="left", padx=(12, 0))
        ent = ttk.Entry(f, textvariable=self.v_buscar, width=28)
        ent.pack(side="left", padx=6)
        ent.bind("<KeyRelease>", lambda e: self._aplicar_filtro())
        ttk.Label(f, textvariable=self.v_cont).pack(side="right")

    def _crear_menu(self) -> None:
        """Prepara el menú de ayuda."""
        ayuda = tk.Menu(self, tearoff=0)
        ayuda.add_command(
            label="Acerca de",
            command=self._abrir_acerca_de
        )

        self._menu_ayuda = ayuda

    def _barra_tracert_masivo(self) -> None:
        """Crea controles para marcar cámaras y ejecutar Tracert grupal."""
        f = ttk.Frame(self, padding=(8, 0, 8, 4))
        f.pack(fill="x")
        ttk.Label(f, text="Camaras seleccionadas:").pack(side="left")
        mb = ttk.Menubutton(f, text="Seleccionar ")
        self._menu_seleccion = tk.Menu(mb, tearoff=0, postcommand=self._armar_menu_seleccion)
        mb["menu"] = self._menu_seleccion
        mb.pack(side="left", padx=6)
        self.v_marcadas = tk.StringVar(value="0 marcadas")
        ttk.Label(f, textvariable=self.v_marcadas, width=13).pack(side="left")
        self.btn_tracert_masivo = ttk.Button(f, text="Tracert grupal",
                                             command=self._tracert_masivo, state="disabled")
        self.btn_tracert_masivo.pack(side="left", padx=6)

