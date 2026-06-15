# Propuesta de Gestión de Vulnerabilidades en la Cadena de Suministro

## 1. Contexto del análisis

En el presente trabajo se evaluó la seguridad de la cadena de suministro de software de una selección de 9 repositorios Open Source: **Ghost, Apache Superset, Gitea, Hoppscotch, LibreNMS, Mastodon, Snipe-IT, Wiki.js y ZoneMinder**. Estos repositorios fueron seleccionados por la variedad de tecnologías (Go/Node/PHP/Ruby/Python/C++).

El proceso de auditoría cubrió múltiples dimensiones del ciclo de vida del desarrollo:

- Generación de SBOMs (Software Bill of Materials) mediante Syft.
- Análisis de vulnerabilidades en dependencias (SCA) con Grype.
- Escaneo estático de código fuente (SAST) con CodeQL.
- Auditoría de postura de seguridad y configuraciones de pipelines de CI/CD (GitHub Actions).

Dada la alta volumetría de datos generada, el objetivo de este documento es proponer un modelo de gestión integral. En las siguientes secciones se aplica un análisis estructurado sobre una muestra representativa de hallazgos críticos, permitiendo priorizar el riesgo y tomar decisiones de mitigación basadas en evidencia.

## 2. Vulnerabilidades encontradas

![Distribución de vulnerabilidades según su severidad](evidence/capturas/distribucion_severidad.png)

En total se identificaron 2740 hallazgos, distribuidos en 29 críticos, 316 altos, 2303 medios y 92 bajos. Esta cifra agrega dos fuentes complementarias: **736 vulnerabilidades en dependencias** (Grype/SCA) y **2004 hallazgos en código fuente** (CodeQL/SAST). Las 29 críticas y las 316 altas provienen en su totalidad del SCA (Grype); el predominio de la severidad "media" (2303) proviene principalmente de las advertencias de CodeQL, que no generó hallazgos críticos ni altos. Cabe precisar que el conteo refleja _instancias_ por versión y ruta afectada —no CVEs únicos—, por lo que una misma librería vulnerable presente en varias versiones suma varias filas (ej. `vm2 @ 3.11.3` con 5 instancias críticas).

![Concentración de vulnerabilidades críticas por repositorio](evidence/capturas/concentracion_criticas_repo.png)

La concentración de hallazgos críticos se ubica principalmente en el repositorio wiki (20) con afectaciones en múltiples dependencias, seguido por apache-superset (5) debido a la presencia repetida de la librería vm2, hoppscotch (2), y de manera aislada en snipe-it (1) y Ghost (1).

## 3. Clasificación según vector de ataque

Las vulnerabilidades y hallazgos identificados se agrupan en los tres vectores de ataque principales definidos para la gestión de este análisis:

- **Vector 1: Dependencias y código fuente:** Vulnerabilidades integradas directamente en el artefacto de software. Incluye inyecciones SQL en repositorios como Gitea y ejecución de código arbitrario en librerías de terceros (ej. `underscore` en el proyecto Wiki.js).
- **Vector 2: Pipelines de CI/CD:** Riesgos en la infraestructura de automatización. Destacan la exposición de secretos en texto claro dentro de scripts y el uso inseguro de GitHub Actions mediante "tags mutables" combinados con permisos excesivos por defecto.
- **Vector 3: Humanos:** Deficiencias en la gobernanza y prácticas del equipo. Se evidencia por la carencia de revisión obligatoria de código (ausencia de archivos `CODEOWNERS`) y la falta de automatización para el parcheo de dependencias de forma continua.

## 4. Análisis usando el ciclo Conozco → Verifico → Evidencio → Decido y Actúo

A continuación, se desarrolla el ciclo de gestión para una muestra representativa de vulnerabilidades críticas que abarcan los tres vectores estudiados.

### Análisis 1: Inyección de Secretos en Pipeline de Wiki.js (Vector 2: Pipelines)

