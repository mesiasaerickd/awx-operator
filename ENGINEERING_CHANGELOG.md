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
