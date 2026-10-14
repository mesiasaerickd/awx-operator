# Registro de ingeniería y seguridad — AWX Operator

Fecha de apertura: 2026-10-13
Estado: diagnóstico inicial; **sin cambios de código de aplicación ni imágenes construidas**.

## Política de ramas
- `devel`: referencia heredada del proyecto upstream, no modificar.
- `dev`: análisis y cambios sujetos a pruebas.
- `prd`: solo código validado, por ahora idéntico al punto inicial de `devel`.

## Hallazgos iniciales
Se verificó `Dockerfile`: parte de `quay.io/operator-framework/ansible-operator:v1.42.3`, ejecuta `microdnf update` e incorpora colecciones de `requirements.yml`. Falta comprobar compatibilidad con el CRD y el despliegue AWX existente.

## Decisiones
1. Comparar el código `devel` con la imagen desplegada AWX 24.6.1 antes de cambiar imagen base.
2. No cambiar imágenes de Kubernetes productivo ni tocar el servidor actual.
3. Mantener cambios en PR desde `dev` hacia `prd`, con revisión, SBOM, análisis Trivy, pruebas de construcción y pruebas funcionales.
4. Construir imágenes en CI/runner aislado y publicarlas en un registro OCI, identificadas por SHA256 y versión propia. Ninguna imagen queda aprobada sin pruebas.
5. Evaluar CentOS Stream 9 y UBI 9 por separado: sustituir el sistema base no corrige por sí mismo dependencias Python.

## Historial
- 2026-10-13: creadas ramas `dev` y `prd` desde `devel`; inspección inicial de fuentes y apertura del registro de ingeniería.

## Pendiente
- Verificar árbol de dependencias resueltas, compilar, obtener SBOM y ejecutar Trivy.
- Establecer runners y condiciones de publicación de imágenes.
- Verificar tests, compatibilidad AWX/Operator/EE y recuperación de PostgreSQL.
- Decidir controles y riesgos aceptables antes de solicitar despliegue en producción.

- 2026-10-13: se agregó el workflow de GitHub Actions para compilación de imagen en `dev`, sin despliegue ni publicación al registro. Estado: ejecución y validación pendientes; fallo de build no autoriza cambios automáticos a `prd`.

- 2026-10-13: se extendió GitHub Actions para escanear la imagen compilada con Trivy 0.75.0 (CRITICAL y HIGH), generar un JSON y subirlo como artifact durante 30 días. Los hallazgos no bloquean todavía el build: se requiere establecer baseline, validar límites de cobertura y definir umbrales antes de habilitar gates. Sin push de imágenes ni modificaciones en `prd`.

## Verificación de CI y seguridad — 2026-10-13
Run 38493370913: los cuatro jobs CI oficiales (`no-log`, Molecule dos variantes, Nox build) finalizaron correctamente. Ese run NO contiene el paso de escaneo Trivy del workflow propio de build. Resultado de seguridad de la imagen Operator aún no confirmado.

Decisión: mantener `prd` sin cambios; no publicar a GHCR hasta identificar CVE remanentes, comprobar cobertura OS y validar la integración Kubernetes. La ejecución de Trivy exitosa significa que el escáner pudo correr, no que no existan vulnerabilidades.

## Fase de seguridad de AWX Operator — 2026-10-13
- El CI propio `operator-build.yml` valida ahora la existencia del ejecutable del Operator y `watches.yaml` en la imagen, recoge el ID local inmutable, exige que exista un JSON válido de Trivy con `SchemaVersion` y `Results`, y adjunta la evidencia durante 30 días.
- El análisis de vulnerabilidades usa Trivy 0.75.0 con HIGH y CRITICAL. No bloqueamos por número de CVE antes de establecer una línea base; sí por ausencia de reporte.
- La ejecución de CI oficial del Operator no equivale al escaneo de nuestra imagen; el resultado de Trivy sigue pendiente de la nueva ejecución de `AWX Operator development image build` en la rama `dev`.
- Esta fase no publica imágenes ni modifica `prd`, AWX instalado o Kubernetes. Los riesgos de compatibilidad de CRD y de sistema operativo se evaluarán por separado.

