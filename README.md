# ARQ GEN V2

**Sistema profesional de escritorio y web para arquitectura, ingeniería, construcción y seguridad.**
**Versión 2.0.0 · Generador de Arquitectura Sin IA V2 + Catálogo Oficial PRECONS III + Normas Cubanas (NC) + Web Studio 2D/3D** (100% funcional, determinista y trazable).

---

## 1. Novedades de la Versión 2.0.0

| Pilar V2 | Estado | Detalle |
|---|---|---|
| **Generador de Arquitectura Sin IA V2** | ✔ nuevo | Generación procedural determinista de plantas completas sin redes neuronales ni alucinaciones: zonificación ortogonal (Social, Servicios, Privada), trazado automático de muros perimetrales e interiores, dimensionamiento normativo de puertas y ventanas, integración automática de redes coordinadas MEP (Electricidad, Agua Fría, Drenaje, SADI, CCTV), cálculo QTO instantáneo y exportación DXF/IFC. Comando `main.py generate`. |
| **Instalaciones MEP, Bioclimático y Seguridad (Normas Cubanas)** | ✔ nuevo | Motores normativos de ingeniería: **Bioclimático** (clima tropical Cuba Aw, orientación solar, aleros y ratios NC de iluminación &ge;10% y ventilación &ge;5%), **Hidráulico y Sanitario** (dotación cubana 200 L/hab/d, cisterna para 2.5 días, tanque elevado, bomba HP, Hunter UF y fosa séptica), **Cuadro Eléctrico 120/240V 60Hz** (circuitos C1-C5, alimentador, breakers y verificación &Delta;V &le; 3%), **SADI** (detección humo/calor, pulsadores, sirenas, batería 24h+30min según NC 96 / NFPA 72), **SACI** (extintores PQS ABC 6kg, CO2, gabinetes BIE y agua de incendio) y **CCTV** (cámaras IP 4MP H.265, 30 días de grabación en TB, switch PoE y Cat6). Comandos `mep bioclimatic|hydraulic|electrical|sadi|saci|cctv`. |
| **Catálogo PRECONS III Oficial (RoPres 3.30)** | ✔ nuevo | Base de datos indexada con FTS5 de los **15,981 renglones variantes** y **4,383 recursos** (materiales, equipos, mano de obra) con precios oficiales CUP y coeficientes de transporte, indirectos y utilidad. Búsqueda en <1 ms y cálculo de APU. Comandos `precons catalogo-search|item|recursos|apu|build`. |
| **Cálculos y Normas Cubanas (NC)** | ✔ nuevo | **NC 207 / NC 450** (vigas a flexión/cortante y columnas con diagrama de interacción P-M y cuantías de acero), **NC 285** (cargas de viento por provincias de Cuba, ráfaga y presiones barlovento/sotavento) y **NC 46** (espectro sísmico y cortante basal por zonas de peligrosidad). Comandos `struct nc-viga|columna|viento|sismo`. |
| **ArqGen V2 Web Studio (2D CAD & 3D BIM & MEP)** | ✔ nuevo | Aplicación web interactiva en puerto 3000 con **Lienzo 2D CAD** con capas conmutables (Arq, Elec, Agua, Drenaje, SADI, CCTV), **Visor 3D BIM** (Three.js WebGL con sombras y control orbital), wizard del generador con informe bioclimático, explorador PRECONS y banco de cálculo de Normas Cubanas. |
| **Multiplataforma y Modo Headless** | ✔ optimizado | Módulos desacoplados de `tkinter` para ejecución fluida en Linux, servidores, contenedores y CI/CD sin display (suite de 453 pruebas unitarias pasando al 100%). |

