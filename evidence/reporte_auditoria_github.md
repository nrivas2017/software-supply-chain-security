# Reporte de Auditoría de Seguridad GitHub — AppSec
**Fecha:** 2026-06-04  
**Alcance:** 9 repositorios — Ghost, gitea, hoppscotch, librenms, mastodon, snipe-it, superset, wiki, zoneminder  
**Vectores auditados:** V2 (Pipelines CI/CD) · V3 (Prácticas de seguridad)

---

## Tabla Resumen Ejecutivo

| Repositorio | V2.1 Permisos | V2.2 Tags mutables | V2.3 `prt`+checkout | V2.4 Secretos en `run:` | V3.1 SECURITY.md | V3.2 Dependabot/Renovate | V3.3 CODEOWNERS |
|---|---|---|---|---|---|---|---|
| Ghost | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ renovate.json5 | ✅ |
| gitea | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ workflow cron | ❌ |
| hoppscotch | ❌ **CRÍTICO** | ❌ **CRÍTICO** | N/A | ✅ | ✅ | ✅ dependabot.yml | ❌ |
| librenms | ⚠️ | ❌ **CRÍTICO** | ✅ | ✅ | ✅ | ❌ | ❌ |
| mastodon | ✅ | ✅ | N/A | ✅ | ✅ | ✅ renovate.json5 | ❌ |
| snipe-it | ❌ **CRÍTICO** | ❌ **CRÍTICO** | N/A | ✅ | ✅ | ⚠️ parcial | ✅ |
| superset | ⚠️ | ✅ | ⚠️ condicional | ✅ | ✅ | ✅ dependabot.yml | ✅ |
| wiki | ❌ | ❌ **CRÍTICO** | N/A | ❌ **CRÍTICO** | ✅ | ❌ | ❌ |
| zoneminder | ✅ | ❌ | N/A | ✅ | ✅ | ⚠️ parcial | ❌ |

> **Leyenda:** ✅ Correcto · ⚠️ Deficiencia menor · ❌ Vulnerabilidad · N/A No aplica (trigger no usado)

---

## Detalle por Repositorio

---

### 1. Ghost

#### Vector 2 — Pipelines

**V2.1 Permisos:** ✅ `ci.yml` declara bloques `permissions:` por job con alcances mínimos. Resto de workflows también correctos.

**V2.2 Tags mutables:** ✅ Todas las Actions están ancladas a commit SHA inmutables (ej. `actions/checkout@<sha>`).

**V2.3 `pull_request_target` + checkout:** ✅ Varios workflows usan `pull_request_target` (`label-actions.yml:8`, `migration-review.yml:3`, `deploy-to-staging.yml:13`, `translation-review.yml:17`) pero **ninguno hace checkout del código del PR**. `translation-review.yml` hace checkout explícito de `ref: main`.

**V2.4 Secretos en `run:`:** ✅ Todos los secretos se inyectan vía bloques `env:` o como parámetros de Action (`with:`). No hay interpolación directa en comandos shell.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ✅ | `.github/renovate.json5` |
| CODEOWNERS | ✅ | `.github/CODEOWNERS` — cubre `/e2e/`, `**/tinybird/`, `/ghost/parse-email-address/` |

**Resultado:** Repositorio con postura de seguridad sólida. Sin hallazgos críticos.

---

### 2. gitea

#### Vector 2 — Pipelines

**V2.1 Permisos:** ⚠️ Dos workflows declaran `permissions: contents: write` de forma amplia cuando no es necesario para la tarea completa:
- `.github/workflows/cron-licenses.yml:12` — solo necesita escribir para commit de licencias
- `.github/workflows/cron-translations.yml:12` — solo necesita escribir para commit de traducciones
- `.github/workflows/cache-seeder.yml:25` — declara solo `contents: read` ✅

**V2.2 Tags mutables:** ✅ **Excelente práctica.** Todas las Actions están ancladas a SHA:
- `cron-licenses.yml:15` → `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2`
- `pull-labeler.yml:20` → `actions/labeler@f27b608878404679385c85cfa523b85ccb86e213 # v6.1.0`