- **Conozco:** La auditoría manual de los flujos de GitHub Actions reveló un riesgo crítico en el repositorio `wiki` (hallazgo C-1). Se utiliza un secreto (`HELM_REPO_PASSWORD`) directamente dentro de un script de shell en el pipeline de despliegue.
- **Verifico:** Inyectar secretos directamente en un comando `run:` es inseguro: el valor real queda en la **lista de procesos** del runner (los argumentos de `helm cm-push`, que GitHub **no** enmascara) y, aunque GitHub oculta los secretos en los logs por defecto, ese enmascaramiento es evadible (transformaciones, coincidencias parciales). Quedan expuestos tanto `HELM_REPO_USERNAME` como `HELM_REPO_PASSWORD`, comprometiendo el acceso al registro de Helm.
- **Evidencio:** El archivo `.github/workflows/helm.yml` (línea 26) ejecuta `helm cm-push … --username="${{secrets.HELM_REPO_USERNAME}}" --password="${{secrets.HELM_REPO_PASSWORD}}" …`. Screenshot en `/evidence/capturas/helm_wiki.png`
- **Decido y Actúo:**
  - _Decisión:_ La exposición potencial de credenciales de infraestructura representa un riesgo crítico de cadena de suministro y debe subsanarse inmediatamente.
  - _Acción:_ Modificar el workflow para que el secreto se asigne a una variable de entorno segura en el bloque `env:`, invocando la variable dentro del script de bash sin interpolación directa.

### Análisis 2: Ejecución Ciega de Binarios y Permisos Excesivos en Hoppscotch (Vector 2: Pipelines)

- **Conozco:** La auditoría manual de los flujos de GitHub Actions en `hoppscotch` (archivo `build-hoppscotch-agent.yml`) reveló vulnerabilidades críticas de envenenamiento de cadena de suministro. Existe ausencia total del bloque global de permisos y se realiza la descarga de dependencias binarias externas sin validación de integridad.
- **Verifico:** Por un lado, las acciones de terceros utilizan tags mutables (`@v1` o `@v3`), asumiendo permisos amplios por defecto. Por otro lado, en múltiples _steps_ de preparación (ej. instalación de `cargo-tauri` o `trunk`), el pipeline utiliza comandos `curl` para descargar archivos comprimidos de repositorios de terceros, los cuales son desempaquetados y ejecutados (`chmod +x`) sin verificar previamente su checksum (SHA256). Si el release de origen es alterado por un atacante, el pipeline ejecutaría código malicioso, exponiendo todos los secretos de firma criptográfica (Apple y Azure) inyectados en el entorno.
- **Evidencio:** Archivo `.github/workflows/build-hoppscotch-agent.yml` (líneas 85-88, 185-187, 293-300 y 385-392), donde se descarga y ejecuta código de `github.com/tauri-apps` y `github.com/thedodd/trunk` sin comandos de verificación de hash previos; además, los jobs de Windows descargan `trusted-signing-cli.exe` vía `Invoke-WebRequest` sin validación (líneas 466 y 555). Adicionalmente, el workflow carece del bloque `permissions:`. Screenshot en `/evidence/capturas/hoppscotch_binarios.png`
- **Decido y Actúo:**
  - _Decisión:_ La inyección de código de terceros no validado durante el proceso de _build_ compromete absolutamente la integridad de los artefactos generados. Es un riesgo inaceptable.
  - _Acción: 1_ Modificar los scripts de bash para que, tras el comando `curl`, se exija la validación del hash del archivo descargado (ej. mediante `sha256sum -c`) contra un hash duro almacenado de forma segura en el repositorio.
  - _Acción: 2_ Declarar `permissions: contents: read` a nivel global en el YAML.
  - _Acción: 3_ Fijar las GitHub Actions a hashes SHA inmutables (`@<SHA-completo>`). Para mitigar el impacto en el mantenimiento y evitar que el pipeline quede obsoleto (deuda técnica), se debe integrar esta medida obligatoriamente con una herramienta de gestión de dependencias como Dependabot o Renovate, la cual automatice la actualización de dichos hashes.

