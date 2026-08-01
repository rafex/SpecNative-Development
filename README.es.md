![SpecNative Development Logo](./docs/assets/specnative-logo.svg)

# SpecNative Development

Desarrollo estructurado por repositorio y orientado por especificaciones para agentes de IA y humanos.

**[Sitio web](https://specnative-d.rafex.io) · [Guía para Agentes IA](https://specnative-d.rafex.io/ai/es/) · [Plantilla](./Template-Project-Agents-AI) · [Releases](https://github.com/rafex/SpecNative-Development/releases)**

---

## Qué es SpecNative Development

SpecNative es un modelo de desarrollo donde las especificaciones, reglas de arquitectura, convenciones y decisiones viven en archivos estables del repositorio para que los agentes puedan planificar e implementar con menos ambigüedad en tiempo de ejecución.

**El repositorio es el sistema de contexto. Los prompts son disparadores, no manuales del proyecto.**

```
prompt → seleccionar spec  (no: explicar el proyecto desde cero)
```

En lugar de reconstruir el contexto en cada sesión, el repositorio lo codifica una vez y el agente lo navega de forma determinista.

## Usar SpecNative

Existe un punto de entrada corto para cualquier solicitud:

```text
/spec <solicitud>               # Claude Code
spec <solicitud>                # Prompt de OpenCode y Codex
specnative(request)             # Prompt MCP
```

El flujo lee el contrato del repositorio, revisa trabajo activo y enruta a la
acción mínima correcta: iniciativa, backlog, implementación, decisión, revisión,
handoff o cierre. Las skills instaladas habilitan el flujo en Claude Code y
OpenCode; Codex recibe prompts equivalentes.

Para trabajo enfocado usa `/spec-backlog-add <solicitud>`. Para cargar solo el
contexto relacionado usa `list_architecture(tag)`, `list_conventions(tag)`,
`list_decisions(tag)` y `read_context_artifact(id)` mediante MCP.

---

## Inicio Rápido

### Instalar en un repositorio existente

```bash
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/install.py \
  | python3 - --target /ruta/a/tu/repo --profile context
```

O descarga una vez y ejecuta localmente:

```bash
python3 install.py --target /ruta/a/tu/repo --profile platform --include-examples
```

### Conectar via MCP (Claude Code, Claude Desktop, OpenCode, Codex)

```bash
pip install mcp

# Claude Code
claude mcp add specnative \
  python3 .specnative/specnative_mcp.py \
  -- --repo /ruta/a/tu/proyecto
```

Consulta [`.specnative/MCP.md`](./Template-Project-Agents-AI/.specnative/MCP.md) para la configuración completa por agente.

---

## Layout del repositorio

```
Template-Project-Agents-AI/
├── AGENTS.md              # Contrato operativo para agentes — leer primero
├── README.md              # Índice de navegación
├── spec-native/
│   ├── PRODUCT.md         # Problema, usuarios y objetivos
│   ├── ARCHITECTURE.md    # Estructura del sistema y límites
│   ├── STACK.md           # Stack tecnológico y restricciones
│   ├── CONVENTIONS.md     # Reglas de código, naming y testing
│   ├── COMMANDS.md        # Comandos reales del proyecto
│   ├── SESSION.md         # Estado activo entre agentes
│   ├── specs/<iniciativa>/SPEC.md
│   ├── tasks/<iniciativa>/TASKS.md
│   ├── backlog/           # Vistas derivadas de entrega; no editar estado aquí
│   ├── workflows/         # PLANNING, IMPLEMENTATION, REVIEW
│   └── pipelines/         # CI.md, CD.md
└── .specnative/           # Infraestructura del framework
    ├── SCHEMA.md          # Contrato del framework
    ├── CLI.md             # Referencia de la CLI
    └── MCP.md             # Configuración del servidor MCP
```

### Ownership documental — una verdad por documento

| Documento | Contiene |
|---|---|
| `PRODUCT.md` | Problema, usuarios, objetivos, no-objetivos |
| `SPEC.md` | Qué debe construirse en esta iniciativa (temporal) |
| `DECISIONS.md` | Tradeoffs persistentes que las próximas iniciativas deben respetar |
| `ROADMAP.md` | Dirección temporal sin detalle de implementación |
| `ARCHITECTURE.md` | Estructura del sistema, módulos, límites |
| `CONVENTIONS.md` | Naming, estilo, testing, convenciones de commits |
| `COMMANDS.md` | Solo comandos del proyecto — nunca comandos del CLI del framework |
| `spec-native/tasks/**/TASKS.md` | Plan ejecutable con estado, owner, criterio de cierre |
| `TRACEABILITY.md` | Vínculos entre artefactos (actualizar al cerrar iniciativa) |
| `spec-native/pipelines/CI.md` | Definición de gates automatizados |
| `spec-native/pipelines/CD.md` | Proceso de entrega y ambientes |

---

## Tooling del framework

### CLI — `tools/specnative.py`

```bash
python3 tools/specnative.py status --target /ruta/al/proyecto              # Estado de specs y tareas
python3 tools/specnative.py validate --target /ruta/al/proyecto            # Verificar archivos y TOML
python3 tools/specnative.py export-index --target /ruta/al/proyecto        # Exportar specs/tareas como JSON
python3 tools/specnative.py export-traceability --target /ruta/al/proyecto # Exportar matriz de trazabilidad
python3 tools/specnative.py board --target /ruta/al/proyecto               # Tablero de entrega derivado
python3 tools/specnative.py board --target /ruta/al/proyecto --format mermaid
python3 tools/specnative.py github-project plan --target /ruta/al/proyecto # Plan de exportación sin efectos
```

### Gestión del trabajo

`TASKS.md` sigue siendo el único registro editable de ejecución. `board`
calcula `ready`, `in_progress`, `blocked`, `waiting` y `done` usando estado y
dependencias; no crea un segundo backlog. Una tarea solo llega a `done` cuando
registra evidencia de cierre además de la validación planificada.

GitHub Projects es opcional y comienza con un plan de exportación determinista.
Copia `.specnative/integrations/github-project.toml.example`, configura el ID
ProjectV2 y los nombres de estado, y revisa el JSON de `github-project plan`.
No realiza solicitudes de red ni hace a GitHub autoritativo.

### Servidor MCP — `tools/specnative_mcp.py` (v0.7) <!-- MCP_VERSION -->

Expone el repositorio como recursos, herramientas y prompts MCP para que
cualquier agente compatible trabaje en modo spec-first sin navegar
manualmente el árbol de archivos.

**Recursos** — documentos de contexto por URI:

```
spec://agents                  → AGENTS.md
spec://context/product         → spec-native/PRODUCT.md
spec://context/architecture    → spec-native/ARCHITECTURE.md
spec://context/decisions       → spec-native/DECISIONS.md
spec://context/roadmap         → spec-native/ROADMAP.md
spec://pipelines/ci            → spec-native/pipelines/CI.md
spec://schema                  → .specnative/SCHEMA.md
# … y más (ver MCP.md)
```

**Herramientas**: `status`, `validate`, `list_specs`, `list_tasks`, `board`, `capture_backlog_item`, `read_spec`, `read_context`, `export_index`

También: `list_decisions(tag?)`, `list_architecture(tag?)`,
`list_conventions(tag?)` y `read_context_artifact(id)`.

Para una solicitud como “agrega esta tarea al backlog”, usa el comando nativo
`spec-backlog-add`. El agente crea una tarea solo si existe una spec y tiene
criterio de cierre y validación; en otro caso captura una idea triada en
`spec-native/intake/IDEAS.md`.

**Prompts**: `start_initiative`, `plan_tasks`, `implement_task`, `review_against_spec`, `record_decision`, `close_initiative`

#### Configuración por agente

**Claude Code**
```bash
claude mcp add specnative \
  python3 .specnative/specnative_mcp.py \
  -- --repo /ruta/a/tu/proyecto
```

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "specnative": {
      "command": "python3",
      "args": ["/ruta/a/specnative_mcp.py", "--repo", "/ruta/a/tu/proyecto"]
    }
  }
}
```

**OpenCode** — `.opencode/config.json`:
```json
{
  "mcp": {
    "servers": {
      "specnative": {
        "command": "python3",
        "args": ["/ruta/a/specnative_mcp.py", "--repo", "/ruta/a/tu/proyecto"]
      }
    }
  }
}
```

**Codex CLI** — `~/.codex/config.toml` o `codex.toml`:
```toml
[mcp_servers.specnative]
command = "python3"
args = ["/ruta/a/specnative_mcp.py", "--repo", "/ruta/a/tu/proyecto"]
type = "stdio"
```

---

## Principios del framework

- **Specification-first.** El comportamiento se define antes de la implementación. Las specs son contexto ejecutable, no documentación tardía.
- **Repositorio como sistema de contexto.** El conocimiento duradero del proyecto vive en archivos, no en el historial de conversación.
- **Una verdad por documento.** Cada hecho existe en un documento autoritativo. Nunca duplicado en prompts, tickets o notas locales.
- **Navegación determinista.** Los agentes leen `AGENTS.md` primero, navegan por `README.md` y cargan el mínimo contexto para la tarea.
- **TOML opcional.** Los documentos son válidos sin bloques TOML. Agrégalos cuando quieras que `validate`/`status`/`export` funcionen automáticamente.
- **Sin dependencia de runtime.** No se requiere un runtime de agentes específico ni orquestación propietaria.

---

## Cómo trabajan los agentes con un repositorio SpecNative

1. Leer `AGENTS.md` — contrato operativo del agente.
2. Revisar `spec-native/ROADMAP.md` — confirmar que la iniciativa es coherente con la dirección.
3. Leer `spec-native/PRODUCT.md` y contexto técnico relevante.
4. Leer `spec-native/DECISIONS.md` — respetar tradeoffs persistentes.
5. Revisar o crear un `SPEC.md`.
6. Derivar tareas en `tasks/`.
7. Implementar siguiendo `workflows/IMPLEMENTATION.md`.
8. Registrar decisiones persistentes en `DECISIONS.md`.
9. Actualizar `TRACEABILITY.md` al cerrar la iniciativa.

**Con el servidor MCP**, los agentes acceden a todo esto mediante recursos tipados y prompts estructurados en lugar de navegar manualmente los archivos.

---

## Cuándo usar esto

Más útil cuando:
- El desarrollo asistido por IA es parte regular del flujo de trabajo.
- Repetir el contexto entre sesiones tiene un costo alto.
- Múltiples agentes o colaboradores necesitan trabajar desde los mismos supuestos arquitectónicos.
- Los flujos deterministas y auditables son importantes.

Menos útil para prototipos muy pequeños y de corta duración donde mantener el contexto estructurado supera el valor del reuso.

---

## Versiones

| Versión | Destacado |
|---|---|
| v0.1 | Concepto inicial — documentos de contexto en `agents/` |
| v0.2 | Specs y archivos de tareas estructurados |
| v0.3 | Contrato del framework (`.specnative/`), `pipelines/`, `install.py`, TOML opcional, comando `status` |
| v0.4 | Servidor MCP — recursos, herramientas y prompts para Claude Code, Claude Desktop, OpenCode, Codex |
| v0.5.0 | `agents/` → `spec-native/` · carpetas consolidadas · `SESSION.md` · continuidad multi-agente |
| v0.6.0 | Comandos nativos por agente · `codex.toml` · prompts en `opencode.json` · CLI `init/update` |
| **v0.6.1** | **`read_template()` · `update_section()` — actualizaciones incrementales, compatible con Copilot** |
| v0.6.2 | Fix `opencode.json` — clave `command` correcta, `instructions` carga AGENTS.md automáticamente |
| **v0.7.0** | **Archetypes (`java-hexagonal` built-in) · Spec templates · Decision snippets · `.specnative/archetypes/` + `.specnative/templates/`** |
| **v0.8.0** | **Flujo corto `/spec` · Skills · Backlog Markdown · Índices de contexto · Plan de exportación a GitHub Projects** |
<!-- END_VERSIONS -->

---

## Licencia

La información de licencia será agregada por los mantenedores del proyecto.
