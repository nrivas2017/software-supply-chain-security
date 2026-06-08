# Propuesta de Gestión de Vulnerabilidades en la Cadena de Suministro

## 1. Contexto del análisis

En el presente trabajo se evaluó la seguridad de la cadena de suministro de software de una selección de 9 repositorios Open Source: **Ghost, Apache Superset, Gitea, Hoppscotch, LibreNMS, Mastodon, Snipe-IT, Wiki.js y ZoneMinder**. 

El proceso de auditoría incluyó la generación de SBOMs (Software Bill of Materials) mediante Syft, análisis de vulnerabilidades en dependencias (SCA) con Grype, escaneo estático de código fuente (SAST) con CodeQL, y una revisión profunda de las configuraciones de los pipelines de CI/CD (GitHub Actions) y políticas de los equipos de desarrollo. 

Dada la gran volumetría de datos generada (cientos de alertas de seguridad), el objetivo de este documento es proponer un modelo de gestión integral. Para ilustrar esta propuesta, en las siguientes secciones se aplica el ciclo de análisis sobre una **muestra representativa con los hallazgos más críticos e ilustrativos** extraídos de todo el ecosistema evaluado, permitiendo así tomar decisiones de mitigación basadas en evidencia.

## 2. Vulnerabilidades encontradas

![Distribución de vulnerabilidades según su severidad](evidence/capturas/distribucion_severidad.png)

A través del uso de herramientas SCA (Grype) y SAST (CodeQL), así como auditorías de configuración, se identificaron fallos críticos en múltiples capas del ciclo de vida del software en los repositorios analizados. Las vulnerabilidades abarcan desde problemas en librerías de pruebas y defectos de renderizado en el código fuente, hasta malas configuraciones de seguridad en los flujos de despliegue automatizado y carencias en la gobernanza y mantenimiento de los proyectos.

## 3. Clasificación según vector de ataque

Las vulnerabilidades y hallazgos identificados se agrupan en los tres vectores de ataque principales definidos para este análisis:

- **Vector 1: Dependencias y código fuente:** Inyecciones de rutas (Path Injection), ReDoS, Command Injection y Server-Side Request Forgery (SSRF) presentes tanto en librerías de terceros (ej. `lodash`, `@cypress/request`) como en componentes internos desarrollados por los equipos (ej. `renderer.js` en Ghost).
- **Vector 2: Pipelines de CI/CD:** Exposición e inyección de secretos de infraestructura directamente en scripts de shell (ej. repositorio `wiki`) y el uso inseguro de GitHub Actions mediante "tags mutables", lo que facilita el envenenamiento de la cadena de suministro.
- **Vector 3: Humanos:** Carencia de políticas de seguridad preventivas, evidenciada por la ausencia de reglas de revisión de código (falta de archivos `CODEOWNERS`) y la falta de automatización para el parcheo de dependencias (ausencia de `Dependabot` o `Renovate`), como se detectó en proyectos como `librenms`.

## 4. Análisis usando el ciclo Conozco → Verifico → Evidencio → Decido y Actúo

A continuación, se desarrolla el ciclo de gestión para una muestra representativa de vulnerabilidades críticas y medias descubiertas.

### Análisis 1: SSRF en Apache Superset (Vector: Dependencias)

- **Conozco:** A través de Grype, detectamos una vulnerabilidad de *Server-Side Request Forgery (SSRF)* en la dependencia `@cypress/request` (versión 2.88.12) dentro del repositorio `apache-superset`. Curiosamente, la herramienta catalogó la severidad como "Low".
- **Verifico:** Como equipo de seguridad, verificamos que un SSRF no es de severidad baja. Sin embargo, al inspeccionar el entorno del paquete afectado, verificamos que *Cypress* es una herramienta de pruebas End-to-End (E2E). El riesgo real es mitigado porque la vulnerabilidad reside en un submódulo aislado dedicado exclusivamente a pruebas, el cual no se empaqueta ni se despliega en el servidor de producción.
- **Evidencio:** \* Reporte SCA: `apache-superset-grype.json` reporta `GHSA-p8p7-x288-28g6`.
  - Declaración en código: El archivo `superset-frontend/cypress-base/package.json` confirma que el contexto es puramente de pruebas:
    ```
    {
      "name": "superset-cypress",
      "description": "run cypress against superset",
      "devDependencies": {
        "cypress": "^11.2.0",
        "eslint-plugin-cypress": "^3.5.0"
      }
    }
    ```