### Análisis 3: Ejecución de Código Arbitrario en Wiki.js (Vector 1: Dependencias)

- **Conozco:** A través del escaneo SCA (Grype), se detectó una vulnerabilidad crítica de Ejecución de Código Arbitrario (ACE) en la dependencia `underscore` utilizada en el repositorio `wiki`.
- **Verifico:** El fallo afecta a las versiones `1.6.0`, `1.8.3` y `1.9.1` de la librería `underscore`. Un atacante podría aprovechar este vector si el software expone funciones de evaluación u objetos sin control a entradas externas. Estas tres versiones conviven en `yarn.lock` junto a una versión sana (`1.13.1`), lo que indica que `underscore` entra como **dependencia transitiva** arrastrada por distintos paquetes, no como dependencia directa de Wiki.js.
- **Evidencio:** El reporte SCA vincula estas versiones al identificador `GHSA-cf4h-3jhx-xvhq` con una severidad "Critical".
- **Decido y Actúo:**
  - _Decisión:_ `underscore` es una vulnerabilidad crítica de ejecución de código, aunque transitiva y condicionada a que la aplicación pase entrada no confiable a funciones tipo `_.template`. Se le suma `tar` (severidad **High** en wiki, no crítica), con riesgo de escritura de archivos fuera de ruta (Zip Slip). El impacto potencial es alto, pero no es un "compromiso total" garantizado: la prioridad es confirmar la alcanzabilidad y resolver la cadena transitiva.
  - _Acción:_ Al ser transitiva, la remediación de `underscore` **no es un `update` directo**: hay que identificar con `yarn why underscore` el paquete padre que arrastra cada versión vulnerable y decidir entre actualizar ese padre, aplicar un `resolutions`/override (con su propio riesgo de incompatibilidad), o aceptar el riesgo si la ruta no resulta alcanzable. En paralelo, es imperativo auditar las funciones de extracción de archivos en Wiki.js para implementar restricciones de rutas (path sanitization), bloqueando explícitamente ataques de Zip Slip o Hardlink Traversal.

### Análisis 4: Escape de Sandbox en Apache Superset (Vector 1: Dependencias)

- **Conozco:** Múltiples vulnerabilidades críticas en la librería `vm2` (ej. `GHSA-m4wx-m65x-ghrr`).
- **Verifico:** `vm2` es una librería de _sandboxing_ de JavaScript con escape de sandbox conocido; su propio autor la deprecó por considerarla insegura por diseño. **No obstante, en este repositorio las instancias vulnerables aparecen en dependencias del frontend y de los tests, no en el backend Python de Superset.** Los CVEs describen un escape que _en abstracto_ permitiría ejecución de código, pero **no verificamos que `vm2` sea alcanzable en tiempo de ejecución** dentro del flujo de Superset.
- **Evidencio:** El reporte `resumen_vulnerabilidades.csv` lista 5 instancias críticas de `vm2 @ 3.11.3` (más 3 High, 1 Medium y 1 Low). En `results/apache-superset-grype-raw.json` esas instancias se ubican en `superset-frontend/package-lock.json` y `superset-frontend/cypress-base/package-lock.json` (build de frontend y _tooling_ de Cypress).
- **Decido y Actúo:**
  - _Decisión:_ `vm2` es una librería de _sandboxing_ deprecada con escape conocido; tratarla como barrera confiable es un error de diseño. Sin embargo, como su alcanzabilidad en runtime no está confirmada, la clasificamos como **"crítica-a-verificar"** y no como un RCE de servidor confirmado: la remediación no puede limitarse a un simple `npm update`, pero tampoco justifica una migración de arquitectura sin antes verificar el contexto.
  - _Acción:_ Primero, **confirmar la alcanzabilidad de `vm2`** (cómo y dónde se invoca, y si procesa entrada no confiable). Si se confirma que ejecuta código no confiable, evaluar la migración a un entorno más seguro (Worker Threads con restricciones de SO, o `isolated-vm`). Si solo está presente en _build_/tests sin entrada no confiable, el riesgo operativo es bajo y la acción se reduce a actualizarla o eliminarla del árbol de dependencias.