**V2.3 `pull_request_target` + checkout:** ✅ `giteabot.yml:7` y `pull-labeler.yml:6` usan `pull_request_target`. `pull-labeler.yml:34` hace checkout con `ref: ${{ github.event.pull_request.base.sha }}` (base, no head del PR — seguro).

**V2.4 Secretos en `run:`:** ✅ Sin hallazgos.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ✅ | Workflow dedicado `cron-renovate.yml` en `.github/workflows/` |
| CODEOWNERS | ❌ | No existe archivo CODEOWNERS |

---

### 3. hoppscotch

#### Vector 2 — Pipelines

**V2.1 Permisos:** ❌ **CRÍTICO.** Los 4 workflows carecen completamente de bloque `permissions:`, otorgando los permisos por defecto de GitHub (excesivos para repositorios con `write` por defecto en tokens heredados).
- `.github/workflows/build-hoppscotch-agent.yml` — sin bloque permissions
- `.github/workflows/build-hoppscotch-desktop.yml` — sin bloque permissions
- `.github/workflows/release-push-docker.yml` — sin bloque permissions
- `.github/workflows/tests.yml` — sin bloque permissions

**V2.2 Tags mutables:** ❌ **CRÍTICO — Supply chain risk.** Todas las Actions usan tags mutables sin SHA. Muestra representativa:

| Archivo | Línea | Action vulnerable |
|---|---|---|
| `build-hoppscotch-agent.yml` | 59 | `actions/checkout@v3` |
| `build-hoppscotch-agent.yml` | 65 | `actions/setup-node@v3` |
| `build-hoppscotch-agent.yml` | 73 | `actions-rs/toolchain@v1` |
| `build-hoppscotch-agent.yml` | 90 | `apple-actions/import-codesign-certs@v3` |
| `build-hoppscotch-desktop.yml` | 60 | `actions/checkout@v3` |
| `build-hoppscotch-desktop.yml` | 71 | `actions-rs/toolchain@v1` |
| `release-push-docker.yml` | 22 | `actions/checkout@v4` |
| `release-push-docker.yml` | 28 | `docker/setup-qemu-action@v3` |
| `release-push-docker.yml` | 31 | `docker/setup-buildx-action@v3` |
| `release-push-docker.yml` | 34 | `docker/login-action@v2` |
| `release-push-docker.yml` | 41 | `docker/build-push-action@v4` |
| `tests.yml` | 22 | `actions/checkout@v4` |
| `tests.yml` | 28 | `actions/setup-node@v4` |

**V2.3 `pull_request_target` + checkout:** N/A — trigger no utilizado.

**V2.4 Secretos en `run:`:** ✅ Sin hallazgos.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ✅ | `.github/dependabot.yml` |
| CODEOWNERS | ❌ | No existe archivo CODEOWNERS |

---

### 4. librenms

#### Vector 2 — Pipelines

**V2.1 Permisos:** ⚠️ Dos workflows sin bloque `permissions:`:
- `.github/workflows/announcements.yml` — sin permisos declarados
- `.github/workflows/web.yml` — sin permisos declarados

**V2.2 Tags mutables:** ❌ **CRÍTICO.** Todos los workflows usan tags mutables:

| Archivo | Línea | Action vulnerable |
|---|---|---|
| `doc.yml` | 34 | `actions/checkout@v6` |
| `doc.yml` | 54 | `crazy-max/ghaction-github-status@v5` |
| `doc.yml` | 60 | `crazy-max/ghaction-github-pages@v4` |
| `label-actions.yml` | 21 | `dessant/label-actions@v5` |
| `lint.yml` | 25 | `actions/checkout@v6` |
| `lint.yml` | 36 | `docker://ghcr.io/github/super-linter:slim-v4` (imagen Docker mutable) |
| `lint.yml` | 54 | `actions/checkout@v6` |
| `lint.yml` | 68 | `actions/cache@v5` |
| `test.yml` | 65 | `actions/checkout@v6` |
| `test.yml` | 68 | `shivammathur/setup-php@v2` |
| `test.yml` | 80 | `actions/cache@v5` |
| `web.yml` | 21 | `actions/checkout@v6` |