## Línea base Trivy Operator — runs de 2026-10-13
- CI oficial #38509376653: 4 jobs SUCCESS (no-log, Molecule x2 y Nox build).
- CI oficial #38509359325: 4 jobs SUCCESS (no-log, Molecule x2 y Nox build).
- Build propio con Trivy #38509359343: SUCCESS, **0 CRITICAL y 41 HIGH**. Artifact `awx-operator-trivy-report` ID 11868838160, JSON descargado y analizado.
- **Distribución de 41 HIGH:** 9 de paquetes del sistema Red Hat 9.8 (expat 2, gnutls 2, libblkid/libmount/libsmartcols/libuuid y python3.12-pip-wheel); 9 de dependencias Python (pyasn1 3, urllib3 2, virtualenv 3, cryptography 1); **23 del binario Go** `/usr/local/bin/ansible-operator` (Go stdlib, x/net, x/text y gRPC).
- Dependencias Python detectadas: pyasn1 0.6.3 (fix 0.6.4), urllib3 2.7.0 (fix 2.8.0), virtualenv 21.5.1 (fix mínimo entre 21.7.12 y 21.7.13), cryptography 49.0.0 (fix 50.0.0).
- En el sistema base expat 2.5.0, gnutls 3.8.10, util-linux 2.37.4 y python3.12-pip-wheel 23.2.1 aparecen HIGH sin FixedVersion informado; requieren comprobar erratas del proveedor, no inventar versiones corregidas.
- El binario `ansible-operator` proviene de la base `quay.io/operator-framework/ansible-operator:v1.42.3`. Sus hallazgos Go **no se arreglan** simplemente actualizando paquetes Python o `microdnf`; evaluar imagen base reconstruida con toolchain/módulos Go corregidos o una versión mantenida compatible. No sustituir la base a ciegas: verificar CRD, permisos y reconciliación.
- Próximo trabajo: inventario de versiones instaladas, opciones seguras de actualización de base y prueba de regresión Operator; reescanear y comparar CVE por ID. Los tests actuales no sustituyen integración real en Kubernetes.
- Sin publicación GHCR, sin promoción a `prd`, sin cambios en Kubernetes.

## CI funcional 38511867990 — 2026-10-14
- Los cuatro jobs del workflow oficial fueron SUCCESS: Molecule sin replicas, Molecule replicas, Nox build y validacion no_log.
- Esta ejecucion no incluyo el workflow de imagen `operator-build.yml` ni produjo artefacto de Trivy. No permite afirmar una reduccion de CVE.
- Ultima linea base de seguridad comprobada: run 38509359343, Trivy CRITICAL=0, HIGH=41 (9 OS, 9 Python, 23 Go binario).
- Proximo trabajo: corregir la imagen en `dev` y ejecutar el workflow de build + Trivy antes de actualizar el conteo de vulnerabilidades. Sin cambios a prd ni Kubernetes.

## Diagnóstico de remediación Python — 2026-10-14
- Se añadió un paso al workflow `operator-build.yml` que inspecciona el intérprete Python, las rutas de instalación, disponibilidad de pip y versiones efectivas de pyasn1, urllib3, virtualenv y cryptography dentro de la imagen generada.
- Objetivo: determinar si los paquetes vulnerables pertenecen al runtime/base o a una instalación gestionada, antes de modificar versiones que podrían romper el Operator; el paso falla si no se pueden localizar mediante `importlib.metadata` y expone el bloqueo real.
- No se han modificado dependencias ni imagen base aún. Línea base Trivy sigue en 0 CRITICAL / 41 HIGH. Tras conocer las rutas, aplicar cambios mínimos y volver a pasar Trivy y Molecule.
- No hay cambios en `prd` ni despliegues Kubernetes.

