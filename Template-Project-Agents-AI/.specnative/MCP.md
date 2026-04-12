# MCP.md — SpecNative MCP Server

El servidor MCP de SpecNative expone el repositorio como **recursos**, **herramientas**
y **prompts** para que cualquier agente compatible con MCP pueda trabajar en modo
spec-first sin navegar manualmente el árbol de archivos.

## Instalación

El instalador de SpecNative descarga el servidor MCP y crea un entorno virtual
aislado con todas sus dependencias automáticamente:

```
.specnative/specnative_mcp.py   ← servidor MCP
.specnative/.venv/              ← entorno virtual con mcp instalado
```

Si necesitas instalarlo manualmente o actualizar el servidor:

```bash
# Descargar servidor actualizado
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/specnative_mcp.py \
  -o .specnative/specnative_mcp.py && chmod +x .specnative/specnative_mcp.py

# Crear venv e instalar dependencias (si no existe)
python3 -m venv .specnative/.venv
.specnative/.venv/bin/python3 -m pip install -U pip
.specnative/.venv/bin/python3 -m pip install mcp
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

Agrega a `opencode.json` en la raíz del proyecto:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "specnative_mcp": {
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

Alternativa con variable de entorno:

```toml
[mcp_servers.specnative]
command = "/ruta/a/tu/proyecto/.specnative/.venv/bin/python3"
args = ["/ruta/a/tu/proyecto/.specnative/specnative_mcp.py"]
type = "stdio"
env = { SPECNATIVE_REPO = "/ruta/a/tu/proyecto" }
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

| URI                          | Documento                         |
|------------------------------|-----------------------------------|
| `spec://agents`              | `AGENTS.md` — contrato operativo  |
| `spec://context/product`     | `agents/PRODUCT.md`               |
| `spec://context/architecture`| `agents/ARCHITECTURE.md`          |
| `spec://context/stack`       | `agents/STACK.md`                 |
| `spec://context/conventions` | `agents/CONVENTIONS.md`           |
| `spec://context/commands`    | `agents/COMMANDS.md`              |
| `spec://context/decisions`   | `agents/DECISIONS.md`             |
| `spec://context/roadmap`     | `agents/ROADMAP.md`               |
| `spec://context/traceability`| `agents/TRACEABILITY.md`          |
| `spec://context/spec`        | `agents/SPEC.md`                  |
| `spec://pipelines/ci`        | `pipelines/CI.md`                 |
| `spec://pipelines/cd`        | `pipelines/CD.md`                 |
| `spec://schema`              | `.specnative/SCHEMA.md`           |

---

## Herramientas disponibles

| Herramienta                  | Descripción                                                    |
|------------------------------|----------------------------------------------------------------|
| `status()`                   | Estado de cada spec y conteo de tareas por estado              |
| `validate()`                 | Verifica que existan todos los archivos obligatorios           |
| `list_specs()`               | Lista specs con ID, estado y owner                             |
| `list_tasks(initiative)`     | Lista tareas de una iniciativa con estados                     |
| `read_spec(initiative)`      | Lee el contenido de una spec                                   |
| `read_context(document)`     | Lee un documento de contexto por nombre corto                  |
| `export_index()`             | Exporta specs y task files con metadata TOML como JSON         |

---

## Prompts disponibles

| Prompt                                    | Descripción                                              |
|-------------------------------------------|----------------------------------------------------------|
| `start_initiative(name, problem)`         | Inicia una nueva iniciativa spec-driven                  |
| `plan_tasks(initiative)`                  | Deriva el plan de tareas desde una spec                  |
| `implement_task(initiative, task_id)`     | Implementa una tarea específica                          |
| `review_against_spec(initiative)`         | Revisa implementación contra criterios de aceptación     |
| `record_decision(title, ctx, dec, cons)`  | Registra una decisión persistente en DECISIONS.md        |
| `close_initiative(initiative)`            | Cierra la iniciativa y actualiza trazabilidad            |

---

## Separación de responsabilidades

El servidor MCP es **infraestructura del framework**, no contenido del proyecto:

- Los documentos del proyecto viven en `agents/`, `tasks/`, `pipelines/`, etc.
- El servidor MCP lee esos documentos; no los reemplaza ni escribe en ellos.
- Las reglas de ownership siguen siendo las de `AGENTS.md` y `SCHEMA.md`.
- El servidor no escribe en el repositorio — las escrituras las hace el agente
  siguiendo los documentos fuente correctos.
- `.specnative/specnative_mcp.py` y `.specnative/.venv/` pueden agregarse a
  `.gitignore` si prefieres no versionarlos; o commitearlos si quieres que el
  equipo use exactamente la misma versión.
