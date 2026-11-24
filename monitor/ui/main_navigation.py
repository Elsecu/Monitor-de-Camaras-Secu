"""Navegación, filtros y selección de cámaras de la ventana principal."""
from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog, messagebox
from ..config import DATA_DIR, TRACERT_MASIVO_CONCURRENTES
from ..excel_reader import leer_nodos
from ..models import Estado
from ..utils import normalizar_ip
from .about_dialog import VentanaAcercaDe
from .history_window import VentanaHistorial
from .scans_window import VentanaEscaneos
from .tracert_masivo_window import VentanaTracertMasivo
from .tracert_window import VentanaTracert


class NavigationMixin:
    """Agrupa responsabilidades; los métodos usan el estado de VentanaPrincipal."""

    def _aplicar_filtro(self) -> None:
        """Actualiza las filas visibles según los filtros seleccionados."""
        self.tabla.filtrar(self.v_filtro.get(), self.v_buscar.get())

    def _actualizar_contadores(self) -> None:
        """Refresca los totales de estados de conexión."""
        c = self.tabla.conteo()
        self.v_cont.set(
            f"Total {len(self.tabla.resultados)} | OK {c[Estado.OK]} | Lento {c[Estado.LENTO]} | "
            f"Sin resp. {c[Estado.SIN_RESPUESTA]} | Sin IP {c[Estado.SIN_IP] + c[Estado.IP_INVALIDA]}")

    def _elegir_excel(self) -> None:
        """Permite elegir el archivo de cámaras."""
        p = filedialog.askopenfilename(title="Excel de nodos",
                                       filetypes=[("Excel", "*.xlsx *.xlsm")])
        if p:
            self.v_excel.set(p)

    def _abrir_datos(self) -> None:
        """Abre la carpeta donde se guardan los datos."""
        try:
            os.startfile(DATA_DIR)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            messagebox.showinfo("Datos", str(DATA_DIR))

    def _abrir_historial(self, nombre: str, ip: str) -> None:
        """Muestra el historial de una cámara."""
        if not nombre and not ip:
            return
        self._abrir_unica(("historial", nombre or ip),
                          lambda: VentanaHistorial(self, self.repo, nombre, ip))

    def _actualizar_boton_tracert(self) -> None:
        """Habilita el Tracert individual según las cámaras marcadas."""

        marcadas = self.tabla.marcadas()

        if len(marcadas) == 1:
            # Comprobar la IP de la única cámara marcada.
            valido = bool(normalizar_ip(marcadas[0].ip))

        elif len(marcadas) > 1:
            # Deshabilitar el Tracert individual si hay varias marcadas.
            valido = False

        else:
            # Si no hay cámaras marcadas, utilizar la fila seleccionada.
            sel = self.tabla.seleccionado()
            valido = bool(sel and normalizar_ip(sel[1]))

        self.btn_tracert.state(
            ["!disabled"] if valido else ["disabled"]
        )

    def _abrir_tracert(
        self,
        nombre: str | None = None,
        ip: str | None = None
    ) -> None:
        """Abre el Tracert individual de una cámara."""

        if ip is None:
            marcadas = self.tabla.marcadas()

            if len(marcadas) == 1:
                # Utilizar la única cámara marcada.
                nombre = marcadas[0].nombre
                ip = marcadas[0].ip

            elif len(marcadas) > 1:
                # Evitar ejecutar el Tracert individual con varias cámaras.
                return

            else:
                # Si no hay marcas, utilizar la fila seleccionada.
                sel = self.tabla.seleccionado()

                if not sel:
                    return

                nombre, ip = sel

        # Validar la dirección IP.
        norm = normalizar_ip(ip)

        if norm is None:
            messagebox.showinfo(
                "Tracert",
                "Esta cámara no tiene una IP válida."
            )
            return

        # Abrir una única ventana de Tracert por cámara.
        self._abrir_unica(
            ("tracert", norm),
            lambda: VentanaTracert(self, nombre or "", norm)
        )

    def _armar_menu_seleccion(self) -> None:
        """Se reconstruye cada vez que se despliega, para mostrar los conteos actuales."""
        m = self._menu_seleccion
        m.delete(0, "end")
        c = self.tabla.conteo()
        visibles = self.tabla.contar_visibles()
        m.add_command(label=f"Las que se muestran en pantalla ({visibles})",
                      command=self.tabla.marcar_visibles,
                      state="normal" if visibles else "disabled")
        m.add_separator()
        for estado in Estado.TODOS:
            n = c.get(estado, 0)
            m.add_command(label=f"Solo las de estado: {estado} ({n})",
                          command=lambda e=estado: self.tabla.marcar_por_estado(e),
                          state="normal" if n else "disabled")
        m.add_separator()
        m.add_command(label="Quitar todas las marcas", command=self.tabla.desmarcar_todo)

    def _actualizar_marcas(self) -> None:
        """Actualiza el contador y los botones de Tracert."""

        # Obtener la cantidad de cámaras marcadas.
        n = self.tabla.contar_marcadas()

        # Actualizar el contador.
        self.v_marcadas.set(f"{n} marcada{'s' if n != 1 else ''}")

        # Habilitar el Tracert grupal con dos o más cámaras.
        self.btn_tracert_masivo.state(
            ["!disabled"] if n >= 2 else ["disabled"]
        )

        # Actualizar también el botón de Tracert individual.
        self._actualizar_boton_tracert()

    def _tracert_masivo(self) -> None:
        """Tracert a todas las camaras marcadas; los resultados salen en una ventana."""
        camaras = [(r.nombre, r.ip) for r in self.tabla.marcadas()]

        # Impedir la ejecución si hay menos de dos cámaras marcadas.
        if len(camaras) < 2:
            return
        v = self._ventanas.get(("tracert_masivo",))
        if v is not None and v.winfo_exists():
            if v.en_curso():
                messagebox.showinfo("Tracert masivo", "Ya hay un tracert masivo en curso. "
                                    "Espera a que termine o pulsa Detener en esa ventana.")
                v.lift()
                return
            v.destroy()                      # el anterior ya termino: se reemplaza
        validas = sum(1 for _, ip in camaras if normalizar_ip(ip))
        if validas > 100 and not messagebox.askyesno(
                "Tracert masivo",
                f"Se ejecutará tracert a {validas} cámaras ({TRACERT_MASIVO_CONCURRENTES} a la vez). "
                "Puede tardar varios minutos. ¿Continuar?"):
            return
        self._abrir_unica(("tracert_masivo",),
                          lambda: VentanaTracertMasivo(self, camaras, self._abrir_tracert))

    def _abrir_acerca_de(self) -> None:
        """Abre información de la aplicación y su listado."""
        ruta = self.v_excel.get().strip()
        try:
            dispositivos = [(n.nombre, n.ip) for n in leer_nodos(ruta)] if ruta and os.path.exists(ruta) else []
        except Exception:  # noqa: BLE001
            dispositivos = []
        lista = Path(ruta).name if dispositivos else ""
        self._abrir_unica(("acerca",), lambda: VentanaAcercaDe(self, lista, dispositivos))

    def _abrir_escaneos(self) -> None:
        """Abre el historial de escaneos guardados."""
        self._abrir_unica(("escaneos",),
                          lambda: VentanaEscaneos(self, self.repo, self._ver_escaneo))

    def _abrir_unica(self, clave, crear):
        """Una sola ventana por clave: si ya esta abierta la trae al frente."""
        self._ventanas = {k: w for k, w in self._ventanas.items() if w.winfo_exists()}
        v = self._ventanas.get(clave)
        if v is not None:
            v.deiconify()
            v.lift()
            v.focus_force()
            return v
        v = self._ventanas[clave] = crear()
        return v

    def _ver_escaneo(self, ts: str) -> None:
        """Carga un escaneo guardado en el panel principal."""
        self.tabla.cargar(self.repo.cargar_escaneo(ts))
        self._aplicar_filtro()
        self._actualizar_contadores()
        self.v_status.set(f"Viendo escaneo guardado: {ts}")