**V2.3 `pull_request_target` + checkout:** ✅ `label-actions.yml:8` usa `pull_request_target` pero no hace checkout de código — seguro.

**V2.4 Secretos en `run:`:** ✅ Sin hallazgos.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ❌ | No existe `dependabot.yml` ni `renovate.json` |
| CODEOWNERS | ❌ | No existe archivo CODEOWNERS |

---

### 5. mastodon

#### Vector 2 — Pipelines

**V2.1 Permisos:** ✅ `build-container-image.yml:29-36` declara permisos por job con alcances adecuados (`contents: read`, `packages: write`).

**V2.2 Tags mutables:** ✅ Todas las Actions ancladas a SHA inmutables.

**V2.3 `pull_request_target` + checkout:** N/A — trigger no utilizado.

**V2.4 Secretos en `run:`:** ✅ Sin hallazgos.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ✅ | `.github/renovate.json5` |
| CODEOWNERS | ❌ | No existe archivo CODEOWNERS |

---

### 6. snipe-it

#### Vector 2 — Pipelines

**V2.1 Permisos:** ❌ **CRÍTICO.** 5 de 7 workflows no tienen bloque `permissions:`:
- `.github/workflows/crowdin-upload.yml` — sin permisos declarados
- `.github/workflows/stale.yml` — sin permisos declarados
- `.github/workflows/tests-mysql.yml` — sin permisos declarados
- `.github/workflows/tests-postgres.yml` — sin permisos declarados
- `.github/workflows/tests-sqlite.yml` — sin permisos declarados
- `ethicalcheck.yml` ✅ — sí tiene `security-events: write, actions: read`

**V2.2 Tags mutables:** ❌ **CRÍTICO.** 25+ instancias de tags mutables:

| Archivo | Línea | Action vulnerable |
|---|---|---|
| `crowdin-upload.yml` | 12 | `actions/checkout@v6` |
| `crowdin-upload.yml` | 15 | `crowdin/github-action@v2` |
| `docker-alpine.yml` | 45 | `actions/checkout@v6` |
| `docker-alpine.yml` | 49 | `docker/setup-buildx-action@v4` |
| `docker-alpine.yml` | 55 | `docker/login-action@v4` |
| `docker-alpine.yml` | 67 | `docker/metadata-action@v6` |
| `docker-alpine.yml` | 76 | `docker/build-push-action@v7` |
| `docker-ubuntu.yml` | 45 | `actions/checkout@v6` |
| `docker-ubuntu.yml` | 49 | `docker/setup-buildx-action@v4` |
| `docker-ubuntu.yml` | 55 | `docker/login-action@v4` |
| `SA-codeql.yml` | 29 | `actions/checkout@v6` |
| `SA-codeql.yml` | 33 | `github/codeql-action/init@v4` |
| `SA-codeql.yml` | 37 | `github/codeql-action/autobuild@v4` |
| `SA-codeql.yml` | 39 | `github/codeql-action/analyze@v4` |
| `stale.yml` | 14 | `actions/stale@v10` |
| `tests-mysql.yml` | 36 | `shivammathur/setup-php@v2` |
| `tests-mysql.yml` | 41 | `actions/checkout@v6` |
| `tests-mysql.yml` | 47 | `actions/cache@v5` |
| `tests-mysql.yml` | 86 | `actions/upload-artifact@v7` |
| `tests-postgres.yml` | 33 | `shivammathur/setup-php@v2` |
| `tests-postgres.yml` | 38 | `actions/checkout@v6` |
| `tests-sqlite.yml` | 23 | `shivammathur/setup-php@v2` |
| `tests-sqlite.yml` | 28 | `actions/checkout@v6` |
| `ethicalcheck.yml` | 66 | `github/codeql-action/upload-sarif@v4` |