### Análisis 5: Inyección SQL en Gitea (Vector 1: Código Fuente)

- **Conozco:** CodeQL reportó una vulnerabilidad de inyección SQL en el código fuente del repositorio Gitea. El archivo afectado es `models/issues/milestone_list.go` .
- **Verifico:** Se revisa el reporte SAST y el código fuente. Aunque la herramienta lo clasifica genéricamente como inyección SQL, se verifica que el ORM protege contra inyecciones clásicas (SQLi) mediante sentencias preparadas. No obstante, se confirma que el framework pasa la entrada del usuario a una cláusula `LIKE` sin escapar, y se detecta una omisión en la cadena de métodos del ORM que ignora la validación de permisos del repositorio. CodeQL detectó 2 hits de `go/sql-injection` en `milestone_list.go` (líneas 184 y 196).
- **Evidencio:** El SARIF nativo de CodeQL (`results/gitea_temp.sarif`) clasifica la regla `go/sql-injection` como **High** (`security-severity` 8.8, `CWE-089`). En el `resumen_vulnerabilidades.csv` figura como "Medium" porque el archivo derivado `gitea-codeql.json` normalizó todas las severidades a `warning`; tras la verificación manual (ver _Decido y Actúo_) la **operacionalizamos como Media**. Captura de pantalla: `evidence/capturas/inyeccion_sql_gitea.png`.
- **Decido y Actúo:**
  - _Decisión:_ Aunque el ORM previene inyecciones SQL tradicionales (SQLi) mediante el uso de sentencias preparadas, la entrada del usuario se pasa directamente a una cláusula `LIKE` sin sanitizar los caracteres comodín (`%`,`_`). Esto representa un riesgo de Inyección de Comodines que podría derivar en una Denegación de Servicio (DoS) por agotamiento de recursos en la base de datos. Por ello, **aunque CodeQL la reporta como High (8.8), la priorizamos operacionalmente como Media**: la verificación demuestra que el impacto real no es exfiltración de datos sino degradación del servicio.
  - _Acción:_ Refactorizar la función en `milestone_list.go` (específicamente donde se usa `builder.Like`) para implementar una función de limpieza que escape explícitamente los caracteres comodín de SQL en la variable `keyword` antes de que el ORM construya la consulta. Adicionalmente, revisar la lógica de construcción de `sess` para resolver la pérdida de condiciones de acceso (posible IDOR).

### Análisis 6: Falta de Gobernanza como Causa Raíz en Wiki.js (Vector 3)

- **Conozco:** Wiki.js es el único repositorio del corpus que combina las tres carencias de gobernanza simultáneamente: sin Dependabot/Renovate, sin CODEOWNERS, y workflows sin bloque `permissions:`. En paralelo, es también el repositorio con mayor concentración de vulnerabilidades críticas SCA del estudio (20 instancias críticas, ≈ 12 paquetes únicos).
- **Verifico:** Se cruza la matriz V3 del reporte_auditoria_github.md (fila `wiki`) con el conteo de severidades Critical/High del resumen_vulnerabilidades.csv filtrado por `Repositorio = wiki`. La correlación es directa: la ausencia de automatización de parches (V3.2) explica por qué versiones como `underscore@1.6.0`, `minimist@0.0.8` o `xmldom@0.1.27` —deprecadas hace años— siguen vigentes en el árbol de dependencias.
- **Evidencio:**
  | Repo | SECURITY.md | Dependabot | CODEOWNERS | CVEs Críticos SCA |
  |--------|:-----------:|:----------:|:----------:|:-----------------:|
  | wiki | ✅ | ❌ | ❌ | 20 |
  | Ghost | ✅ | ✅ | ✅ | 1 |
