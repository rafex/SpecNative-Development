# MCP.md — SpecNative MCP Server v0.9

El servidor MCP de SpecNative expone el repositorio como **recursos**, **herramientas**
y **prompts** para que cualquier agente compatible con MCP pueda trabajar en modo
spec-first sin navegar manualmente el árbol de archivos.

**v0.9 define una superficie de comandos común para Claude Code, OpenCode y
Codex**, con operaciones canónicas para decisiones, arquitectura y
convenciones.

## Comandos por agente

Instalados automáticamente en tu repositorio. Disponibles desde el primer día.

### Comandos comunes

| Comando | Descripción |
|---------|-------------|
| `spec` | Enruta una solicitud por el flujo mínimo correcto |
| `spec-init`, `spec-update`, `spec-status` | Inicialización, refinamiento y salud del contexto |
| `spec-backlog [solicitud]` | Tablero derivado o captura canónica de trabajo |
| `spec-decision` | Registra una decisión persistente después de revisión |
| `spec-plan`, `spec-implement` | Planifica e implementa una tarea con evidencia de cierre |
| `spec-review`, `spec-close` | Revisa criterios y cierra con trazabilidad |
| `spec-context` | Carga el mínimo contexto por tag o ID `DEC`/`ARCH`/`CONV` |
| `spec-architecture`, `spec-convention` | Crea artefactos canónicos e índices derivados |
| `spec-handoff` | Guarda un traspaso para el siguiente agente |

`spec-backlog-add` se mantiene como alias compatible de `spec-backlog`.

La fuente de verdad es `.specnative/commands.json`. En el repositorio del
framework, `tools/sync_agent_commands.py --check` verifica que los adaptadores
generados no hayan quedado desactualizados.

### Claude Code — slash commands

Usa `/spec-*`; cada entrada de `.specnative/commands.json` genera un archivo
en `.claude/commands/`.

La skill `specnative-workflow` se instala en `.claude/skills/` y es detectada
por Claude Code y OpenCode. También se incluye en `.codex/skills/` para los
entornos Codex que cargan skills de proyecto. El MCP se instala globalmente;
`codex.toml` conserva los prompts versionados del proyecto.

### OpenCode — comandos integrados

Disponibles mediante el MCP global y los prompts del proyecto.

### Codex CLI — prompts en codex.toml

```bash
codex --prompt spec-decision
codex --prompt spec-plan
codex --prompt spec-implement
codex --prompt spec-review
```

Todos los comandos comunes se instalan como prompts `spec-*`; si ya existe un
`codex.toml`, el instalador agrega solo los prompts faltantes. La conexión MCP
vive en la configuración global del usuario, no en `.codex/config.toml`.

### CLI sin agente

```bash
python3 specnative.py init              # wizard interactivo en terminal
python3 specnative.py update            # health check + refinamiento guiado
python3 specnative.py update --doc stack  # actualizar solo un documento
```

## Instalación global

Ejecuta una vez por usuario y máquina:

```bash
python3 install.py --global
```

El runtime se instala fuera de los repositorios y registra la conexión global
para Codex, OpenCode y Claude. El servidor descubre el repositorio activo desde
el workspace buscando `AGENTS.md` y `spec-native/`; usa `SPECNATIVE_REPO` o
`select_repository(path)` solo como alternativa.

Para retirar artefactos locales de instalaciones previas:

```bash
python3 install.py --global --migrate-local --target /ruta/a/tu/repo
```

Para diagnosticar el runtime y los registros de los clientes:

```bash
python3 install.py --doctor
```

### Qué instala

Un único runtime por usuario, sin `sudo` y fuera de los repositorios:

| Plataforma | Ubicación |
|------------|-----------|
| macOS | `~/Library/Application Support/SpecNative/` |
| Linux | `$XDG_DATA_HOME/specnative/` (por defecto `~/.local/share/specnative/`) |
| Windows | `%LOCALAPPDATA%\SpecNative\` |

```
specnative_mcp.py   ← servidor MCP
.venv/              ← entorno virtual con la dependencia mcp
```

Y lo registra en la configuración de usuario de cada cliente:

| Cliente | Configuración |
|---------|---------------|
| Claude Code | `claude mcp add --scope user specnative` (reinstalar es idempotente) |
| Claude Desktop | `claude_desktop_config.json` (solo si Claude Desktop está instalado) |
| OpenCode | `~/.config/opencode/opencode.json`, clave `mcp.specnative` |
| Codex CLI | `~/.codex/config.toml`, tabla `[mcp_servers.specnative]` |

Para actualizar el runtime, vuelve a ejecutar `python3 install.py --global`.
`--reinstall` está obsoleto y equivale a `--global`.

### Diagnóstico

`python3 install.py --doctor` verifica el servidor, el Python del venv, la
dependencia `mcp`, que el servidor arranque y que cada cliente apunte al
runtime. Imprime un JSON con `ok`, `fail` o `skip` por verificación y termina
con código 1 si algo falla.

### Selección del repositorio

Como el servidor es compartido, descubre el repositorio activo desde el
directorio de trabajo del cliente (el primer ancestro con `AGENTS.md` y
`spec-native/`). Si el cliente no arranca dentro del repositorio (por ejemplo,
Claude Desktop), usa `select_repository(path)` o `SPECNATIVE_REPO`.

---

## Configuración manual (opcional)

Solo si no usas el instalador. Sustituye `<RUNTIME>` por la ubicación de la
tabla anterior.

```bash
claude mcp add --scope user specnative -- "<RUNTIME>/.venv/bin/python3" "<RUNTIME>/specnative_mcp.py"
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.specnative]
command = "<RUNTIME>/.venv/bin/python3"
args = ["<RUNTIME>/specnative_mcp.py"]
enabled = true
startup_timeout_sec = 30
```

OpenCode (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "specnative": {
      "type": "local",
      "enabled": true,
      "command": ["<RUNTIME>/.venv/bin/python3", "<RUNTIME>/specnative_mcp.py"]
    }
  }
}
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "specnative": {
      "command": "<RUNTIME>/.venv/bin/python3",
      "args": ["<RUNTIME>/specnative_mcp.py"]
    }
  }
}
```