- **Decido y Actúo:**
  - *Decisión:* Dado que la evidencia muestra que es un entorno de desarrollo/testing, la prioridad de parcheo es secundaria frente a vulnerabilidades de producción, pero debe mitigarse para proteger el entorno de CI.
  - *Acción:* Actualizar el ecosistema de Cypress a una versión parcheada. Implementar una regla en el pipeline de despliegue para asegurar (como medida de defensa en profundidad) que las dependencias de la carpeta `cypress-base` nunca se incluyan en el build final de producción.

### Análisis 2: Path Injection en Ghost (Vector: Código Fuente)

- **Conozco:** CodeQL detectó una inyección de rutas (Path Injection) en el archivo de Ghost: `ghost/core/core/frontend/services/rendering/renderer.js` (línea 35), donde una ruta depende de un valor proveído por el usuario.
- **Verifico:** El equipo debe confirmar si el input del usuario ("user-provided value") llega a esta función `renderer.js` de forma directa sin ser sanitizada previamente por los middlewares o controladores de entrada del framework.
- **Evidencio:** _ Reporte SAST: `Ghost-codeql.json` advierte: _"This path depends on a user-provided value"\*.
  - Log de CodeQL: Archivo afectado `renderer.js`, región de código de la línea 35, columna 16 a la 29.
- **Decido y Actúo:**
  - *Decisión:* Las vulnerabilidades de Path Traversal/Injection en componentes de frontend/renderizado pueden derivar en fuga de información local. Su gestión es prioritaria.
  - *Acción:* Refactorizar la función en `renderer.js` utilizando la librería `path.resolve` de Node.js combinada con comprobaciones estrictas para rechazar caracteres como `../` o `%2e%2e%2f` en el input del usuario antes de tocar el sistema de archivos.

### Análisis 3: ReDoS en Interfaz de Usuario de Ghost (Vector: Código Fuente)

- **Conozco:** CodeQL encontró múltiples riesgos de Expresión Regular Polinómica (ReDoS) en el archivo `apps/admin-x-design-system/src/global/form/currency-field.tsx` de Ghost.
- **Verifico:** Al ser un componente de React (tsx) ejecutado en el cliente/administrador, verificamos que un ReDoS podría congelar el navegador del administrador que ingrese valores de moneda anómalos, pero difícilmente causará una caída del servidor backend. Es un ataque de denegación de servicio del lado del cliente.
- **Evidencio:** Archivo `Ghost-codeql.json` en la regla `js/polynomial-redos`.
- **Decido y Actúo:**
  - *Decisión:* Riesgo medio. Afecta la usabilidad del sistema administrativo, pero no compromete los datos.
  - *Acción:* Delegar al equipo de Frontend el reemplazo de la expresión regular defectuosa por un validador de divisas estándar (como `Intl.NumberFormat`) que no sufra de _catastrophic backtracking_.

### Análisis 4: Inyección de Secretos en Pipeline de CI/CD (Vector 2: Pipelines)

- **Conozco:** La auditoría de los flujos de GitHub Actions reveló un riesgo crítico en el repositorio `wiki` (línea 26), se utiliza un secreto directamente dentro de un script de shell.
- **Verifico:** Inyectar secretos en línea en un intérprete de bash es altamente inseguro. Si otra variable controlada por el usuario se procesa en el mismo bloque, un atacante podría alterar el comando y provocar que GitHub Actions imprima el secreto en los logs públicos, comprometiendo la infraestructura de despliegue.
- **Evidencio:** Archivo `.github/workflows/helm.yml` en el repositorio `wiki`:
  ```
  - run: helm registry login ... --password="${{secrets.HELM_REPO_PASSWORD}}"
  ```

- **Decido y Actúo:**
  - *Decisión:* La exposición potencial de credenciales de despliegue representa el riesgo más alto del sistema, ya que otorga acceso directo a la infraestructura.
  - *Acción:* Modificar el workflow para que el secreto se asigne a una variable de entorno de forma segura, evitando la interpolación directa en el shell:
    ```
    - run: helm registry login ... --password="$HELM_REPO_PASSWORD"
      env:
        HELM_REPO_PASSWORD: ${{ secrets.HELM_REPO_PASSWORD }}
    ```

### Análisis 5: Ausencia de Políticas de Revisión y Actualización (Vector 3: Humanos)