- **Decido y Actúo:** Wiki.js evidencia que la deuda técnica de seguridad no se origina
  en los desarrolladores, sino en la AUSENCIA de mecanismos automáticos.
  - _Acciones:_
    - introducir `.github/dependabot.yml` con todos los ecosistemas (npm, github-actions).
    - establecer `CODEOWNERS` para módulos críticos como autenticación SAML (`server/modules/authentication`) y persistencia (`server/db`).
    - habilitar Branch Protection Rules que exijan revisión.

## 5. Priorización de vulnerabilidades

La priorización se construye evaluando cinco criterios para cada hallazgo: **severidad** (CVSS/clasificación de la herramienta), **exposición** (si el componente afectado es accesible externamente), **facilidad de explotación** (si existe exploit público o el ataque es trivial), **impacto** (alcance del daño potencial: RCE, exfiltración, DoS) y **evidencia disponible** (nivel de confirmación empírica del hallazgo). El resultado es el siguiente orden de remediación:

1. **Prioridad 1 (Crítica) — Integridad de la cadena de suministro (Vector 2):** La exposición de secretos en `wiki` (C-1) y la ejecución ciega de binarios externos en `hoppscotch` (C-4) combinan severidad crítica con facilidad de explotación alta (un atacante que comprometa el origen del artefacto o el runner tiene acceso inmediato a todos los secretos de firma criptográfica). La evidencia es directa: líneas específicas en workflows auditados. Impacto: compromiso total del pipeline y de los artefactos publicados.
2. **Prioridad 2 (Alta) — Ejecución de código arbitraria (Vector 1):** Vulnerabilidades SCA con severidad crítica y advisories documentados (GHSA): `underscore` en `wiki` (transitiva) y `vm2` en `apache-superset` (presente en frontend/tests). El impacto _potencial_ es alto —RCE o escape de sandbox—, pero su explotabilidad real está **sujeta a verificar la alcanzabilidad** del componente en runtime, por lo que no la damos por confirmada.
3. **Prioridad 3 (Media) — Inyecciones en código fuente (Vector 1):** La inyección SQL en Gitea (`milestone_list.go`) tiene severidad media porque el ORM previene SQLi clásico; sin embargo, la omisión en la validación de comodines puede derivar en DoS por agotamiento de recursos. Requiere parche pero no detiene operaciones.
4. **Prioridad 4 (Media) — Postura de gobernanza (Vector 3):** La ausencia de Dependabot y CODEOWNERS no es una vulnerabilidad explotable directamente, pero es la causa raíz que permite la acumulación de deuda técnica (demostrado en `wiki`). Se aborda después de los riesgos activos, pero es transversal a toda la organización.
5. **Prioridad 5 (Baja) — Fallos aislados (Vector 1):** Vulnerabilidades tipo ReDoS que solo resultan en caídas de servicio a nivel cliente, o vulnerabilidades presentes únicamente en herramientas de prueba (`devDependencies`). Bajo impacto operacional y sin evidencia de explotación activa.

## 6. Acciones propuestas (Plan de remediación global)

- **Refactorización de código:** Sanitizar proactivamente la entrada del usuario (por ejemplo, escapando caracteres especiales y comodines en búsquedas) y auditar la lógica del ORM para garantizar que las políticas de control de acceso y filtrado por permisos se apliquen de forma estricta e inmutable en todas las consultas.
- **Hardening de Pipelines (CI/CD):** El orden importa, por contexto. (1) Establecer **primero** la automatización de actualizaciones (Dependabot/Renovate); fijar Actions a SHA _sin_ esa automatización es contraproducente, porque congela la acción en una versión que dejará de recibir parches —de hecho, 5 de 9 repos del corpus no tienen Dependabot—. (2) Sobre esa base, migrar de "tags mutables" a "commit SHA" inmutables, **priorizando las Actions de terceros / no oficiales** (mayor riesgo de compromiso) y aceptando _tags_ de versión mayor en las oficiales de proveedores confiables; cabe reconocer que el bot no elimina el costo de mantenimiento, lo traslada a la revisión recurrente de PRs. (3) Requerir validación criptográfica (checksums) de todo artefacto o binario descargado durante el build. (4) Mover la gestión de contraseñas de línea de comandos a inyección segura de variables de entorno y declarar `permissions:` mínimos por workflow.
- **Políticas Organizacionales e Ingeniería Humana:** Instaurar archivos `.github/dependabot.yml` y `CODEOWNERS` como requerimientos estándar para todos los repositorios productivos.

