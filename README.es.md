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

---

## Inicio Rápido

### Instalar en un repositorio existente

```bash
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/install.py \
  | python3 - --target /ruta/a/tu/repo --profile minimal
```

O descarga una vez y ejecuta localmente:

```bash
python3 install.py --target /ruta/a/tu/repo --profile minimal --include-examples
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
├── agents/
│   ├── PRODUCT.md         # Problema, usuarios, objetivos (permanente)
│   ├── ARCHITECTURE.md    # Estructura del sistema y límites
│   ├── STACK.md           # Stack tecnológico y restricciones de versión
│   ├── CONVENTIONS.md     # Reglas de código, naming, testing
│   ├── COMMANDS.md        # Comandos del proyecto (build, test, lint...)
│   ├── SPEC.md            # Spec activa (o entrada a specs/)
│   ├── DECISIONS.md       # Decisiones persistentes y tradeoffs
│   ├── ROADMAP.md         # Dirección temporal
│   ├── TRACEABILITY.md    # Vínculos entre artefactos
│   └── specs/<iniciativa>/SPEC.md
├── tasks/<iniciativa>/TASKS.md
├── workflows/             # PLANNING.md, IMPLEMENTATION.md, REVIEW.md
├── pipelines/             # CI.md, CD.md — contexto de CI/CD
└── .specnative/           # Infraestructura del framework
    ├── SCHEMA.md          # Contrato del framework (archivos, estados)
    ├── CLI.md             # Referencia del CLI y el servidor MCP
    └── MCP.md             # Configuración del servidor MCP por agente
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
| `tasks/**/TASKS.md` | Plan ejecutable con estado, owner, criterio de cierre |
| `TRACEABILITY.md` | Vínculos entre artefactos (actualizar al cerrar iniciativa) |
| `pipelines/CI.md` | Definición de gates automatizados |
| `pipelines/CD.md` | Proceso de entrega y ambientes |

---

## Tooling del framework

### CLI — `tools/specnative.py`

```bash
python3 specnative.py status              # Estado de specs y tareas
python3 specnative.py validate            # Verificar archivos y TOML
python3 specnative.py export-index        # Exportar specs/tareas como JSON
python3 specnative.py export-traceability # Exportar matriz de trazabilidad
python3 specnative.py install --target /ruta/al/repo --profile minimal
```

### Servidor MCP — `tools/specnative_mcp.py` (v0.6) <!-- MCP_VERSION -->

Expone el repositorio como recursos, herramientas y prompts MCP para que
cualquier agente compatible trabaje en modo spec-first sin navegar
manualmente el árbol de archivos.

**Recursos** — documentos de contexto por URI:

```
spec://agents                  → AGENTS.md
spec://context/product         → agents/PRODUCT.md
spec://context/architecture    → agents/ARCHITECTURE.md
spec://context/decisions       → agents/DECISIONS.md
spec://context/roadmap         → agents/ROADMAP.md
spec://pipelines/ci            → pipelines/CI.md
spec://schema                  → .specnative/SCHEMA.md
# … y más (ver MCP.md)
```

**Herramientas**: `status`, `validate`, `list_specs`, `list_tasks`, `read_spec`, `read_context`, `export_index`

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
2. Revisar `agents/ROADMAP.md` — confirmar que la iniciativa es coherente con la dirección.
3. Leer `agents/PRODUCT.md` y contexto técnico relevante.
4. Leer `agents/DECISIONS.md` — respetar tradeoffs persistentes.
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
<!-- END_VERSIONS -->

---

## Licencia

La información de licencia será agregada por los mantenedores del proyecto.