- **Conozco:** Se evaluaron las prácticas del equipo revisando los archivos estáticos de configuración en los repositorios. Mientras que repositorios maduros como `Ghost` cuentan con automatización de dependencias (`renovate.json5`) y responsables de código (`CODEOWNERS`), proyectos como `librenms` carecen de ambos mecanismos.
- **Verifico:** La ausencia de `CODEOWNERS` implica que no hay reglas técnicas que obliguen a la revisión por pares antes de hacer un "merge" a la rama principal. Además, sin herramientas como Dependabot, el descubrimiento de vulnerabilidades (Vector 1) depende exclusivamente del factor humano, garantizando que el software operará con dependencias obsoletas e inseguras. 
- **Evidencio:** El reporte de auditoría de configuración de repositorios arroja los siguientes indicadores críticos de falta de gobernanza en `librenms`:
  | Repositorio | SECURITY.md | Dependabot/Renovate | CODEOWNERS |
  |---|---|---|---|
  | librenms | ✅ | ❌ | ❌ |
- **Decido y Actúo:** 
  - *Decisión:* Las deficiencias en las prácticas humanas no son vulnerabilidades explotables directamente, pero son la causa raíz que permite que los Vectores 1 y 2 existan.
  - *Acción:* Establecer protección de ramas (Branch Protection Rules) en GitHub exigiendo al menos 1 revisión aprobada para `main` apoyada en la creación de un archivo `CODEOWNERS`. Incorporar un archivo `.github/dependabot.yml` base en todos los repositorios de la organización para automatizar el parcheo de dependencias.

### Análisis 6: Tags mutables y permisos por defecto en Hoppscotch (Vector 2: Pipelines)

- **Conozco:** La auditoría de los workflows de GitHub Actions reveló dos prácticas inseguras simultáneas en el repositorio `hoppscotch`: (1) **los 4 workflows carecen completamente del bloque `permissions:`**, lo que otorga al `GITHUB_TOKEN` los permisos por defecto de la organización (potencialmente con `write` heredado); y (2) **las 13+ Actions de terceros usan tags mutables** (`@v3`, `@v4`, `@v1`) en lugar de SHAs inmutables, incluyendo Actions no oficiales como `actions-rs/toolchain@v1` y `apple-actions/import-codesign-certs@v3`.
- **Verifico:** Confirmamos que ambas condiciones se cumplen simultáneamente revisando los 4 archivos en `.github/workflows/` del repositorio. Verificamos que el riesgo no es teórico: un tag como `@v3` apunta a una referencia mutable que el mantenedor (o un atacante que comprometa la cuenta del mantenedor) puede reasignar a un commit malicioso en cualquier momento — un patrón documentado en incidentes reales de supply chain como tj-actions/changed-files (CVE-2025-30066). Combinado con la ausencia de `permissions:`, una Action comprometida ejecutándose en CI podría escribir en el repositorio, publicar releases falsos o exfiltrar secretos.
- **Evidencio:**
  - **Reporte de auditoría** (`evidence/reporte_auditoria_github.md`, hallazgos C-2 y C-3):
    | # | Vector | Hallazgo | Evidencia |
    |---|---|---|---|
    | C-2 | V2.1 | Ausencia total de bloque `permissions:` en los 4 workflows | Todos los archivos en `.github/workflows/` |
    | C-3 | V2.2 | 13+ Actions de terceros con tags mutables | `build-hoppscotch-agent.yml:59,65,73,90`, `release-push-docker.yml:22,28,31,34,41`, `tests.yml:22,28`, etc. |
    
  - **Muestra de líneas afectadas** (ejemplo de `build-hoppscotch-agent.yml`):
    ```yaml
    - uses: actions/checkout@v3            # línea 59 — mutable
    - uses: actions/setup-node@v3          # línea 65 — mutable
    - uses: actions-rs/toolchain@v1        # línea 73 — mutable + 3rd party
    - uses: apple-actions/import-codesign-certs@v3  # línea 90 — mutable + 3rd party
    ```