**V2.3 `pull_request_target` + checkout:** N/A — trigger no utilizado.

**V2.4 Secretos en `run:`:** ✅ Secretos pasados correctamente vía `with:` o `env:`.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ⚠️ | `.github/dependabot.yml` — solo cubre ecosistema `github-actions` |
| CODEOWNERS | ✅ | `.github/CODEOWNERS` — `@snipe` como owner por defecto |

---

### 7. superset

#### Vector 2 — Pipelines

**V2.1 Permisos:** ⚠️ Un workflow con `pull_request_target` sin permisos de job declarados:
- `.github/workflows/welcome-new-users.yml:6` — usa `pull_request_target`, sin `permissions:` a nivel de job (mayor riesgo dado el trigger privilegiado)
- Resto de workflows: ✅ Permisos correctamente declarados

**V2.2 Tags mutables:** ✅ **Excelente práctica.** Casi todos los workflows usan SHA. Ejemplos:
- `bump-python-package.yml:35` → `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6`
- `codeql-analysis.yml:66` → `github/codeql-action/init@7211b7c8077ea37d8641b6271f6a365a22a5fbfa # v4`

**V2.3 `pull_request_target` + checkout:** ⚠️ **Riesgo condicional.**
- `.github/workflows/showtime-trigger.yml:6` — usa `pull_request_target`
- `.github/workflows/showtime-trigger.yml:154-158` — realiza checkout del código del PR **solo si** el `github.actor` es mantenedor autorizado (comprobación en líneas 39-102). El riesgo se reduce, pero el patrón sigue siendo sensible: si la lógica de autorización falla, un PR externo podría ejecutar código privilegiado.
- `labeler.yml:3` y `welcome-new-users.yml:6` — usan `pull_request_target` **sin** checkout → seguros.

**V2.4 Secretos en `run:`:** ✅ Todos los secretos inyectados vía `env:` o parámetros `with:`.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ✅ | `.github/dependabot.yml` — cubre múltiples ecosistemas (github-actions, npm, pip) |
| CODEOWNERS | ✅ | `.github/CODEOWNERS` — cubre migraciones DB, componentes, Helm, GitHub Actions |

---

### 8. wiki (Wiki.js)

#### Vector 2 — Pipelines

**V2.1 Permisos:** ❌ Dos workflows sin bloque `permissions:`:
- `.github/workflows/helm.yml` — sin permisos declarados
- `.github/workflows/packer.yml` — sin permisos declarados
- `.github/workflows/build.yml:18-19` — solo declara `packages: write` sin `contents: read` explícito

**V2.2 Tags mutables:** ❌ **CRÍTICO.** 22+ instancias en `build.yml` solo:

| Archivo | Línea | Action vulnerable |
|---|---|---|
| `build.yml` | 22 | `actions/checkout@v6` |
| `build.yml` | 45 | `docker/login-action@v4` |
| `build.yml` | 58 | `docker/build-push-action@v7` |
| `build.yml` | 97 | `actions/checkout@v6` |
| `build.yml` | 126 | `actions/checkout@v6` |
| `build.yml` | 139 | `docker/setup-qemu-action@v4` |
| `build.yml` | 142 | `docker/setup-buildx-action@v4` |
| `build.yml` | 169 | `docker/build-push-action@v7` |
| `build.yml` | 189 | `actions/setup-node@v6` |
| `build.yml` | 194 | `actions/download-artifact@v8` |
| `build.yml` | 220 | `actions/upload-artifact@v7` |
| `build.yml` | 340 | `Requarks/changelog-action@v1` |
| `build.yml` | 347 | `ncipollo/release-action@v1.21.0` |
| `build.yml` | 369 | `appleboy/telegram-action@v1.0.1` |
| `build.yml` | 380 | `sebastianpopp/discord-action@v2.0` |
| `helm.yml` | 19 | `actions/checkout@v6` |
| `packer.yml` | 17 | `actions/checkout@v6` |

**V2.3 `pull_request_target` + checkout:** N/A — trigger no utilizado.