## CI Molecule 38514441350 / 38514549974 / 38514565259 — 2026-10-14
- #38514441350: fallo temporal al instalar colecciones desde Ansible Galaxy (`Connection reset by peer`); otros dos jobs SUCCESS y test de replicas cancelado.
- #38514549974 y #38514565259: Molecule se detuvo por yamllint `line-length` en `.github/workflows/operator-build.yml:40` (199 caracteres, limite 170), introducido por nuestro inventario Python. Nox y no_log SUCCESS; un job Molecule fallido y el otro cancelado en cada ejecucion.
- Corregido en `dev` dividiendo el inventario de rutas Python en comandos cortos. Verificacion estatica del workflow: ninguna linea excede 170 caracteres (maximo actual: 162). Requiere nuevo CI para confirmar.
- Ninguna de estas ejecuciones corresponde al escaneo Trivy; ultima linea base del Operator: 0 CRITICAL / 41 HIGH. El inventario de Python todavia no tiene resultado de ejecucion confirmado.
- Sin cambios en `prd`, GHCR ni Kubernetes.

## CI siete ejecuciones e inicio de remediación Python — 2026-10-14
- #38514951973 y #38514962858: CI Molecule falló por longitud de línea (177 y 180 caracteres respectivamente) en el workflow de inventario durante versiones intermedias; `no-log` y Nox pasaron. Corregido posteriormente en `dev`.
- #38514994480 y #38514978509: CI oficial APPROVED (Molecule ambos escenarios, Nox y no_log).
- #38514952052, #38514962861 y #38514978705: Docker build, inventario Python y Trivy SUCCESS; resultado consistente: **0 CRITICAL / 41 HIGH**.
- Inventario confirmado en imagen: pyasn1 0.6.3, urllib3 2.7.0, virtualenv 21.5.1 en `/usr/local/lib/python3.12/site-packages`; cryptography 49.0.0 en `/usr/local/lib64/python3.12/site-packages`.
- CANDIDATO sin validar aplicado a Dockerfile **solo dev**: pyasn1 0.6.4, urllib3 2.8.0, virtualenv 21.7.13 y cryptography 50.0.0 usando `python3 -m pip install` seguido por `pip check`.
- Añadido gate CI para versiones exactas, `pip check` e importación de librerías. Si falla compatibilidad, resolver cuidadosamente; no forzar con `--no-deps`. No se presume reducción de hallazgos hasta reescaneo.
- Pendientes: validar build+Trivy con nuevo Dockerfile, ejecutar CI funcional, atender 23 HIGH de Go y 9 HIGH OS, probar reconciliación en Kubernetes aislado. Sin cambios a prd ni despliegues.

## RCA cinco ejecuciones y corrección de bootstrap pip — 2026-10-14
- Runs #38517382621 y #38517402256: Docker build FAILED en instalación de cuatro parches Python, ERROR inequívoco `/usr/local/bin/python3: No module named pip`. No llegó a resolver ni instalar librerías, tampoco ejecutó Trivy.
- Runs #38517382693, #38517402324 y #38517428566: jobs Molecule fallaron al construir `testing-operator` por el mismo paso Docker, no por regresión demostrada de lógica Kubernetes; jobs Nox y no_log pasaron.
- Fallo de diseño anterior: se asumió que la base operator-framework ansible-operator v1.42.3 tenía pip instalado, pese a que nuestro inventario ya mostraba lo contrario. Se corrige sin `curl | sh` ni desactivar dependencias.
- Nuevo candidato en `dev`: copiar exclusivamente el módulo pip (puro Python) desde `python:3.12-slim` a una ruta temporal en build; ejecutarlo con el intérprete Python 3.12 del Operator mediante `PYTHONPATH`, instalar pyasn1 0.6.4, urllib3 2.8.0, virtualenv 21.7.13 y cryptography 50.0.0; ejecutar pip check y retirar pip temporal. La imagen final permanece sin pip como en upstream. CI confirma versión/imports y Trivy, sin invocar pip en runtime.
- Nota de cadena de suministro: la referencia `python:3.12-slim` deberá fijarse por digest y comprobarse antes de promover imagen. Riesgo de compatibilidad entre bibliotecas pendiente. No se afirma éxito hasta un nuevo build.
- Baseline último verificado: Operator 0 CRITICAL/41 HIGH. No se tocaron prd, GHCR ni Kubernetes.