## 7. Evidencia utilizada

Toda la propuesta está debidamente respaldada por los artefactos recopilados, ubicados en los directorios del repositorio de la siguiente forma:

- `results/`: Contiene los archivos crudos generados en formato JSON y SARIF resultantes del paso de Syft, Grype y CodeQL por cada repositorio.
- `evidence/capturas/distribucion_severidad.png`: Gráfico generador a partir del archivo `evidence/reportes/resumen_vulnerabilidades.csv` que muestra la distribución de vulnerabilidades según su severidad.
- `evidence/capturas/helm_wiki.png`: Captura de pantalla del archivo `.github/workflows/helm.yml` que muestra el uso de un secreto directamente dentro de un script de shell en el pipeline de despliegue.
- `evidence/capturas/inyeccion_sql_gitea.png`: Captura de pantalla del archivo `gitea/models/issues/milestone_list.go` que muestra la lógica de construcción de la consulta SQL con parámetros dinámicos.
- `evidence/capturas/hoppscotch_binarios.png`: Captura de pantalla del archivo `.github/workflows/build-hoppscotch-agent.yml` que muestra la descarga de binarios y posterior ejecución.
- `evidence/reportes/resumen_vulnerabilidades.csv`: Agregado final de vulnerabilidades (SCA y SAST) identificadas a lo largo del proceso.
- `evidence/reporte_auditoria_github.md`: Documento elaborado para constatar las debilidades en los archivos de control (.github) y workflows de CI/CD.
- `scripts/`: Scripts en Python empleados para la extracción automatizada y orquestación de datos.

## 8. Conclusiones

Proteger la cadena de suministro de software requiere un enfoque tridimensional. Como demostró este análisis práctico, detectar vulnerabilidades en el código fuente o en dependencias (Vector 1) pierde efectividad si los atacantes pueden saltarse estos controles envenenando directamente la tubería de despliegue automatizado (Vector 2) debido a configuraciones de permisos negligentes. Al aplicar de forma cíclica el método **Conozco, Verifico, Evidencio, Decido y Actúo**, logramos trascender del simple escaneo técnico hacia un modelo de gestión y gobernanza activa que prioriza riesgos reales (Vector 3), blindando la organización de manera eficiente. Es destacable que los 9 repositorios cuentan con `SECURITY.md`, lo que refleja madurez en la comunicación de seguridad, pero contrasta con la pobre implementación operativa de `Dependabot` (5/9, aunque existe parcialmente en snipe-it y zoneminder), `CODEOWNERS` (4/9) y pinning de Actions (4/9). La cultura existe; falta la automatización.

## 9. Reconocimientos y Licencia

Este proyecto utiliza y modifica scripts originales proporcionados para esta actividad académica, cuyos derechos de autor pertenecen a fastai (2022) bajo la Licencia Apache 2.0.

**Modificaciones y aportes realizados en este repositorio:**

- Creación del entorno de ejecución interactivo (`scripts/vulnerability_analysis.ipynb`).
- Modificación de los scripts base (`add_submodules.py`, `generate_codeql.py`, `generate_grype.py`, `generate_sboms.py`) para integrar un sistema de salida y registro de logs (`*.log`).
- Actualización del archivo `/data/repos.json` con la selección de los 9 repositorios Open Source analizados.
- Generación de toda la documentación de auditoría, directorios de evidencia (`evidence/`) y resultados crudos (`results/`).