**V2.4 Secretos en `run:`:** ❌ **CRÍTICO — Secreto expuesto en comando shell.**
- `.github/workflows/helm.yml:26` — El secreto se interpola directamente en el argumento de un comando shell:
  ```yaml
  --password="${{secrets.HELM_REPO_PASSWORD}}"
  ```
  Esto hace que el valor del secreto quede visible en los logs de ejecución y en la lista de procesos del sistema operativo del runner. El secreto debe inyectarse vía bloque `env:` y referenciarse como variable de entorno.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ❌ | No existe `dependabot.yml` ni `renovate.json` |
| CODEOWNERS | ❌ | No existe archivo CODEOWNERS |

---

### 9. zoneminder

#### Vector 2 — Pipelines

**V2.1 Permisos:** ✅ Todos los workflows declaran bloques `permissions:` explícitos:
- `build-deb-packages.yml:6-16` → `contents: write`
- `ci-eslint.yml:10-11` → `contents: read`
- `cleanup-caches.yml:13-15` → `actions: write, contents: read`
- `codeql-analysis.yml:39-47` → permisos por job
- `depsreview.yaml:4-5` → `contents: read`

**V2.2 Tags mutables:** ❌ Múltiples instancias de tags mutables:

| Archivo | Línea | Action vulnerable |
|---|---|---|
| `build-deb-packages.yml` | 51 | `actions/checkout@v6` |
| `ci-eslint.yml` | 18 | `actions/checkout@v6` |
| `codeql-analysis.yml` | 62 | `actions/checkout@v6` |
| `codeql-analysis.yml` | 70 | `github/codeql-action/init@v4` |
| `codeql-analysis.yml` | 93 | `github/codeql-action/autobuild@v4` |
| `codeql-analysis.yml` | 108 | `github/codeql-action/analyze@v4` |
| `depsreview.yaml` | 12 | `actions/checkout@v6` |
| `depsreview.yaml` | 14 | `actions/dependency-review-action@v5` |

**V2.3 `pull_request_target` + checkout:** N/A — trigger no utilizado.

**V2.4 Secretos en `run:`:** ✅ Secretos GPG pasados correctamente vía bloque `env:`.

#### Vector 3 — Prácticas

| Check | Estado | Evidencia |
|---|---|---|
| SECURITY.md | ✅ | `SECURITY.md` en raíz |
| Dependabot/Renovate | ⚠️ | `.github/dependabot.yml` — solo cubre ecosistema `github-actions` |
| CODEOWNERS | ❌ | No existe archivo CODEOWNERS |

---

## Clasificación de Hallazgos por Severidad

### 🔴 Crítico — Riesgo inmediato

| # | Repositorio | Vector | Hallazgo | Evidencia |
|---|---|---|---|---|
| C-1 | wiki | V2.4 | Secreto `HELM_REPO_PASSWORD` interpolado directamente en comando shell — visible en logs | `.github/workflows/helm.yml:26` |
| C-2 | hoppscotch | V2.1 | Ausencia total de bloque `permissions:` en los 4 workflows — permisos excesivos por defecto | Todos los archivos en `.github/workflows/` |
| C-3 | hoppscotch | V2.2 | 13+ Actions de terceros con tags mutables — riesgo de supply chain attack | `build-hoppscotch-agent.yml:59,65,73,90`, `release-push-docker.yml:28,31,34,41`, etc. |
| C-4 | snipe-it | V2.1 | Ausencia de `permissions:` en 5 de 7 workflows | `crowdin-upload.yml`, `stale.yml`, `tests-mysql.yml`, `tests-postgres.yml`, `tests-sqlite.yml` |
| C-5 | snipe-it | V2.2 | 24+ Actions de terceros con tags mutables | `docker-alpine.yml:45,49,55,67,76`, `SA-codeql.yml:29,33,37,39`, etc. |
| C-6 | librenms | V2.2 | 12+ Actions de terceros con tags mutables en todos los workflows | `doc.yml:34,54,60`, `lint.yml:25,36,54,68`, `test.yml:65,68,80`, etc. |
| C-7 | wiki | V2.2 | 17+ Actions de terceros con tags mutables incluyendo Actions no-oficiales (`appleboy`, `sebastianpopp`, `Requarks`) | `build.yml:22,45,58,340,347,369,380`, etc. |