| Componente | Estado | Detalle |
|---|---|---|
| Núcleo (CORE) | ✔ completo | Entidades con UUID persistentes, códigos humanos (`ARQ-WALL-001`), unidades con control de dimensiones, eventos, Command Bus con undo/redo transaccional, motor de reglas con lenguaje de fórmulas seguro (sin `eval`), validación, grafo de dependencias, auditoría, versionado, backups, permisos, sistema de plugins |
| Motor geométrico 2D | ✔ completo | Point/Line/Polyline/Arc/Circle/Ellipse/Polygon + `distance, angle, area, perimeter, centroid, intersection, contains, overlaps, offset, trim, extend, split, join, fillet, chamfer, mirror, rotate, translate, scale, project, nearest_point, bounding_box` + reparación geométrica con el patrón DETECTAR→EXPLICAR→PROPONER→APROBAR→APLICAR→REVALIDAR |
| Modelo semántico | ✔ completo | Project→Site→Building→Level→Zone→Space→Wall→Door/Window/Opening + relaciones entre locales como entidades + Space DNA (conocimiento técnico en JSON) |
| Persistencia | ✔ completo | SQLite con migraciones versionadas y reversibles, repositorios indexados, backup con verificación de integridad |
| Módulo Arquitectura | ✔ completo | Niveles, zonas, locales, muros, puertas, ventanas; relaciones espaciales por geometría; adyacencias con explicación |
| QTO (cómputo) | ✔ completo | Fórmulas paramétricas en datos (JSON), cantidades con origen trazable, desperdicio, recálculo **incremental** por hash de entrada |
| Precios y presupuesto | ✔ completo | Listas de precios con histórico (nunca se sobrescribe un precio), recursos, capítulos/partidas/recursos, directos + indirectos + otros = total |
| Interoperabilidad | ✔ completo | Exportación **DXF** (ezdxf, capas ARQ-*, un layout por nivel), **XLSX** (openpyxl), **CSV**, **JSON** (ida y vuelta completa) |
| Instalaciones (FASES 10–13) | ✔ completo | **Módulo INSTALLATIONS CORE**: redes Nodo→Tramo con trazado, caminos de coste mínimo, validación topológica (árbol radial/sumaidero) y detección de finales muertos; **motor de rutas** ortogonal determinista con obstáculos (muros), cruces, holguras y corredores preferentes; **motor eléctrico** (corrientes 1φ/3φ, factores de demanda, caída de tensión IEC, protecciones normalizadas, secciones con coordinación In≤Iz, canalización al 40%, balanceo de fases); **motor sanitario** (caudales con simultaneidad, Hazen-Williams, Manning en gravedad, diámetros y pendientes por tabla, bombeo TDH/potencias, tanques); **motor HVAC** (carga térmica por componentes, caudal de aire, ductos circulares/rectangulares, selección de equipos del catálogo). Todo integrado con QTO (13 fórmulas nuevas), presupuesto (capítulos 03–05), eventos, auditoría, undo/redo y validación |
| Pluviales, gas y telecom (FASES 14–16) | ✔ completo | **Pluviales**: método racional de captación, canalón tipo canal rectangular (Manning), bajantes por tabla, colectores Manning al 50%, tanque de detención V=Q·t y evacuación con margen 10%. **Gas**: caudal por PCI y unidades de consumo, Darcy-Weisbach con catálogo de DN, velocidad máxima, validaciones de válvulas por aparato, ventilación 1/50 del suelo, separación gas-eléctrico y recorridos. **Telecom**: llenado de canalización ≤40%, enlace horizontal TIA-568 de 90 m, rack U, puertos patch/switch, presupuesto óptico de fibra. QTO con 10 fórmulas nuevas y comandos `plu/gas/tel` |
| Estructura (FASES 17) | ✔ completo | Materiales (hormigón/acero/mampostería/madera), secciones rectangulares/circulares/perfil I con propiedades, acciones y combinaciones ULS/SLS (1,35G+1,5Q, viento, sismo), vigas isostáticas y empotradas (reacciones, cortante, momento, flecha elástica), pilares (esbeltez, pandeo de Euler, utilización), torsión circular, **cerchas por método de los nudos** con solver gaussiano determinista, uniones (pernos y soldadura), cantidades de acero, QTO (CONCRETE_VOLUME/STEEL_WEIGHT/FORMWORK_AREA) y comandos `struct` |
| Seguridad (FASES 18–23) | ✔ completo | **FOV**: cono de cobertura por ray casting contra muros, puntos ciegos por retícula, solapamientos, detección de objetivos y candidatos de optimización. **CCTV**: cableado (ruta + rulo + desnivel + reserva), ancho de banda, PoE, almacenamiento y retención, capacidad switch/NVR. **Fuego**: cobertura de detectores por local, carga de lazo, batería 24 h + alarma, matriz **causa/efecto** parametrizada por ruleset. **Intrusión**: zonas, PIR por área, contactos, panel, batería y sirenas. **Acceso**: controladores, alimentación, batería y liberación de evacuación fail-safe. **Perímetro**: sensores de valla, cámaras y accesos. BOM de seguridad, QTO (14 fórmulas) y comandos `sec` |
| Coordinación y clash (FASES 24–25) | ✔ completo | Motor de interferencias determinista: HARD (dentro de muro), SOFT (proximidad), CLEARANCE (holgura), ACCESS (frente de maniobra), MAINTENANCE (zona de retiro) y ROUTE (cruce de rutas); entidad Clash con ciclo de vida OPEN→REVIEWED→ACCEPTED/RESOLVED/IGNORED, deduplicación por par de objetos, eventos CLASH_CREATED/CLASH_RESOLVED y comandos `clash` |
| PRECONS / SIECONS-like (FASES 30–31) | ✔ completo | Ruleset **versionado** de partidas/indicadores/recursos/rendimientos/precios (datos JSON, no tablas rígidas), análisis de precio unitario con coeficientes de transporte, indirectos y beneficio, takeoff por partida, análisis del proyecto alimentado por QTO, variantes (BASE/ECONOMIC/PREMIUM) con comparación, actualización de precios e **importador/mapeador** de bases externas por mapa de columnas; comandos `precons` |
| Importación externa (spec 94, v1.7.0) | ✔ nuevo | **Pipeline completo de 9 etapas** (DETECTAR→PARSE→VALIDAR→MAPEAR→CONVERTIR→PREVIEW→APROBAR→IMPORTAR→AUDITAR) sobre archivos externos: **catálogos PRECONS** (.xlsx/.csv/.json → ruleset con autodetección de hojas/columnas por sinónimos, mapa explícito opcional, importación plana por partida+insumo o multi-hoja con recursos/rendimientos/precios) y **planos DXF** (LINE→muros, LWPOLYLINE cerrada→locales con nombre desde TEXT/MTEXT, capas por pista muro/wall y local/space o capas explícitas). Siempre PREVIEW antes de APLICAR; la aplicación es transaccional (CommandBus), audita `IMPORT_DXF`/import y emite eventos. Comando `importar catalogo|dxf`; `precons import` acepta ahora .xlsx/.csv |
| BIM e IFC (FASES 32–33) | ✔ completo | Modelo BIM interno ligero: cada objeto proyecta categoría, geometría, nivel, material, propiedades, clasificación, sistemas y relaciones (spec 63); árbol espacial Project→Site→Building→Storeys; **exportador IFC4 SPF** (ISO 10303-21) con IfcProject/IfcSite/IfcBuilding/IfcBuildingStorey/IfcSpace/IfcWall/IfcDoor/IfcWindow/IfcOpeningElement/IfcBeam/IfcColumn/IfcMember/IfcDistributionElement, IfcRelAggregates/ContainedInSpatialStructure/VoidsElement/FillsElement y GlobalIds deterministas; comandos `bim` y `export --format ifc` |
| Documentación (FASES 34) | ✔ completo | **Motor de planos** (spec 69): entidad Drawing con hoja, formato A0–A4, escala normalizada, orientación, vista, capas, anotaciones (Dimension/Text/Leader/Symbol/Hatch/Block/Viewport) y cajetín automático; **documentos paramétricos** (spec 70): plantillas con variables `{{PROJECT.NAME}}`, `{{CLIENT.NAME}}`, `{{BUDGET.TOTAL}}`, `{{QTO.TOTAL_WALL_AREA}}`… con validación estricta de variables sin resolver; **generación de documentos** (spec 68): memoria descriptiva, memoria técnica, especificaciones, cuadros de superficies/vanos, listados e informe de interferencias, en Markdown/HTML deterministas; **documentación automática por módulo** (spec 106): README/API/DATA MODEL/RULES/FORMULAS/TESTS/CHANGELOG; comandos `docs` |
| Optimización multiobjetivo (FASES 35) | ✔ completo | Motor del spec 19: los **12 objetivos** (AREA, COST, DISTANCE, CIRCULATION, LIGHTING, VENTILATION, PRIVACY, ACCESSIBILITY, SECURITY, MAINTENANCE, MATERIAL, COMPLEXITY) evaluados sobre el modelo con su dirección (minimizar/maximizar), **sin score mágico**; dominancia de Pareto, frente no dominado, comparación objetivo a objetivo con deltas y rangos; variantes cargables desde JSON; comandos `optimize` |
| Auditoría, versiones y backup (FASES 36–38) | ✔ completo | Auditoría filtrable (usuario, comando, tipo, objeto, rango de fechas) con estadísticas y exportación CSV/JSON (spec 71); versionado completo save/list/restore/**compare/export/branch** (spec 80) con backup automático previo a restaurar; backup **autosave rodante**, **incremental por hash SHA-256 con manifiesto**, estado y checkpoint del journal WAL, verificación de todas las copias y **recuperación automática** de proyectos corruptos conservando copia forense (spec 81); comandos `audit show|stats|export`, `version …`, `backup …` |
| Plugins y rendimiento (FASES 39–40) | ✔ completo | Contrato de plugins (spec 88-89) con **validación estática sin ejecutar**, información detallada de declaraciones y **andamiaje generador** de plugins externos; rendimiento (spec 86-87): suite de **benchmark determinista** de 8 operaciones (geometría, adyacencias, QTO, presupuesto, optimización, documentación, clash, exportación) con ops/s y **inventario de las 6 cachés** (geometry/rules/catalog/calculation/routing/coverage) con sus claves de invalidación; comandos `plugins validate|info|new` y `benchmark run|caches` |
| QA final (FASES 41–43) | ✔ completo | Suite de **305 pruebas** con valores dorados (presupuesto, IFC, QTO, PRECONS, demanda eléctrica, acero), TEST-021 Documentación y TEST-024 Recuperación cubiertos; selftest de **23 comprobaciones**; empaquetado PyInstaller onedir verificado |
| Interfaz | ✔ completa (CLI) | Consola profesional con más de 100 comandos; mensajes en español; códigos de salida para scripts |

**Fuera del alcance** hasta el cierre del plan maestro: solo la interfaz gráfica de ventanas (§90), preparada para engancharse a las fachadas de servicios existentes (spec 90-93). Todas las fases de dominio del plan maestro (1-43) están entregadas y funcionales.

---

## 2. Requisitos

- Windows 10/11 (los .bat también funcionan en Windows 8.1 con PowerShell disponible)
- **Python 3.13** instalado desde https://www.python.org/downloads/ (marcar *Add python.exe to PATH*)
- Solo para `01_INSTALAR_DEPENDENCIAS.bat`: internet una vez. Después, todo offline.

---

## 3. Instalación y uso (en orden)

| Paso | Archivo | Qué hace |
|---|---|---|
| 1 | `00_VERIFICAR_ENTORNO.bat` | Detecta Python 3.13 (`py -3.13` → `python3.13` → `py` → `python`), verifica versión y biblioteca estándar, guarda la elección en `config\python_home.txt`. **Registra todo en `logs\setup\`** |
| 2 | `01_INSTALAR_DEPENDENCIAS.bat` | Crea el entorno virtual `.venv`, instala `ezdxf`, `openpyxl` y `pyinstaller` con pip. Congela versiones instaladas en `logs\setup\pip_freeze_*.txt`. **Ejecutar UNA vez (con internet)** |
| 3 | `02_PRUEBAS.bat` | Ejecuta la suite completa (439 pruebas) → `logs\tests\run_*.log`. Sale con error si algo falla |
| 4 | `03_COMPILAR.bat` | Pipeline completo con logs en las tres etapas: **pruebas antes** (`logs\tests\pre_build_*.log`) → **compilación PyInstaller** (`logs\build\build_*.log`) → **selftest del ejecutable después** (`logs\tests\post_build_*.log`). Si algo falla, se detiene y muestra el log correspondiente. Genera `dist\ARQ_GEN\ARQ_GEN.exe` |
| 5 | `04_EJECUTAR.bat` | Ejecuta la CLI en modo desarrollo (Python local) |
| 6 | `05_EJECUTAR_COMPILADO.bat` | Ejecuta el `ARQ_GEN.exe` compilado |
| 7 | `06_DEMO.bat` | Genera el proyecto demo completo y exporta DXF/XLSX/JSON/CSV a `output\` |
| 8 | `07_LIMPIAR.bat` | Limpia `build\`, `dist\` y cachés (no toca proyectos, backups ni logs) |
| 9 | `08_GUI.bat` | Abre la interfaz gráfica en modo desarrollo (FASE 90, spec 90-93); sin argumentos carga el proyecto de demostración |
| 10 | `09_GUI_COMPILADO.bat` | Abre la **interfaz gráfica del ejecutable compilado** (`ARQ_GEN.exe gui`) — no necesita Python instalado; es la forma recomendada de trabajar a diario |

**Variables opcionales:**
- `set ARQ_PY_EXE=C:\ruta\a\python.exe` — usar un intérprete concreto (ruta completa).
- `set ARQ_ALLOW_OTHER_PYTHON=1` — permitir un Python 3.x distinto de 3.13.
- `set ARQ_NOPAUSE=1` — desactiva las pausas de los .bat (para automatización).

### Solución de problemas de los .bat (v1.6.4)

**Historial de incidencias resueltas:**

- *v1.6.0 y anteriores* — los .bat se distribuían con fin de línea de Unix (LF): **cmd.exe los abortaba de inmediato —la ventana se cerraba sin hacer nada— y no se creaba ningún log**.
- *v1.6.1* — los textos de error dentro de bloques `if (...)` incluían paréntesis literales, p. ej. `echo [ERROR] Etapa 1 (pruebas...) fallida`. En cmd.exe un `)` sin comillas **cierra el bloque aunque esté dentro del texto**: el pipeline de compilación abortaba justo tras las pruebas previas y **nunca llegaba a compilar** (la carpeta `logs\build\` quedaba vacía).
- *v1.6.2* — ambos defectos corregidos y **congelados por tests**: la suite verifica byte a byte CRLF/ASCII/sin BOM y **parsea los bloques de los 9 scripts** prohibiendo paréntesis literales dentro de ellos.
- *v1.6.3* — la compilación fallaba con `ERROR: Aborting build process due to attempt to collect multiple Qt bindings packages`. **Causa**: la librería ezdxf contiene un import perezoso de Qt (`ezdxf.npshapes` → `ezdxf.addons.xqt`) que PyInstaller detecta en su análisis estático; si en el equipo están instalados **PySide6 y PyQt5 a la vez** (típico en un Python global usado para otros proyectos), PyInstaller se niega a empaquetar ambos. **Solución**: `03_COMPILAR.bat` ahora excluye todos los bindings Qt (`--exclude-module PySide6/PyQt5/PyQt6/PySide2` + sus companions) — ARQ GEN usa Tkinter, no Qt — así que la compilación funciona **independientemente de lo que haya instalado en el equipo**. Verificado reproduciendo el entorno conflictivo (ambos bindings instalados).
- *v1.6.4* — «compila y funciona pero no aparece la interfaz»: el ejecutable es una app de consola; **la ventana gráfica siempre existió pero faltaba la ruta obvia para abrirla**. Desde esta versión: (1) **doble clic sobre `ARQ_GEN.exe` abre la ventana directamente**, (2) nuevo `09_GUI_COMPILADO.bat` que lanza la GUI sin Python, (3) `05_EJECUTAR_COMPILADO.bat` anuncia cómo abrir la GUI en su ayuda. La presencia real de Tkinter en el ejecutable queda verificada en la etapa 3 del pipeline (selftest con ventana Tk real).

**Garantías desde v1.6.4:**

- **La ventana ya no desaparece**: cualquier error queda en pantalla (`pause`) hasta pulsar una tecla.
- **Latido de arranque**: cada .bat escribe `INICIO`/`FIN` en `logs\bat_boot.log` nada más arrancar; si ese archivo no se crea, el script no llegó a ejecutarse (ZIP viejo o bloqueo de SmartScreen).
- **Detección de Python reforzada**: si falta `config\python_home.txt`, los .bat autodetectan el intérprete (`py -3.13` → `python3.13` → `py` → `python` → `python3`), lo normalizan a su **ruta completa** y lo validan (descarta el alias trampa de Microsoft Store y rutas rotas).
- **Rutas con espacios**: todo se invoca entre comillas (funciona con `C:\Program Files\Python313\python.exe`).
- **«Ejecutar como administrador»**: todos los scripts cambian primero al directorio del propio .bat (`cd /d "%~dp0"`).
- **04/05 sin argumentos** muestran la ayuda de la CLI en lugar de cerrarse solos.
- **La interfaz gráfica siempre alcanzable**: doble clic en el exe, `09_GUI_COMPILADO.bat` o `ARQ_GEN.exe gui`; y desde desarrollo con `08_GUI.bat`.
- **Automatización**: `set ARQ_NOPAUSE=1` desactiva las pausas; si PowerShell está bloqueado por política, la marca de tiempo de los logs usa un fallback interno.

Diagnóstico rápido si un .bat fallara:

1. Abra `logs\bat_boot.log`: si su `INICIO` no aparece, está ejecutando un ZIP antiguo — extraiga el ZIP actual en una carpeta nueva.
2. La ventana permanece abierta: lea el mensaje de error final.
3. Consulte el log de la etapa correspondiente en `logs\` (tabla de la sección 5).
4. Si Windows SmartScreen bloquea el script descargado: clic derecho sobre el .bat → **Propiedades** → casilla **Desbloquear** → Aceptar.
5. La integridad de los 10 .bat se verifica automáticamente: `02_PRUEBAS.bat` incluye 18 pruebas de integridad (CRLF, ASCII, BOM, pausas, paréntesis en bloques, latido, exclusión de bindings Qt, lanzador de GUI compilada) y el selftest la comprobación 27 «scripts .bat».
6. Si la compilación mostrara `multiple Qt bindings`, descargue el ZIP **1.6.3 o superior**: las exclusiones Qt van incluidas desde esa versión.

---

## 4. Primeros pasos con la CLI

```bat
06_DEMO.bat
05_EJECUTAR_COMPILADO.bat project info output\demo.arqgen
08_GUI.bat
```

Crear un proyecto desde cero:

```bat
04_EJECUTAR.bat project create proyectos\mi_obra.arqgen --name "Casa Demo" --client "Cliente" --ruleset international_v1
04_EJECUTAR.bat level add proyectos\mi_obra.arqgen --name "Nivel 1" --elevation 0 --height 3
04_EJECUTAR.bat space add proyectos\mi_obra.arqgen --level "Nivel 1" --name Sala --type LIVING_ROOM --polygon 0,0 6,0 6,5 0,5
04_EJECUTAR.bat wall add proyectos\mi_obra.arqgen --level "Nivel 1" --start 0,0 --end 6,0 --thickness 0.2
04_EJECUTAR.bat door add proyectos\mi_obra.arqgen --wall ARQ-WALL-001 --width 0.95 --height 2.10 --offset 1.0
04_EJECUTAR.bat relationships recompute proyectos\mi_obra.arqgen
04_EJECUTAR.bat validate proyectos\mi_obra.arqgen
04_EJECUTAR.bat qto compute proyectos\mi_obra.arqgen
04_EJECUTAR.bat resource add proyectos\mi_obra.arqgen --code BLOQUE-20 --name "Bloque 20" --type MATERIAL --unit und
04_EJECUTAR.bat price set proyectos\mi_obra.arqgen --resource BLOQUE-20 --price 32.50 --list GENERAL
04_EJECUTAR.bat budget compute proyectos\mi_obra.arqgen --template residential_full_v1
04_EJECUTAR.bat export proyectos\mi_obra.arqgen --format dxf --out planos\planta1.dxf
```

Instalaciones desde cero (red eléctrica de ejemplo):

```bat
04_EJECUTAR.bat net add proyectos\mi_obra.arqgen --name "Fuerza" --system POWER
04_EJECUTAR.bat node add proyectos\mi_obra.arqgen --network MEP-NETWORK-001 --kind PANEL --x 0.5 --y 0.5 --attr voltage=220 phases=1 main_breaker_a=63
04_EJECUTAR.bat node add proyectos\mi_obra.arqgen --network MEP-NETWORK-001 --kind PROTECTION --x 1 --y 0.5 --attr rating_a=16 kind_circuit=POWER
04_EJECUTAR.bat node add proyectos\mi_obra.arqgen --network MEP-NETWORK-001 --kind OUTLET --x 4 --y 3 --space ARQ-SPACE-001 --attr power_w=600
04_EJECUTAR.bat link add proyectos\mi_obra.arqgen --network MEP-NETWORK-001 --from MEP-NODE-001 --to MEP-NODE-002 --kind CONDUIT --attr conductors=3 spare_pct=10
04_EJECUTAR.bat link add proyectos\mi_obra.arqgen --network MEP-NETWORK-001 --from MEP-NODE-002 --to MEP-NODE-003 --kind CONDUIT --attr conductors=3 spare_pct=10
04_EJECUTAR.bat net validate proyectos\mi_obra.arqgen --network MEP-NETWORK-001
04_EJECUTAR.bat elec summary proyectos\mi_obra.arqgen --panel MEP-NODE-001
04_EJECUTAR.bat elec check proyectos\mi_obra.arqgen --circuit MEP-NODE-002
04_EJECUTAR.bat qto compute proyectos\mi_obra.arqgen   (las redes alimentan el cómputo)
```

Sanitaria y HVAC:

```bat
04_EJECUTAR.bat san size proyectos\mi_obra.arqgen --network MEP-NETWORK-002   (caudales, diámetros, bombeo)
04_EJECUTAR.bat hvac load proyectos\mi_obra.arqgen --space Sala               (carga térmica + equipo)
04_EJECUTAR.bat hvac loads proyectos\mi_obra.arqgen                            (tabla de los 4 locales)
04_EJECUTAR.bat hvac duct proyectos\mi_obra.arqgen --flow 800 --kind MAIN     (dimensionado puntual)
04_EJECUTAR.bat hvac size-network proyectos\mi_obra.arqgen --network MEP-NETWORK-004
```

### Comandos V2.0.0: MEP, Bioclimático y Seguridad Integral (Normas Cubanas)

```bash
# 1. Análisis Bioclimático (Cuba tropical Aw, orientación solar, aleros y ratios NC de iluminación/ventilación)
python main.py mep bioclimatic --ancho 10 --fondo 8 --orientacion SUR

# 2. Dimensionamiento Hidrosanitario (NC dotación 200 L/hab/d, cisterna 2.5d, bomba, Hunter y fosa séptica)
python main.py mep hydraulic --habitantes 5 --dias 2.5

# 3. Cuadro Eléctrico 120/240V 60Hz (cargas de demanda, interruptor ppal, alimentador y caída de tensión <= 3%)
python main.py mep electrical --area 85 --ac-units 2

# 4. SADI Detección Automática de Incendios (NC 96 / NFPA 72: detectores humo/calor, pulsador, sirena, batería)
python main.py mep sadi --area 85

# 5. SACI Extinción Manual (NC 96 / NFPA 10: extintores PQS ABC 6kg, CO2 panel eléctrico, BIE, reserva fuego)
python main.py mep saci --area 85 --riesgo LEVE

# 6. Seguridad Electrónica CCTV (cámaras IP 4MP H.265, 30 días almacenamiento continuo en TB, switch PoE, Cat6)
python main.py mep cctv
```

### Interfaz gráfica (FASE 90, spec 90-93; editable desde v1.6.0)

Tres formas de abrirla:

- **Ejecutable compilado (recomendado)**: `09_GUI_COMPILADO.bat`, o doble clic sobre `dist\ARQ_GEN\ARQ_GEN.exe` — el exe sin argumentos abre la ventana directamente; no necesita Python.
- **Modo desarrollo**: `08_GUI.bat` o `python main.py gui [archivo] [--demo] [--width N --height N]`.
- **CLI**: `ARQ_GEN.exe gui [archivo] [--demo] [--width N --height N]`.

**Novedades v1.7.1 — interfaz guiada y tema oscuro:**

- **Tema oscuro moderno con letras claras**: paleta centralizada en `ui/theme.py` (fondo profundo, paneles en capas, acento azul amable, lienzo con rejilla y colores de entidades ajustados para contrastar). Todos los widgets ttk, menús, treeviews, pestañas y scrollbars comparten el mismo lenguaje visual.
- **Ayuda dinámica en cada control**: al detener el cursor sobre cualquier botón, campo o panel aparece un globo de ayuda con una explicación breve Y la misma frase se fija en la barra de estado inferior. Al abrir cualquier menú superior (Archivo, Editar, Ver, Herramientas, Ayuda), la barra de estado explica para qué sirve.
- **Flujo no abrumador**: la barra de estado sugiere siempre el siguiente paso natural (crear el primer local → muros → puertas → calcular → validar → exportar) según el estado real del proyecto. La interfaz habla en tono cercano: «¿Fue un error? Ctrl+Z lo recupera al instante», «Validación limpia: todo en orden».
- **Guía rápida (F1 o botón «Guía rápida»)**: recorrido de 4 pasos que explica la pantalla entera en lenguaje sencillo.
- **Panel de bienvenida**: un proyecto vacío ya no es un lienzo en blanco: muestra una tarjeta con los 4 pasos y la invitación a cargar el proyecto de demostración.
- **Formularios con ayuda por campo**: cada campo de creación y edición muestra su explicación («Espesor del muro en metros (0.2 = 20 cm)»), y los obligatorios están marcados con *.
- **Barra de estado con dos canales**: a la izquierda la orientación dinámica (mensajes y ayudas), a la derecha los datos técnicos (proyecto · disciplina · objetos en el plano) y las coordenadas de mundo bajo el cursor.

Funcionalidad consolidada:

- **Ventana §90**: menú · barra de herramientas · explorador | lienzo | propiedades · pestañas Avisos/Log/Estado de cálculos + barra de estado con coordenadas de mundo en metros bajo el cursor.
- **Navegación §91**: las 13 disciplinas; filtro por nivel para Arquitectura.
- **Buscador §92**: los 9 campos del spec; `Enter` busca, `Escape` limpia, `Ctrl+F` salta al buscador.
- **Estados §93**: cambio de estado con transiciones validadas, auditoría y evento.
- **Edición (v1.6.0)**: doble clic en una fila editable (marcada con ✎) o botón «Editar propiedad…» (`Ctrl+E`) modifica campos en lista blanca por tipo (locales, muros, vanos, nodos, materiales, secciones, elementos…). Cada edición audita `UPDATE_ENTITY` con snapshots completos y es reversible con `Ctrl+Z`.
- **Creación (v1.6.0)**: «Nuevo objeto…» abre formularios declarativos por tipo (local, muro, puerta, ventana, nivel, zona, material, sección, elemento, red, nodo), con menús desplegables dinámicos (niveles, muros, redes, sistemas) y por las mismas fachadas que la CLI.
- **Borrado (v1.6.0)**: tecla `Supr` o menú Editar → «Eliminar selección», con confirmación, cascadas (muro→vanos, nodo→tramos, red→todo) y undo persistente.
- **Lienzo**: zoom anclado al cursor con la rueda, desplazamiento con botón central o derecho, clic para seleccionar, doble clic en vacío para encuadrar (`F`), cuadrícula adaptativa de 1/5/25 m.
- **Atajos**: `Ctrl+N/O/S`, `Ctrl+Z/Y`, `Ctrl+F`, `Ctrl+E`, `Supr`, `+`/`−`, `F`, `Escape`, `F1` (**guía rápida**; listados en Ayuda → Atajos de teclado).
- **Herramientas**: validación, recálculo de QTO/presupuesto, «Recalcular todo», e informe del proyecto en Markdown.

### Importación de archivos externos (spec 94, v1.7.0)

El pipeline completo de 9 etapas ya no se limita a instantáneas JSON. Dos puertas de entrada nuevas:

- **Catálogo PRECONS → ruleset** (sin proyecto abierto):

  ```bat
  python main.py importar catalogo Catalogo_PRECONS_III_Completo.xlsx
  python main.py importar catalogo Catalogo_PRECONS_III_Completo.xlsx --code PRECONS_III --out resources\rulesets\precons_iii.json
  ```

  Detecta automáticamente hojas (PARTIDAS/RECURSOS/RENDIMIENTOS/PRECIOS) y columnas por sinónimos (Código, Descripción, UM, Insumo, Rendimiento, Merma…); entiende el formato plano (una fila por partida+insumo) y el multi-hoja. Si el autodetect falla, pase un mapa JSON con `--mapping` (claves `items_sheet`, `resources_sheet`, `indicators_sheet`, `prices_sheet`, `columns`). Sin `--out` solo muestra el PREVIEW; los precios detectados se reportan (se cargan al proyecto con `price set`).
- **DXF → muros y locales** (proyecto abierto):

  ```bat
  python main.py importar dxf plano.dxf --file proyecto.arqgen --nivel PLANTA_1
  python main.py importar dxf plano.dxf --file proyecto.arqgen --nivel PLANTA_1 --aplicar
  ```

  LINE en capas de muro (`muro`/`wall`) → muros; LWPOLYLINE cerrada en capas de local (`local`/`space`/`hab`/`ambiente`) → locales (el nombre sale del TEXT/MTEXT contenido dentro, o `LOCAL-001`); capas explícitas con `--capa-muros`/`--capa-locales`; espesor uniforme con `--espesor`. Sin `--aplicar` es solo PREVIEW (ninguna entidad se crea).

### Referencia de comandos

`project create|info` · `level add|list` · `zone add|list` · `space add|list` · `wall add|list|move` · `door add|list` · `window add|list` · `undo` · `redo` · `relationships recompute|report` · `validate` · `qto compute|show` · `resource add|list` · `price set|history` · `budget compute|show` · `export --format dxf|json|xlsx|csv|ifc` · `import [--approve]` · `importar catalogo|dxf` · `version save|list|restore|compare|export|branch` · `backup create|list|restore|autosave|incremental|journal|checkpoint|verify|recover` · `audit show|stats|export` · `events show` · `net add|list|show|trace|path|validate|deadends` · `node add|list|move` · `link add|list|remove` · `elec check|summary|balance` · `san size` · `hvac load|loads|duct|size-network` · `plu size` · `gas size|check` · `tel size` · `struct material-add|section-add|element-add|element-list|element-delete|case-add|combo-add|defaults|analyze|truss|connection-check|report` · `sec net|device-add|coverage|network|cabling|fire-check|cause-effect|intrusion-check|access-check|perimeter-check|bom` · `clash run|list|status` · `precons list|analyze|project|compare|import` · `bim tree|show` · `docs variables|memoria|tecnica|specs|cuadros|listados|informe|module|drawing-add|drawing-list|drawing-delete|template-add|template-render` · `optimize current|pareto|compare` · `plugins validate|info|new` · `benchmark run|caches` · `gui [archivo] [--demo]` · `demo` · `selftest`

Cualquier comando con errores controlados muestra `ERROR [código] mensaje` + sugerencia y devuelve código 1 (útil para automatizar). Los errores inesperados quedan con detalle completo en `logs\app\errors.log`.

---

## 5. Dónde están los registros (logs)

| Ruta | Contenido |
|---|---|
| `logs\bat_boot.log` | **Latido de arranque**: una línea `INICIO`/`FIN` por cada ejecución de cualquier .bat. Si este archivo no aparece, el script ni siquiera llegó a arrancar (archivos viejos o bloqueo de SmartScreen) |
| `logs\setup\env_*.log` | Verificación del entorno (errores de detección de Python) |
| `logs\setup\install_*.log` | Instalación de dependencias (errores de pip) |
| `logs\tests\pre_build_*.log` | Pruebas **antes** de compilar |
| `logs\build\build_*.log` | Compilación PyInstaller (errores **durante**) |
| `logs\tests\post_build_*.log` | Selftest del ejecutable **después** de compilar |
| `logs\tests\run_*.log` | Ejecuciones de la suite con `02_PRUEBAS.bat` |
| `logs\app\arqgen.log` | Log rotativo de ejecución (DEBUG) |
| `logs\app\errors.log` | Solo errores (ERROR/CRITICAL) de ejecución |

---

## 6. Estructura del código

```
ARQ_GEN/
├── main.py                  Punto de entrada
├── app/                     bootstrap, ciclo de vida, logging, CLI, demo, selftest, undo persistente
├── core/                    entidades, ids, unidades, geometría, eventos, comandos, reglas,
│                            validación, grafos, cálculos, auditoría, versionado, permisos
├── domain/                  modelo semántico único + instalaciones + estructura + clash + Space DNA (conocimiento)
├── services/                ProjectService, ArchitectureService, InstallationsService, Security, Coordination,
│                            Structure, Precons, BIM, Analysis (reglas/validación/espacial), Quantity (QTO),
│                            Pricing, Budget, Version, Import, Export, contexto y contenedor DI
├── engines/                 quantity (QTO), pricing, budget, spatial, network (§25), routing (§26),
│                            electrical (§27), sanitary (§28), hvac (§29), stormwater (§30), gas (§31),
│                            telecom (§32), structure (§34), fov (§39), cctv (§41-42), fire (§43-44),
│                            intrusion (§45), access (§46), perimeter (§47), clash (§36), precons (§59-60)
├── persistence/             sqlite (conexión), migraciones reversibles (7), repositorios, backup
├── importers/               Pipeline §94: tablas (xlsx/csv), catálogo PRECONS (autodetección + mapa), DXF→muros/locales
├── exporters/               JSON (ida/vuelta) · DXF · XLSX · CSV · IFC4 SPF
├── ui/                      Interfaz gráfica Tkinter (FASE 90): ventana, explorador, lienzo, buscador, estados + theme (tema oscuro) y help (ayuda dinámica, guía)
├── plugins/                 API de plugins + 15 integrados (§88 completo: architecture, installations, gas, structure, cctv, fire, intrusion, access, perimeter, qto, budget, bim, documentation, coordination, precons) + externos en plugins\external
├── resources/               rulesets (reglas, causa/efecto fuego, PRECONS), space DNA, plantillas de presupuesto (datos, no código)
├── tests/                   439 pruebas unittest (pirámide del spec + todas las disciplinas con valores verificados a mano)
└── 00..07 *.bat             pipeline de instalación/pruebas/compilación/ejecución con logs
```

**Principios respetados del spec maestro:** una sola pared (`WALL-001`) consultada por todos los módulos (§111); cambio → detección de dependencias → recálculo incremental → validación → auditoría (§112); trazabilidad de todo número (§105); normas como datos versionados, nunca incrustadas en código (§12); patrón DETECTAR→EXPLICAR→PROPONER→APROBAR→APLICAR→REVALIDAR (§10); un solo UNDO revierte la operación completa (§77).

---

## 7. Datos configurables (sin tocar código)

- `resources\knowledge\space_dna.json` — ADN de tipos de local (áreas mínimas, zonas húmedas, adyacencias preferidas…)
- `resources\rulesets\*.json` — reglas por jurisdicción con severidad INFO/WARNING/ERROR/HARD_BLOCK y parámetros
- `resources\budget_templates\*.json` — estructura del presupuesto: capítulos, partidas, origen de cantidades y rendimientos de recursos

Añada los suyos copiando el formato; el motor no cambia.

---

## 8. Pruebas

```bat
02_PRUEBAS.bat
```

439 pruebas cubren: proyectos, geometría y reparación, unidades y conversiones seguras, evaluador de fórmulas (incluye rechazo de código peligroso), eventos, undo/redo (en proceso y persistente entre sesiones), migraciones reversibles (8), repositorios, auditoría, relaciones espaciales y DNA, reglas y validación, QTO con números exactos, precios históricos, presupuesto determinista, DXF legible, XLSX/CSV, round-trip JSON, backup/corruptos/recuperación, versionado, permisos, plugins internos y externos, batería completa de la CLI, instalaciones (redes, eléctrico, sanitario, HVAC, pluviales, gas, telecom), **estructura** (secciones, vigas, pilares, cerchas analíticas, uniones, QTO), **seguridad** (FOV, CCTV, fuego con causa/efecto, intrusión, acceso, perímetro, BOM), **coordinación y clash** (seis tipos de interferencia, deduplicación, ciclo de vida), **PRECONS** (takeoff, análisis con coeficientes, variantes, importador con mapa de columnas), **importadores spec 94** (tablas XLSX/CSV con cabeceras y delimitadores, catálogo plano y multi-hoja con autodetección y mapa explícito, precios reportados, DXF→muros/locales con auditoría, CLI preview/aplicar), **BIM/IFC** (proyección de 8 dimensiones, árbol espacial, SPF válido sin referencias colgantes), **documentación** (escalas, elementos de plano, plantillas con variables, memorias deterministas, cuadros, informes, TEST-021), **optimización multiobjetivo** (dominancia de Pareto con valores verificados a mano, 12 objetivos del spec 19), **auditoría filtrada/estadísticas/exportación**, **versiones** (compare/export/branch con backup automático), **backup** (autosave rodante, incremental por hash, journal, verificación, recuperación TEST-024), **plugins** (validación estática, andamiaje, info, registro §88 completo con GAS como plugin de instalaciones §31) y **benchmark** (8 operaciones, inventario de cachés), **regresión con valores dorados** (dos demos independientes idénticas), **GUI FASE 90** (13 disciplinas §91, buscador §92 por 9 campos, estados §93 con transiciones y auditoría, lienzo con primitivas y viewport, ventana Tk real con display o Xvfb — 7 pruebas de ventana omitidas con elegancia sin display) y **GUI editable FASE 90.1** (PropertyEditor con lista blanca y auditoría UPDATE_ENTITY, creación declarativa por fachadas, borrado con cascadas, undo persistente, zoom anclado al cursor, atajos de teclado), **UX v1.7.1** (tema oscuro con estilos ttk aplicados, paleta del lienzo completa, tooltips obligatorios en la barra de herramientas y paneles, ayudas por campo que cubren todos los formularios de creación, mensajes orientadores de los 5 menús, guía rápida de 4 pasos, motor de siguiente paso, tarjeta de bienvenida en proyectos vacíos, ecos de ayuda en la barra de estado), todo con valores verificados a mano.

---

## 9. Cálculos de instalaciones: método y datos

Los motores de instalaciones son deterministas y todos sus parámetros normativos
viven como datos editables en la cabecera de cada módulo (`engines/*.py`),
documentados con la norma de referencia:

| Motor | Métodos | Valores por defecto (configurables) |
|---|---|---|
| Eléctrico (§27) | I = P/(V·pf) 1φ, P/(√3·V·pf) 3φ; ΔV = 2ρLI/S y √3ρLI/S; protección normalizada IEC; sección con coordinación Ib ≤ In ≤ Iz; conducto al 40%; balance (max−min)/media | ρ Cu 0,0175 Ω·mm²/m; ampacidades IEC 60364-5-52 método C (1,5 mm²→19,5 A … 240 mm²→461 A); caída máx. ramal 3%; factores de demanda por tipo de circuito |
| Sanitario (§28) | simultaneidad k = min(1, 1,8/√n); Hazen-Williams J = 10,67·Q^1,852/(C^1,852·D^4,87); Manning en gravedad con lámina 50%; TDH = estática + rozamiento + residual; P = ρgQH/η | caudales por aparato (WC 0,10 L/s, ducha 0,15…); C PVC 140, acero 100; n PVC 0,011; pendientes mín. tipo IPC (DN50→2,08%…); residual 5 m.c.a.; η bomba 0,70 |
| HVAC (§29) | carga = transmisión + solar + interna + ventilación (y calefacción sin aportes); aire Q = Qs/(ρ·cp·ΔT); ducto A = Q/v con catálogo comercial; selección con margen 10% | ΔT refrigeración 9 K, calefacción 10 K; U muro 2,0 / vidrio 5,8 / cubierta 1,5 W/m²K; solar 180 W/m²; ocupación 10 m²/persona (75 W + 55 W); iluminación 10 + equipos 5 W/m²; infiltración 0,5 ACH; ΔT impulsión 10 K; velocidades MAIN 6 / BRANCH 4 / RETURN 3 m/s |
| Redes (§25-26) | grafo dirigido en dirección de flujo; BFS (saltos) y Dijkstra (longitud/coste); validación árbol radial o convergencia a sumidero; router ortogonal con penalizaciones | cruce de muro 15; obstáculo infranqueable 100; violación de holgura 40; holgura 5 cm; corredor preferente −0,5/m |

Cada cálculo queda registrado en la tabla `calculations` con su hash de entrada
(§102): mismo input → mismo resultado verificable. El selftest comprueba 7180 W
conectados en el panel demo como diana determinista.

## 10. Qué incluye la demo (v1.6.2)

La demo determinista incluye **12 redes** de 6 disciplinas sobre la misma
geometría, coordinadas sin interferencias HARD:

- **Fuerza e Iluminación** (POWER): tablero + 3 circuitos → 7.180 W conectados.
- **Agua Fría Sanitaria** (COLD_WATER): contador + 5 aparatos con
  dimensionado Hazen-Williams.
- **Desagüe Sanitario** (SANITARY_DRAINAGE): 2 aparatos → bajada →
  alcantarillado; colector acumula 0,25 L/s en DN50 al 2,08%.
- **Extracción Baño** (EXHAUST): rejilla 60 m³/h → extractor, DN100 a 2,12 m/s.
- **Pluvial Cubierta** (STORMWATER): 2 sumideros (80 m², C=0,90, i=100 mm/h)
  → canalón → tanque de detención 1.800 L → evacuación 2,2 L/s.
- **Gas Doméstico** (GAS): regulación + 2 válvulas + 2 aparatos (15,5 kW),
  validación completa del spec 31.
- **Telecomunicaciones** (TELECOM): rack 12U, patch panel, switch, 4 rosetas
  y uplink de fibra con presupuesto óptico.
- **Estructura**: 2 pilares de hormigón H-25 con análisis ULS-1, viga de
  acero IPE-300 con flexión y flecha, y **cercha analizada por método de
  nudos** (≈1.875 kg de acero en total).
- **CCTV**: 2 cámaras con FOV por ray casting, switch PoE y NVR; cobertura,
  red (ancho de banda/almacenamiento 30 días) y cableado calculados.
- **Detección de Incendios**: central + 4 detectores por local + pulsador +
  sirena; matriz causa/efecto ejecutada.
- **Intrusión**: central + teclado + 4 PIR en 2 zonas + 2 contactos + sirena.
- **Control de Acceso**: controlador + lector + cerradura fail-safe (0,5 s).
- **Perímetro**: valla de 40 m + 3 sensores + portón + cámara + lector.

La **coordinación** corre detección completa sobre el proyecto (sin choques
HARD); **PRECONS** analiza el proyecto con el ruleset `precons_cuba_v1`
(cimientos, mampostería, enlucido, acero) alimentado por QTO; y la demo se
exporta a **DXF/XLSX/CSV/JSON/IFC**.

Presupuesto con la plantilla `residential_full_v1` (8 capítulos: obra civil,
carpintería, eléctrica, sanitaria, climatización, instalaciones
complementarias, estructura y seguridad): **1.295.093,90 CUP** (valor dorado
verificado por la suite de regresión).