## RCA cinco runs 385180* — conflicto pip-api tras instalación Python — 2026-10-14
- Build FAILED: #38518045823 y #38518063551. Molecule FAILED/cancelado: #38518046433, #38518063606, #38518091786; `no-log` y Nox SUCCESS en ejecuciones oficiales.
- Logs de build: el bootstrap temporal de pip SI instaló correctamente pyasn1 0.6.4, urllib3 2.8.0, virtualenv 21.7.13 y cryptography 50.0.0; el fallo posterior de `pip check` es `pip-api 0.0.34 requires pip, which is not installed`. No fue fallo de descarga ni de resolución de las cuatro versiones.
- Corrección en rama `dev`: instalar también `pip==25.3` como distribución real; mantener `python3 -m pip check` en el Dockerfile y comprobar en imagen final `pip==25.3`, dependencias e imports mediante CI. Eliminar únicamente el módulo temporal usado para bootstrap. La imagen final YA NO está libre de pip: decisión explícita para cumplir con pip-api instalado.
- Candidato sin verificar: nueva compilación y pruebas Molecule, Trivy y verificación de compatibilidad funcional requeridas. No inventar reducción de los 41 HIGH antes de un informe posterior.
- Seguridad pendiente: revisar exposición/actualizaciones de pip y fijar por digest la imagen de bootstrap python:3.12-slim; cambios solo dev, prd/Kubernetes/GHCR intactos.

## Remediación Python validada — CI 385190* (2026-10-14)
- Build + Trivy #38519023344 y #38519038144: SUCCESS. `pip check` informa `No broken requirements found`, imports Python correctos. Trivy CRITICAL=0, HIGH=32 en ambas ejecuciones, bajando 9 HIGH frente a baseline 41.
- Builds incluyen pyasn1==0.6.4, urllib3==2.8.0, virtualenv==21.7.13, cryptography==50.0.0 y pip==25.3 para satisfacer `pip-api`. Cambio de paquetes Python compatible con estos controles, no aún validado en clúster real.
- CI #38519023337 y #38519062126: SUCCESS los cuatro jobs (Molecule ambos escenarios, Nox build y no_log).
- CI #38519038143: falla Molecule debido a consulta `https://api.github.com/repos/ansible/awx/releases/latest` con HTTP 403 rate limit exceeded, no por fallo demostrado del runtime. CI #38519062126 vuelve a aprobar.
- Reportes Trivy en los runs: artefactos 11873740347 y 11873260950. Quedan 32 HIGH; siguiente fase: aislar 23 del binario Go y 9 del OS en JSON actual y evaluar estrategia de reconstrucción/base, con compatibilidad probada antes de cambiar.
- No se promovió a `prd`, no se publicó GHCR y Kubernetes sigue sin modificaciones.

## Fase 3: análisis de Go/RPM y procedencia — 2026-10-14
- Evidencia directa del JSON del run #38519023344, artefacto 11873740347: **0 CRITICAL / 32 HIGH**; 23 HIGH del ejecutable `/usr/local/bin/ansible-operator` (Go stdlib 1.26.3, golang.org/x/net 0.54.0, x/text 0.38.0, google.golang.org/grpc 1.79.3) y 9 HIGH RPM (expat 2, gnutls 2, util-linux libraries 4, python3.12-pip-wheel 1). Dependencias Python corregidas ya no aparecen con HIGH.
- Go necesita reconstrucción del ejecutable o base actualizada compatible; instalar Go o subir bibliotecas Python **no corrige** binarios precompilados. Trivy indica para las CVE de stdlib más recientes Go 1.26.9 / 1.27.2, para x/net hasta 0.60.0, x/text 0.39.0 y gRPC varias correcciones hasta 1.83.x+, sujetas a su resolución real en un rebuild.
- RPM expat, gnutls, libblkid/libmount/libsmartcols/libuuid y python3.12-pip-wheel figuran con alta severidad y sin FixedVersion en el JSON; no asumir que `microdnf update` los puede corregir sin erratas nuevas del proveedor.
- Añadido workflow en `dev` para extraer `go version -m` del ejecutable y `rpm -q` de paquetes afectados, archivando ambos en `awx-operator-trivy-report`; esto permite evaluar actualización del binario y cobertura del OS con evidencia de builds reproducibles. Candidato de workflow sin nueva validación todavía.
- Siguiente paso: revisar salida de procedencia, comparar versión de ansible-operator/imagen base mantenida o planificar reconstrucción de binario con Go y módulos corregidos, asegurando pruebas Molecule, reconciliación y permisos Kubernetes. Solo dev; prd/GHCR/Kubernetes sin cambios.