### 🟠 Alto — Corregir en próximo sprint

| # | Repositorio | Vector | Hallazgo | Evidencia |
|---|---|---|---|---|
| A-1 | superset | V2.3 | `showtime-trigger.yml` usa `pull_request_target` y realiza checkout del código del PR — la validación de autorización reduce el riesgo pero el patrón es intrínsecamente peligroso | `.github/workflows/showtime-trigger.yml:6,154-158` |
| A-2 | superset | V2.1 | `welcome-new-users.yml` usa `pull_request_target` sin `permissions:` de job | `.github/workflows/welcome-new-users.yml:6` |
| A-3 | librenms | V2.1 | `announcements.yml` y `web.yml` sin bloque `permissions:` | `.github/workflows/announcements.yml`, `.github/workflows/web.yml` |
| A-4 | zoneminder | V2.2 | 8 Actions de terceros con tags mutables | `codeql-analysis.yml:62,70,93,108`, `depsreview.yaml:12,14`, etc. |
| A-5 | librenms | V3.2 | Sin Dependabot ni Renovate — dependencias sin actualización automática | Ausente en `.github/` |
| A-6 | wiki | V2.1 | `helm.yml` y `packer.yml` sin bloque `permissions:` | `.github/workflows/helm.yml`, `.github/workflows/packer.yml` |
| A-7 | wiki | V3.2 | Sin Dependabot ni Renovate | Ausente en `.github/` |

### 🟡 Medio — Deuda técnica de seguridad

| # | Repositorio | Vector | Hallazgo |
|---|---|---|---|
| M-1 | gitea | V2.1 | `cron-licenses.yml:12` y `cron-translations.yml:12` con `contents: write` más amplio de lo necesario |
| M-2 | snipe-it | V3.2 | `dependabot.yml` cubre solo ecosistema `github-actions` — npm/composer sin actualización automática |
| M-3 | zoneminder | V3.2 | `dependabot.yml` cubre solo ecosistema `github-actions` |
| M-4 | gitea, hoppscotch, librenms, mastodon, wiki, zoneminder | V3.3 | Sin archivo CODEOWNERS — sin revisión obligatoria por pares en áreas críticas |

---

## Recomendaciones de Remediación

### Para V2.2 — Reemplazo de tags mutables por SHA
Ejecutar por cada workflow:
```bash
# Ejemplo: reemplazar actions/checkout@v6 por SHA
# 1. Obtener el SHA del tag actual:
#    gh api repos/actions/checkout/git/ref/tags/v6 --jq '.object.sha'
# 2. Reemplazar en el YAML:
#    uses: actions/checkout@<SHA-completo> # v6
```
Herramientas recomendadas: [**pin-github-action**](https://github.com/mheap/pin-github-action) o Dependabot con `github-actions` ecosystem.

### Para V2.1 — Agregar bloque `permissions:`
Añadir al inicio de cada workflow como mínimo:
```yaml
permissions:
  contents: read
```
Y otorgar solo los permisos adicionales que cada job requiera explícitamente.

### Para C-1 (wiki `helm.yml:26`) — Secreto en shell
```yaml
# VULNERABLE (actual):
- run: helm registry login ... --password="${{secrets.HELM_REPO_PASSWORD}}"

# CORRECTO:
- run: helm registry login ... --password="$HELM_REPO_PASSWORD"
  env:
    HELM_REPO_PASSWORD: ${{ secrets.HELM_REPO_PASSWORD }}
```

### Para A-1 (superset `showtime-trigger.yml`) — pull_request_target + checkout
Revisar si el checkout del código PR es estrictamente necesario. Si lo es, agregar `permissions: contents: read` mínimo y considerar usar `workflow_run` como trigger alternativo que aísla mejor los contextos de confianza.