- **Decido y Acto:**
  - *Decisión:* Riesgo **crítico de cadena de suministro**. A diferencia de una vulnerabilidad en una dependencia de producción (que requiere que un atacante logre llegar al endpoint vulnerable), una Action comprometida ejecuta código **directamente dentro del pipeline de build**, con acceso a secretos y permisos de escritura en el repositorio. El impacto es equivalente al hallazgo C-1 de wiki, pero con mayor superficie (4 workflows vs 1).
  - *Acción:*
    1. **Anclar todas las Actions a su Commit SHA exacto** usando una herramienta como [`pin-github-action`](https://github.com/mheap/pin-github-action) o el ecosistema `github-actions` de Dependabot:
    ```yaml
    # Antes
    - uses: actions/checkout@v3
    # Después
    - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
    ```
    2. **Declarar `permissions:` explícitos por workflow**, partiendo del principio de mínimo privilegio:
    ```yaml
    permissions:
      contents: read   # solo lectura por defecto
    ```
    Y otorgar permisos adicionales (`packages: write`, `id-token: write`, etc.) únicamente en los jobs que los requieran.
    3. **Habilitar `Dependabot` para `github-actions`** (`.github/dependabot.yml`) para que las actualizaciones de SHA lleguen como PRs revisables, evitando que el pinning se convierta en deuda técnica.


## 5. Priorización de vulnerabilidades

Para gestionar eficientemente los hallazgos, se propone la siguiente priorización basada en severidad, exposición y facilidad de explotación:

1. **Prioridad 1 (Crítica) - Riesgos en CI/CD (Vector 2):** Se debe resolver inmediatamente (a) la inyección de secretos en `helm.yml` del repositorio `wiki` (Análisis 4) y (b) la combinación de permisos por defecto + tags mutables en `hoppscotch` y `snipe-it` (Análisis 6). Un pipeline comprometido permite envenenar futuras entregas de software (Supply Chain Attack) independientemente de qué tan seguro sea el código fuente.
2. **Prioridad 2 (Alta) - Vulnerabilidades SAST con acceso externo (Vector 1):** Inyecciones de rutas (Path Injection en Ghost) o Inyecciones SQL (Knex), ya que pueden ser explotadas por usuarios maliciosos desde el exterior sin requerir autenticación privilegiada.
3. **Prioridad 3 (Media) - Dependencias de producción y prácticas Humanas:** Parchear componentes vulnerables del lado del servidor y habilitar reglas de revisión humana (`CODEOWNERS`).
4. **Prioridad 4 (Baja) - Denegación de servicio en cliente y devDependencies:** Problemas como ReDoS en interfaces de administración interna (Ghost) o SSRF en dependencias de testing (Superset), debido a que su impacto está altamente encapsulado.

## 6. Acciones propuestas (Plan de remediación global)

- **Refactorización de código:** Reemplazar funciones de ruteo y expresiones regulares identificadas por herramientas SAST, aplicando validaciones estrictas de entrada.
- **Hardening de Pipelines:** Fijar todas las GitHub Actions por su *Commit SHA* exacto y reestructurar el manejo de secretos en los workflows.
- **Políticas Organizacionales:** Exigir `SECURITY.md` y escaneos de `Dependabot` en todos los proyectos como criterio mínimo para pasar a producción.

## 7. Evidencia utilizada

Toda la propuesta está fundamentada en los siguientes artefactos, ubicados en los directorios correspondientes del repositorio de entrega:

- `results/`: Archivos JSON crudos generados por Grype (dependencias) y CodeQL (código fuente).
- `scripts/`: Scripts automatizados en Python utilizados para la orquestación, extracción de SBOMs y generación de métricas.
- `evidence/reportes/`: El documento `reporte_auditoria_github.md` resultante de la auditoría dirigida a archivos de flujos de trabajo (.github/).

## 8. Conclusiones

La seguridad en la cadena de suministro de software es un desafío tridimensional. El análisis demuestra que ejecutar herramientas de escaneo como Grype y CodeQL es insuficiente si no se blindan los pipelines de integración (CI/CD) y no se estandarizan las reglas de comportamiento del equipo de ingeniería. Al aplicar el ciclo Conozco, Verifico, Evidencio, Decido y Actúo, el equipo no solo reacciona ante un reporte de vulnerabilidades, sino que construye un mecanismo escalable y fundamentado para discernir entre falsos positivos, dependencias de desarrollo y verdaderos riesgos críticos, permitiendo alocar los recursos de mitigación donde el riesgo sistémico es real.

## 9. Reconocimientos y Licencia

Este proyecto utiliza y modifica scripts originales proporcionados para esta actividad académica, cuyos derechos de autor pertenecen a fastai (2022) bajo la Licencia Apache 2.0.

**Modificaciones y aportes realizados en este repositorio:**
* Creación del entorno de ejecución interactivo (`scripts/vulnerability_analysis.ipynb`).
* Modificación de los scripts base (`add_submodales.py`, `generate_codeql.py`, `generate_grype.py`, `generate_sboms.py`) para integrar un sistema de salida y registro de logs (`*.log`).
* Actualización del archivo `/data/repos.json` con la selección de los 9 repositorios Open Source analizados.
* Generación de toda la documentación de auditoría, directorios de evidencia (`evidence/`) y resultados crudos (`results/`).