## CI funcional 38521565282, 38521754183, 38521796263 — 2026-10-14
- Cada ejecución completó con éxito los cuatro jobs oficiales: Molecule ambos escenarios, Nox build y no_log (12 jobs exitosos en total).
- Son pruebas funcionales; ninguna generó artefacto de seguridad ni corresponde al workflow `operator-build.yml`. No se ha verificado todavía el nuevo paso de procedencia Go/RPM del commit a30ecdd6.
- Línea base de seguridad confirmada: Trivy Operator 0 CRITICAL, 32 HIGH (#38519023344 / #38519038144). Falta ejecutar/verificar el workflow de imagen en `dev` para obtener `go-build-info.txt` y `rpm-versions.txt`.
- `prd`, GHCR y Kubernetes siguen intactos.

## CI funcional #38524804074 — 2026-10-14
- Molecule sin réplicas, Molecule con réplicas, Nox build y no_log: todos SUCCESS.
- Esta ejecución NO es el workflow `operator-build.yml` ni contiene artifacts de Go/RPM o Trivy; no demuestra remediación de CVE.
- Baseline confirmado Operator: 0 CRITICAL / 32 HIGH; pendiente ejecutar `AWX Operator development image build` en `dev` para obtener go-build-info.txt y rpm-versions.txt.
- Sin cambios a prd, GHCR ni Kubernetes.

## Evidencia completa build #14 / run 38521754159 — 2026-10-14
- Workflow `AWX Operator development image build` SUCCESS en dev: build Docker, inventario de bibliotecas Python, `pip check`, `go version -m`, inventario RPM, Trivy y publicación del artefacto de diagnóstico. Artefacto ID 11874003352, informe `trivy-reports/awx-operator-trivy.json`, procedencia `security-evidence/go-build-info.txt`, RPM `security-evidence/rpm-versions.txt`.
- Informe Trivy JSON leído del artefacto: **0 CRITICAL, 32 HIGH**; 23 Go binario y 9 paquetes RPM, sin HIGH Python.
- Binario `/usr/local/bin/ansible-operator`: Go **1.26.3**, `golang.org/x/net` **0.54.0**, `golang.org/x/text` **0.38.0**, `google.golang.org/grpc` **1.79.3**.
- Distribución de hallazgos Go: stdlib 14 HIGH, x/net 5 HIGH, x/text 1 HIGH, grpc 3 HIGH. Trivy indica versiones corregidas máximas pertinentes: Go >=1.26.9 en la línea 1.26 o >=1.27.2; x/net >=0.60.0; x/text >=0.39.0; grpc >=1.83.2 (entre versiones estables indicadas para los tres hallazgos). Esas versiones son objetivos de evaluación, no garantía de compatibilidad ni de resolución exhaustiva de transitorios.
- RPM: expat 2 HIGH, gnutls 2 HIGH, util-linux libraries (libblkid, libmount, libsmartcols, libuuid) 4 HIGH, python3.12-pip-wheel 1 HIGH. Versiones efectivas: expat `2.5.0-6.el9_8.5`, gnutls `3.8.10-9.el9_8`, cuatro util-linux `2.37.4-25.el9`, pip-wheel `23.2.1-5.el9`. JSON no informa FixedVersion para ninguno; evaluar RHSA y actualizar imagen base cuando haya corrección del proveedor, sin sustituir RPM por contenido no certificado.
- Decisión técnica: NO subir directamente módulos Go en Dockerfile; están embebidos en ejecutable estático. Investigar fuente exacta del binario `ansible-operator` upstream v1.42.3 y rebuild reproducible con toolchain/módulos compatibles, pruebas Molecule y comparación API/CRD antes de adoptar. Mantener cambios confinados a dev, no promover a prd/GHCR/Kubernetes.

## CI #38531424707: Molecule sin dependencia de GitHub releases/latest (2026-10-14)
- CI oficial: no_log SUCCESS, Nox build SUCCESS, Molecule replicas FAILED, Molecule sin replicas CANCELLED.
- Causa confirmada en logs: `lookup('url', 'https://api.github.com/repos/ansible/awx/releases/latest')` devuelve HTTP 403 `rate limit exceeded`. No evidencia un defecto del operador ni altera baseline Trivy.
- Se localizó el lookup en `molecule/kind/molecule.yml` y `molecule/default/molecule.yml`, bajo `default_awx_version`.
- Se eliminó la consulta externa de ambos escenarios. Ahora `default_awx_version: ${AWX_DEFAULT_VERSION:-24.6.1}`, con valor determinista alineado al argumento de build Docker en nuestro CI y configurable por ambiente para probar otra versión. `awx_version` y las pruebas siguen intactas.
- Cambio solo en dev, **pendiente de validar** con nuevos runs Molecule. Última referencia de seguridad: 0 CRITICAL / 32 HIGH. Sin cambios en prd, GHCR ni Kubernetes.

## Validación Molecule posterior al cambio de versión determinista — 2026-10-14
- CI #38532006562, #38532012712, #38532047205: cada una con 4/4 jobs SUCCESS (Molecule replicas, Molecule sin replicas, Nox y no_log).
- Cambio de eliminación del lookup remoto a GitHub validado a nivel de CI de ambos escenarios. Estas ejecuciones no incluyen Trivy.
- Baseline de seguridad del Operator sin cambios demostrados: 0 CRITICAL / 32 HIGH (23 Go y 9 RPM). Falta reconstrucción y verificación del binario, evaluación de avisos RPM y validación de despliegue/rollback en clúster de pruebas antes de promover.
- Solo rama dev; prd, GHCR y Kubernetes sin modificaciones.

## CI funcional #38535609849 — 2026-10-14
- Molecule replicas SUCCESS, Molecule sin replicas SUCCESS, Nox build SUCCESS y no_log SUCCESS (4/4).
- Ejecucion sin Trivy ni artefactos Go/RPM: no constituye evidencia de reduccion de las 32 HIGH pendientes.
- Sigue pendiente reconstruccion/actualizacion segura del binario Go (23 HIGH), revision de RPM (9 HIGH) y validacion de despliegue. Solo dev; no se tocan prd, GHCR ni Kubernetes.

## CI funcional #38539140506 — 2026-10-14
- Los cuatro jobs finalizaron SUCCESS: Molecule con y sin réplicas, Nox build y no_log.
- La ejecución no incluye workflow de imagen ni reporte Trivy; no demuestra reducción de las 32 HIGH pendientes (23 binario Go, 9 RPM).
- Continúa pendiente reconstruir/actualizar binario Go y evaluar erratas RPM, además de validación integral en clúster aislado. Sin cambios a prd, GHCR ni Kubernetes.

## CI funcional #38592302883 — 2026-10-14
- Aprobados los cuatro jobs: Molecule sin réplicas, Molecule con réplicas, Nox build y no_log.
- Esta ejecución no incluye build de seguridad, artefactos Go/RPM ni Trivy; el último conteo validado continúa en 0 CRITICAL y 32 HIGH (23 Go, 9 RPM).
- La reconstrucción del binario Go continúa pendiente; no se promovió a prd ni se desplegó Kubernetes.

## CI funcional #38596579359 — 2026-10-14
- Molecule con réplicas, Molecule sin réplicas, Nox build y no_log: SUCCESS (4/4).
- Sin artefactos Trivy en esta ejecución. Última referencia confirmada: 0 CRITICAL, 32 HIGH (23 Go, 9 RPM).
- Pendientes reconstrucción segura del binario Go, evaluación de erratas RPM y pruebas de integración antes de una promoción. Solo dev; prd, GHCR y Kubernetes sin modificaciones.

## CI funcional #38600960085 — 2026-10-14
- Los cuatro jobs finalizaron SUCCESS: Molecule con réplicas, Molecule sin réplicas, Nox build y no_log.
- No contiene artefacto Trivy ni verifica reducción de vulnerabilidades. Última referencia de seguridad: 0 CRITICAL / 32 HIGH (23 Go, 9 RPM).
- Pendiente reconstrucción/actualización del binario Go y evaluación de RPM. Cambios solo en dev; prd, GHCR y Kubernetes sin modificaciones.

## CI funcional #38605449135 — 2026-10-14
- Exitosos los cuatro jobs: Molecule replicas, Molecule sin replicas, Nox build y no_log.
- No hubo artefactos Trivy. Se mantiene la ultima referencia de 0 CRITICAL y 32 HIGH (23 Go, 9 RPM).
- Sigue pendiente remediacion del binario Go, comprobacion de erratas RPM y nueva validacion de seguridad. Solo rama dev.

## CI funcional #38608936168 — 2026-10-14
- Molecule replicas, Molecule sin replicas, no_log y Nox build: SUCCESS (4/4).
- Sin reporte Trivy ni artefactos de seguridad. Ultima linea base observada: 0 CRITICAL y 32 HIGH (23 Go, 9 RPM).
- Pendiente remediacion del binario Go, verificacion de parches RPM y validacion integral. Solo dev; sin cambios a prd, GHCR ni Kubernetes.

## CI unificado para dev — 2026-10-14
- Diagnostico del run funcional #38613422046: Molecule con y sin replicas, Nox build y no_log: SUCCESS (4/4). No publico reportes Trivy ni evidencia de remediacion.
- `.github/workflows/operator-build.yml` pasa a `AWX Operator unified dev validation` y ejecuta en cada `push` a `dev` (sin filtro de rutas): build de imagen local sin publicar, checks de binario y Python, provenance Go, versiones RPM, Trivy JSON y upload de evidencia, ademas de Molecule (dos escenarios), no_log y Nox.
- `.github/workflows/ci.yaml` mantiene comprobaciones de PR y pushes fuera de dev, pero excluye dev en pushes para evitar ejecuciones duplicadas.
- Objetivo: un solo workflow visible para cada commit en dev. Trivy es observacional y NO bloquea por HIGH; por tanto un workflow verde no equivale a remediacion de seguridad. Estado ultimo confirmado: 0 CRITICAL y 32 HIGH (23 Go, 9 RPM).
- Cambios exclusivamente en dev; no se modifica prd, devel, GHCR ni Kubernetes. Nuevos jobs de validacion unificada quedan pendientes de resultado tras el push.

## Candidato de remediación Go en dev — 2026-10-14
- Se identificó el origen del binario: `operator-framework/ansible-operator-plugins` release `v1.42.3`, commit exacto `292a56a4877c8093037c0533f3ef3c7a6bbd78e2` (tag anotado validado por GitHub).
- Dockerfile en dev incorpora una etapa `golang:1.26.9` que obtiene el origen y compila `./cmd/ansible-operator` con `CGO_ENABLED=0`. Se solicita la actualización de `golang.org/x/net@v0.60.0`, `golang.org/x/text@v0.39.0`, `google.golang.org/grpc@v1.83.2` y se recalculan dependencias mediante `go mod tidy`.
- El binario compilado sustituye en la imagen candidata al binario Go embebido en la imagen base; se conservan los componentes de runtime y las verificaciones Python. La corrección necesita validar compatibilidad y el reporte Trivy; **no se afirma remediación hasta obtener resultado**.
- Sólo rama dev y Docker build local del CI, sin publicar imagen. No hay cambios en prd, devel, GHCR o clúster de Kubernetes.
