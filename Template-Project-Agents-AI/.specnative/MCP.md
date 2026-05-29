# MCP.md — SpecNative MCP Server v0.5

El servidor MCP de SpecNative expone el repositorio como **recursos**, **herramientas**
y **prompts** para que cualquier agente compatible con MCP pueda trabajar en modo
spec-first sin navegar manualmente el árbol de archivos.

La versión 0.5 agrega continuidad multi-agente: `checkpoint`, `resume`,
`update_task`, `log_decision` y `context_snapshot` permiten que un agente
continúe exactamente donde lo dejó otro — sin importar si fue Claude Code,
Codex, Cursor, o cualquier otro.

## Instalación

El instalador de SpecNative descarga el servidor MCP y crea un entorno virtual
aislado con todas sus dependencias automáticamente:

```
.specnative/specnative_mcp.py   ← servidor MCP
.specnative/.venv/              ← entorno virtual con mcp instalado
```

Si necesitas reinstalar o actualizar el servidor:

```bash
python3 install.py --reinstall --target /ruta/a/tu/repo
```

---

## Configuración por agente

El servidor usa el Python del venv aislado en `.specnative/.venv/`.
Reemplaza `/ruta/a/tu/proyecto` con la ruta absoluta real de tu repositorio.

### Claude Code

```bash
# Desde la raíz de tu proyecto:
claude mcp add specnative \
  "$(pwd)/.specnative/.venv/bin/python3" "$(pwd)/.specnative/specnative_mcp.py" \
  -- --repo "$(pwd)"
```

O agrega a `.claude/mcp_settings.json` (proyecto) o `~/.claude/mcp_settings.json` (global):

```json
{
  "mcpServers": {
    "specnative": {
      "command": "/ruta/a/tu/proyecto/.specnative/.venv/bin/python3",
      "args": [
        "/ruta/a/tu/proyecto/.specnative/specnative_mcp.py",
        "--repo", "/ruta/a/tu/proyecto"
      ]
    }
  }
}
```

### Claude Desktop

Agrega a `claude_desktop_config.json`
(`~/Library/Application Support/Claude/` en macOS,
`%APPDATA%\Claude\` en Windows):

```json
{
  "mcpServers": {
    "specnative": {
      "command": "/ruta/a/tu/proyecto/.specnative/.venv/bin/python3",
      "args": [
        "/ruta/a/tu/proyecto/.specnative/specnative_mcp.py",
        "--repo", "/ruta/a/tu/proyecto"
      ]
    }
  }
}
```

### OpenCode

Generado automáticamente en `opencode.json` durante la instalación:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "specnative": {
      "type": "local",
      "enabled": true,
      "command": [
        "./.specnative/.venv/bin/python3",
        "./.specnative/specnative_mcp.py"
      ]
    }
  }
}
```

### Codex CLI

Agrega a `~/.codex/config.toml` (global) o `codex.toml` (raíz del proyecto):

```toml
[mcp_servers.specnative]
command = "/ruta/a/tu/proyecto/.specnative/.venv/bin/python3"
args = [
  "/ruta/a/tu/proyecto/.specnative/specnative_mcp.py",
  "--repo", "/ruta/a/tu/proyecto"
]
type = "stdio"
```

### Variable de entorno (alternativa universal)

```bash
export SPECNATIVE_REPO=/ruta/a/tu/proyecto
.specnative/.venv/bin/python3 .specnative/specnative_mcp.py
```

### Transporte SSE (agentes remotos)

```bash
.specnative/.venv/bin/python3 .specnative/specnative_mcp.py \
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
| `read_spec(initiative)`      | Lee el contenido de una spec                                   |
| `read_context(document)`     | Lee un documento de contexto por nombre corto                  |
| `export_index()`             | Exporta specs y task files con metadata TOML como JSON         |
| `context_snapshot(initiative?)` | Dump completo de contexto para onboarding de nuevo agente  |

### Continuidad multi-agente (v0.5)

| Herramienta                               | Descripción                                                    |
|-------------------------------------------|----------------------------------------------------------------|
| `resume()`                                | Lee SESSION.md y genera resumen de continuidad                 |
| `checkpoint(initiative, task_id, intent, next_steps, context_notes?, agent_name?)` | Guarda estado antes de pausar |
| `update_task(initiative, task_id, state, notes?)` | Actualiza estado de tarea en TASKS.md              |
| `log_decision(title, context, decision, consequences)` | Append rápido a DECISIONS.md              |

---

## Prompts disponibles

| Prompt                                    | Descripción                                              |
|-------------------------------------------|----------------------------------------------------------|
| `start_initiative(name, problem)`         | Inicia una nueva iniciativa spec-driven                  |
| `plan_tasks(initiative)`                  | Deriva el plan de tareas desde una spec                  |
| `implement_task(initiative, task_id)`     | Implementa una tarea específica                          |
| `review_against_spec(initiative)`         | Revisa implementación contra criterios de aceptación     |
| `handoff(summary, next_steps, decisions?)` | Genera traspaso estructurado para el siguiente agente   |
| `record_decision(title, ctx, dec, cons)`  | Registra una decisión persistente en DECISIONS.md        |
| `close_initiative(initiative)`            | Cierra la iniciativa y actualiza trazabilidad            |

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
- `.specnative/specnative_mcp.py` y `.specnative/.venv/` pueden agregarse a
  `.gitignore` si prefieres no versionarlos; o commitearlos si quieres que el
  equipo use exactamente la misma versión.
