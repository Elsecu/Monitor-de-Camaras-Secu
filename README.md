# Monitor de Cámaras

Aplicación de escritorio para Windows que mide la **latencia** y la **conexión** desde el equipo central hacia todas las cámaras (nodos) de una lista en Excel.

- Ping masivo en paralelo, pensado para ~1,600 cámaras o más.
- Historial de **30 días** con borrado automático.
- Revisión de escaneos pasados, historial por cámara y **tracert individual y grupal**.
- Selección de cámaras mediante casillas y clic en cualquier columna.
- Reportes de Tracert en HTML para impresión o guardado como PDF desde el navegador.
- Exportación a Excel (escaneo actual e historial del mes).

## Funciones

| Función | Cómo se usa |
|---|---|
| Escaneo | **Ejecutar escaneo**: ping a todas las IPs del Excel, en paralelo |
| Cancelar | El mismo botón cambia a **Cancelar escaneo** mientras corre. Un escaneo cancelado **no se guarda** |
| Repetición automática | **Repetir cada N min** (la aplicación debe quedar abierta) |
| Filtrar y ordenar | Lista **Estado**, cuadro **Buscar** (cámara o IP) y clic en un encabezado para ordenar |
| Historial de escaneos | **Ver historial de escaneos**: lista de los escaneos de los últimos 30 días. Doble clic (o **Ver este escaneo**) lo carga en el panel principal |
| Historial de una cámara | Doble clic en la cámara, o clic derecho → *Ver historial de la cámara*. Muestra disponibilidad, promedio, mín y máx, con botones **Copiar nombre** y **Copiar IP** |
| Selección de cámaras | Un clic en cualquier columna marca o desmarca la cámara. El contador indica cuántas están marcadas |
| Selección masiva | Menú **Seleccionar**: marcar visibles, seleccionar por estado o desmarcar todas. La casilla del encabezado alterna las visibles |
| Tracert individual | Marca una cámara con IP válida y pulsa **Tracert individual**, o usa el menú contextual. Los saltos aparecen en vivo; permite detener, repetir, copiar e imprimir |
| Tracert grupal | Marca dos o más cámaras y pulsa **Tracert grupal**. Muestra el avance y un resumen por cámara; permite detener, copiar e imprimir resultados |
| Impresión de Tracert | Abre un reporte HTML en el navegador para imprimir o guardar como PDF |
| Ayuda | Menú **Ayuda → Acerca de**: información de la aplicación |
| Copiar | Clic derecho → *Copiar nombre de la cámara* / *Copiar IP* |
| Exportar (Escaneo actual) | Excel con lo que se ve en el panel (incluye un escaneo pasado cargado desde el historial) |
| Exportar historial (30 días) | Excel con una columna por escaneo (ver [Exportar historial](#exportar-historial-30-días)) |
| Carpeta de datos | Abre la carpeta de la base de datos, configuración y logs |

Las ventanas secundarias son **únicas**: el tracert y el historial de una cámara (una por cámara) y el historial de escaneos. Si ya está abierta, se trae al frente en lugar de abrir otra. La lista de escaneos se actualiza sola cuando termina un escaneo nuevo.

## Selección de cámaras y Tracert

### Selección en la tabla principal

- Un clic izquierdo sobre cualquier parte de una fila marca o desmarca su casilla, sin depender del resaltado azul de Tkinter.
- Doble clic sobre una cámara abre su historial. Se utiliza una breve espera configurable para distinguirlo del clic individual.
- Clic derecho conserva las opciones de historial, Tracert y copia de nombre o IP.
- El encabezado de la primera columna permite marcar o desmarcar las cámaras visibles. Los demás encabezados ordenan la tabla.
- El menú **Seleccionar** permite marcar las visibles, seleccionar por estado o desmarcar todas. Las marcas pueden mantenerse al cambiar el filtro.

| Cámaras marcadas | Tracert individual | Tracert grupal |
|---|---|---|
| 0 | Deshabilitado | Deshabilitado |
| 1 | Habilitado si la IP es válida | Deshabilitado |
| 2 o más | Deshabilitado | Habilitado |

El menú contextual permite abrir un Tracert individual directamente sobre la cámara pulsada, independientemente de las marcas.

### Tracert individual

Muestra los saltos de la ruta hacia la IP de una cámara, sus tiempos de respuesta y notas. Permite detener o repetir la prueba, copiar los resultados e imprimir el reporte.

### Tracert grupal

Ejecuta pruebas en paralelo sobre las cámaras marcadas y muestra una barra de progreso y una tabla con cámara, IP, último salto (IP), total de saltos respondidos y notas. Un doble clic en un resultado permite abrir el Tracert individual correspondiente.

| Parámetro en `config.py` | Valor de referencia |
|---|---:|
| `TRACERT_MAX_SALTOS` | 30 |
| `TRACERT_TIMEOUT_MS` | 4000 ms |
| `TRACERT_MASIVO_CONCURRENTES` | 15 |
| `TRACERT_MASIVO_TIMEOUT_MS` | 4000 ms |
| `TRACERT_MASIVO_SALTOS_SIN_RESPUESTA` | 8 (0 desactiva el corte anticipado) |

Estos valores corresponden a la configuración del proyecto reorganizado y pueden ajustarse según la red.

Un salto sin respuesta no demuestra por sí solo que la ruta esté interrumpida: algunos equipos no responden a ICMP aunque reenvíen tráfico. El ping y el Tracert no verifican directamente la transmisión de video.

### Impresión de resultados

1. Ejecuta el Tracert individual o grupal.
2. Pulsa el botón de impresión en la ventana de resultados.
3. En el navegador, imprime el reporte o selecciona **Guardar como PDF**.

Los reportes se generan en HTML con formato de impresión horizontal, tamaño carta y márgenes de 10 mm. Se reutiliza un archivo temporal por tipo de reporte; guarda una copia en PDF si necesitas conservarlo.

## Excel de entrada

| A | B |
|---|---|
| Nodo | IP |
| Cámara 1-A | 10.1.1.10 |

- La fila 1 es el encabezado y se ignora. Hay un ejemplo en `nodos_ejemplo.xlsx`.
- Solo se aceptan **IPs** (IPv4 o IPv6), no nombres de host.
- Los **nombres deben ser únicos** dentro de cada Excel.
- IP vacía → *No hay IP*. IP mal escrita → *IP invalida*. Las filas sin nombre y sin IP se ignoran.
- **El nombre del archivo identifica la lista** (`norte.xlsx` → lista `norte`). El historial se guarda y se exporta por lista. Si renombras el archivo, cuenta como lista nueva.

## Estados y parámetros

| Estado | Significado |
|---|---|
| OK | Respondió, sin pérdida y con latencia ≤ umbral |
| Lento | Latencia > umbral, o pérdida parcial de paquetes |
| Sin respuesta | No respondió ningún ping |
| No hay IP | La fila no tiene IP |
| IP invalida | El texto no es una IP válida |

| Parámetro | Por defecto | Cuándo cambiarlo |
|---|---|---|
| Intentos (Pings) | 4 | Sube a 10 para más precisión (más lento) |
| Tiempo de espera (s) | 1 | Sube a 2-3 en enlaces lentos (VPN, satélite) |
| Dispositivos simultáneos | 500 | Baja a 200 si ves falsos "Sin respuesta" |
| Lento > (ms) | 150 | Ajústalo a tu red |
| Repetir cada (min) | 15 | Ver [tamaño de la base de datos](#datos-guardados) |

Los parámetros y el último Excel usado se recuerdan al cerrar la aplicación.

## Exportar historial (30 días)

Una fila por cámara y **una columna por escaneo**, de izquierda a derecha en orden cronológico:

| Cámara | Dirección IP | 2026-11-01 10:00 | 2026-11-01 10:15 | 2026-11-02 08:00 |
|---|---|---|---|---|
| Cámara 1-A | 10.1.1.10 | 21.5 | 23.0 | Sin respuesta |
| Cámara 1-B | 10.1.1.11 | | 18.0 | 19.5 |

- **Por lista**: se exporta una sola lista por archivo. Si hay varias, aparece un selector con la lista del Excel cargado preseleccionada. Los registros anteriores a que existieran las listas aparecen como *registros anteriores, sin lista*.
- **Por nombre**: si una cámara cambia de IP o se queda sin IP, sigue en la misma fila. La columna IP muestra la más reciente.
- **Orden de filas**: manda el Excel del último escaneo. Una cámara agregada en medio queda en medio, una movida sigue su nueva posición, y una eliminada queda junto a su vecino con las fechas nuevas vacías.
- **Celdas**: latencia numérica, o el texto del estado. Colores por formato condicional: rojo = sin respuesta, gris = sin IP, amarillo = latencia > umbral (la pérdida parcial no se marca en este Excel).
- Cabeceras y primeras 2 columnas congeladas, con filtro. Máximo 16,000 columnas (límite de Excel 16,384); si hay más, se exportan las más recientes.

## Datos guardados

Carpeta `%APPDATA%\MonitorCamaras\` (botón **Carpeta de datos**):

| Archivo | Contenido |
|---|---|
| `pings.db` | Historial en SQLite. En cada escaneo se borra lo mayor a 30 días |
| `config.json` | Preferencias de la ventana |
| `logs\monitor.log` | Log rotativo (1 MB por archivo). Aquí se revisan los errores |
| `temp/tracert_masivo.html` | Reporte HTML grupal reutilizable |
| `temp/tracert_individual.html` | Reporte HTML individual reutilizable |

Tamaño aproximado de `pings.db` con 1,600 cámaras:

| Intervalo de repetición | Filas en 30 días | Tamaño |
|---|---|---|
| 5 min | ~13.8 M | ~1 GB |
| 15 min | ~4.6 M | ~300-400 MB |
| 30 min | ~2.3 M | ~150-200 MB |
| 60 min | ~1.2 M | ~80-100 MB |

Se recomienda **15 min o más**.

## Instalación y ejecución

Requisitos: Windows y Python 3.10 o superior.

```bat
pip install -r requirements-dev.txt
python main.py                 :: ejecutar (CMD como administrador)
python -m pytest -q            :: pruebas
construir_exe.bat              :: genera dist\MonitorCamaras.exe
```

- El ping ICMP necesita **permisos de administrador**. El `.exe` los pide solo (`--uac-admin`); con `python main.py` abre la consola como administrador.
- El antivirus puede marcar el `.exe` como falso positivo (común con PyInstaller): agrega una excepción.
- El tracert usa `tracert.exe` de Windows (`-d`, con máximo de saltos y tiempo de espera configurables) y no necesita administrador.

## Estructura del proyecto

| Archivo | Responsabilidad | Toca aquí si quieres... |
|---|---|---|
| `main.py` | Arma las dependencias y abre la ventana | Cambiar el arranque |
| `monitor/config.py` | Rutas, constantes (retención, lote, tracert), colores, `Settings` | Cambiar días de retención, colores, límites del tracert |
| `monitor/models.py` | `Nodo`, `Resultado`, `Estado`, `ParametrosPing` | Agregar un estado o un campo |
| `monitor/utils.py` | `es_admin`, `normalizar_ip`, `clave_ip` | Utilidades de IP |
| `monitor/pinger.py` | Ping ICMP masivo y cancelación (`EscaneoCancelado`) | Cambiar el motor de ping |
| `monitor/service.py` | `clasificar()` y `MonitorService.ejecutar()` | Reglas de "Lento", alertas |
| `monitor/tracert.py` | `SesionTracert` y `TracertMasivo`: ejecución, interpretación de saltos y pruebas paralelas | Cambiar el comportamiento del Tracert |
| `monitor/tracert_print.py` | Generación del reporte HTML grupal | Formato de impresión grupal |
| `monitor/tracert_individual_print.py` | Generación del reporte HTML individual | Formato de impresión individual |
| `monitor/about.py` | Información de la aplicación | Datos de Acerca de |
| `monitor/database.py` | SQLite: guardar, purgar, escaneos, historial por cámara, matriz del mes | Nuevas consultas o reportes |
| `monitor/excel_reader.py` | Lee el Excel de cámaras | Nuevas columnas de entrada |
| `monitor/excel_exporter.py` | Exporta el escaneo actual y el historial del mes | Formato de los Excel |
| `monitor/logging_setup.py` | Log rotativo | Nivel de log |
| `monitor/ui/main_window.py` | Ventana principal y coordinación de los módulos de interfaz | Inicialización y ciclo de vida |
| `monitor/ui/main_layout.py` | Construcción de controles, botones, filtros y menús | Distribución visual |
| `monitor/ui/main_navigation.py` | Navegación, ventanas secundarias, marcas y botones de Tracert | Reglas de selección y apertura de ventanas |
| `monitor/ui/main_scanning.py` | Ejecución, cancelación y repetición de escaneos | Flujo de escaneo |
| `monitor/ui/main_exports.py` | Acciones de exportación | Flujo de exportación |
| `monitor/ui/about_dialog.py` | Ventana Acerca de | Presentación de la información |
| `monitor/ui/results_table.py` | Tabla de resultados: colores, filtros, orden, casillas, clic y doble clic, menú contextual | Selección y columnas |
| `monitor/ui/history_window.py` | Historial de una cámara (por nombre) | Detalle por cámara |
| `monitor/ui/scans_window.py` | Lista de escaneos guardados | Navegar escaneos pasados |
| `monitor/ui/tracert_window.py` | Ventana de saltos del Tracert individual | Columnas, botones y colores |
| `monitor/ui/tracert_masivo_window.py` | Ventana de progreso y resultados grupales | Resumen y acciones grupales |
| `monitor/ui/list_picker.py` | Selector de lista para exportar el historial | Selector de lista |
| `monitor/ui/worker.py` | Hilos y cola hacia la interfaz | Tareas en segundo plano |
| `tests/` | Pruebas con pytest | Validar cambios |
| `construir_exe.bat` | Genera el `.exe` con PyInstaller | Nombre o ícono del `.exe` |

Reglas de diseño:

- `ui/` depende de la lógica; la lógica **nunca** importa `ui/`.
- El ping está detrás de la interfaz `Pinger` (`pinger.py`): se reemplaza por un falso en las pruebas.
- Las tareas largas (escaneo, exportación) corren en hilos con `Trabajador`; la ventana lee los resultados con una cola.
- La base de datos abre una conexión por operación, por lo que es segura entre hilos.

Flujo de un escaneo:

```
Excel -> excel_reader -> service (pinger -> clasificar) -> database -> tabla / excel_exporter
```

## Pruebas

`python -m pytest -q` cubre: clasificación de estados, cancelación del escaneo, base de datos (purga, listas, orden de la matriz, migración de bases antiguas), exportaciones a Excel, configuración y el parser del tracert. La interfaz gráfica y el ping real contra equipos no tienen pruebas automáticas.

## Agregar funciones (ejemplos)

| Quiero... | Dónde |
|---|---|
| Un estado nuevo | `models.Estado` + `config.COLOR_ESTADO` + regla en `service.clasificar` |
| Alerta por correo cuando una cámara se cae | Módulo nuevo `monitor/notifier.py`, llamado desde `MonitorService.ejecutar` |
| Otro reporte en Excel | Método en `database.py` + función en `excel_exporter.py` + botón en `main_layout.py` y acción en `main_exports.py` |
| Otra ventana secundaria | Clase en `monitor/ui/` y abrirla con `self._abrir_unica(clave, crear)` en `main_navigation.py` |
| Cambiar el retraso del clic individual | `results_table.py`, método `_click_casilla()`; ajustar `self.after(...)` sin perder la distinción del doble clic |
| Cambiar el diseño de los reportes HTML | `tracert_print.py` y `tracert_individual_print.py` |
| Más saltos o más espera en el tracert | `TRACERT_MAX_SALTOS` y `TRACERT_TIMEOUT_MS` en `config.py` |

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Todas "Sin respuesta" | Sin permisos de administrador | Ejecutar como administrador |
| Algunas "Sin respuesta" que sí están vivas | La cámara bloquea ICMP, o hay saturación | Revisar el firewall de la cámara; bajar "Dispositivos simultáneos" |
| Caracteres raros en las notas del tracert | Página de códigos de la consola | Revisar `_codificacion()` en `tracert.py` |
| La aplicación se cierra o falla algo | Error interno | Revisar `%APPDATA%\MonitorCamaras\logs\monitor.log` |
| `py` no se reconoce | Python sin PATH | Reinstalar Python marcando *Add python.exe to PATH* |
| El `.bat` falla en `pip` | Sin internet o proxy | Ejecutar `pip install -r requirements-dev.txt` manualmente |
| Tracert individual deshabilitado | No hay exactamente una cámara marcada con IP válida | Revisar casillas e IP |
| Tracert grupal deshabilitado | Menos de dos cámaras marcadas | Marcar dos o más cámaras |
| El marcado tarda en aparecer | Espera para distinguir clic y doble clic | Ajustar el intervalo en `_click_casilla()`; si es demasiado corto, el doble clic puede modificar la marca |
| `AttributeError` en métodos de `TablaResultados` | Método ausente o mal indentado | Revisar que los métodos estén dentro de la clase, al mismo nivel |
| El reporte HTML no se abre | Navegador predeterminado o problema de escritura | Revisar la carpeta `temp`, permisos y navegador predeterminado |

## Alcance

La aplicación realiza pruebas de conectividad y diagnóstico de rutas bajo demanda o mediante escaneos programados. No sustituye un sistema de monitoreo de video ni mide bitrate o latencia de transmisión de video.