En OpenCode, la clave `instructions` de un `opencode.json` de proyecto hace que
`AGENTS.md` se cargue en cada sesión; los comandos `spec-*` se generan desde
`.specnative/commands.json`.

### Variable de entorno

```bash
export SPECNATIVE_REPO=/ruta/a/tu/proyecto
```

### Transporte SSE (agentes remotos)

```bash
<RUNTIME>/.venv/bin/python3 <RUNTIME>/specnative_mcp.py \
  --repo /ruta/al/proyecto \
  --transport sse \
  --port 8765
```

---

## Recursos disponibles

| URI                          | Documento                              |
|------------------------------|----------------------------------------|
| `spec://agents`              | `AGENTS.md` — contrato operativo       |
| `spec://session`             | `spec-native/SESSION.md` — estado activo |
| `spec://context/product`     | `spec-native/PRODUCT.md`               |
| `spec://context/architecture`| `spec-native/ARCHITECTURE.md`          |
| `spec://context/stack`       | `spec-native/STACK.md`                 |
| `spec://context/conventions` | `spec-native/CONVENTIONS.md`           |
| `spec://context/commands`    | `spec-native/COMMANDS.md`              |
| `spec://context/decisions`   | `spec-native/DECISIONS.md`             |
| `spec://context/roadmap`     | `spec-native/ROADMAP.md`               |
| `spec://context/traceability`| `spec-native/TRACEABILITY.md`          |
| `spec://pipelines/ci`        | `spec-native/pipelines/CI.md`          |
| `spec://pipelines/cd`        | `spec-native/pipelines/CD.md`          |
| `spec://schema`              | `.specnative/SCHEMA.md`                |

---

## Herramientas disponibles

### Consulta

| Herramienta                  | Descripción                                                    |
|------------------------------|----------------------------------------------------------------|
| `status()`                   | Estado de cada spec y conteo de tareas por estado              |
| `validate()`                 | Verifica que existan todos los archivos obligatorios           |
| `list_specs()`               | Lista specs con ID, estado y owner                             |
| `list_tasks(initiative)`     | Lista tareas de una iniciativa con estados                     |
| `board(format?)`             | Tablero de entrega de solo lectura derivado de tareas           |
| `capture_backlog_item(...)`  | Crea tarea válida o idea triada según la información disponible |
| `read_spec(initiative)`      | Lee el contenido de una spec                                   |
| `read_context(document)`     | Lee un documento de contexto por nombre corto                  |
| `export_index()`             | Exporta specs y task files con metadata TOML como JSON         |
| `context_snapshot(initiative?)` | Dump completo de contexto para onboarding de nuevo agente  |

### Continuidad multi-agente (v0.5)

| Herramienta                               | Descripción                                                    |
|-------------------------------------------|----------------------------------------------------------------|
| `resume()`                                | Lee SESSION.md y genera resumen de continuidad                 |
| `checkpoint(initiative, task_id, intent, next_steps, context_notes?, agent_name?)` | Guarda estado antes de pausar |
| `update_task(initiative, task_id, state, notes?, completion_evidence?)` | Actualiza estado; cerrar exige evidencia |
| `log_decision(title, context, decision, consequences)` | Append rápido a DECISIONS.md              |
| `log_architecture(title, context, design, consequences)` | Crea `ARCH-*` y actualiza ARCHITECTURE.md |
| `log_convention(title, rationale, rule, consequences)` | Crea `CONV-*` y actualiza CONVENTIONS.md |

### Definición y salud del proyecto (v0.6)

| Herramienta                               | Descripción                                                    |
|-------------------------------------------|----------------------------------------------------------------|
| `health_check()`                          | Escanea spec-native/ y reporta vacíos, docs faltantes, sesión obsoleta |
| `suggest_next()`                          | Sugiere las 3 acciones más impactantes basado en estado actual |
| `refine_document(document, what_changed, new_content)` | Actualiza un documento con nuevo contenido     |
| `read_template(document)`                 | Retorna la estructura vacía esperada de cualquier doc (11 tipos) |
| `update_section(document, section, content)` | Actualiza una sola sección sin tocar el resto del archivo  |

### Archetypes (v0.7)

| Herramienta                               | Descripción                                                    |
|-------------------------------------------|----------------------------------------------------------------|
| `list_archetypes()`                       | Lista archetypes disponibles: built-in + locales en `.specnative/archetypes/` |
| `read_archetype(name)`                    | Previsualiza todos los documentos de un archetype antes de aplicarlo |
| `apply_archetype(name, force?)`           | Escribe docs del archetype en spec-native/ (respeta docs con contenido) |

**Built-in:** `java-hexagonal` — Java 21 + Spring Boot 3 + Hexagonal Architecture
Incluye: ARCHITECTURE, STACK, CONVENTIONS, COMMANDS, DECISIONS, ROADMAP

**Archetype propio:** crea `.specnative/archetypes/<nombre>/archetype.toml` + docs.
Ver `.specnative/archetypes/README.md` para el formato.

### Templates (v0.7)

| Herramienta                               | Descripción                                                    |
|-------------------------------------------|----------------------------------------------------------------|
| `list_templates(type?)`                   | Lista spec templates y decision snippets (`spec` \| `decision` \| vacío=ambos) |
| `apply_spec_template(template, initiative)` | Crea `spec-native/specs/{initiative}/SPEC.md` desde un template |
| `apply_decision_snippet(name)`            | Appenda snippet a DECISIONS.md con auto DEC-XXXX y fecha      |

**Spec templates built-in:** `feature-rest-endpoint`, `db-migration`, `module-refactor`

**Decision snippets built-in:** `jwt-authentication`, `hexagonal-ports`, `database-choice`

**Templates propios:** crea archivos `.md` en `.specnative/templates/specs/` o
`.specnative/templates/decisions/`. Ver los `README.md` de cada carpeta para el formato.

---

## Prompts disponibles

### Definición del proyecto (v0.6)

| Prompt                                    | Descripción                                              |
|-------------------------------------------|----------------------------------------------------------|
| `init_project_guided(name, problem, users, goals, non_goals, stack, arch, conv, cmds)` | Llena los documentos core con contenido real del proyecto |

### Flujo de iniciativas

| Prompt                                    | Descripción                                              |
|-------------------------------------------|----------------------------------------------------------|
| `start_initiative(name, problem)`         | Inicia una nueva iniciativa spec-driven                  |
| `plan_tasks(initiative)`                  | Deriva el plan de tareas desde una spec                  |
| `implement_task(initiative, task_id)`     | Implementa una tarea específica                          |
| `review_against_spec(initiative)`         | Revisa implementación contra criterios de aceptación     |
| `handoff(summary, next_steps, decisions?)` | Genera traspaso estructurado para el siguiente agente   |
| `record_decision(title, ctx, dec, cons)`  | Registra una decisión persistente en DECISIONS.md        |
| `record_architecture(title, ctx, design, cons)` | Prepara un artefacto ARCH para revisión |
| `record_convention(title, rationale, rule, cons)` | Prepara una convención para revisión |
| `close_initiative(initiative)`            | Cierra la iniciativa y actualiza trazabilidad            |
| `capture_backlog(title, description, initiative?, priority?)` | Clasifica y registra una solicitud de backlog |

---

## Flujo multi-agente

```
Agente A (Claude Code) implementa TASK-AUTH-0002:
  → update_task('authentication', 'TASK-AUTH-0002', 'in_progress')
  → ... trabaja ...
  → Se acaban los tokens. Llama checkpoint antes de cerrar:
  → checkpoint(
       initiative='authentication',
       task_id='TASK-AUTH-0002',
       intent='Implementando middleware JWT',
       next_steps='1. Agregar endpoint /refresh\n2. Escribir tests de integración',
       context_notes='JWT secret en env AUTH_SECRET. No hardcodear.'
     )

Agente B (Codex) entra al repo:
  → Lee AGENTS.md
  → resume()
  ← "Task TASK-AUTH-0002 in_progress. Intent: Implementando middleware JWT.
     Next: 1. Agregar endpoint /refresh..."
  → Continúa sin fricción
```

---

## Separación de responsabilidades

El servidor MCP es **infraestructura del framework**, no contenido del proyecto:

- Los documentos del proyecto viven en `spec-native/`.
- El servidor MCP lee y escribe esos documentos mediante herramientas tipadas.
- Las reglas de ownership siguen siendo las de `AGENTS.md` y `SCHEMA.md`.
- El runtime vive en el directorio de datos del usuario, no en el repositorio:
  no hay nada que versionar ni agregar a `.gitignore`. Si quedan restos de
  instalaciones antiguas, `python3 install.py --global --migrate-local --target <repo>`
  los retira.
