# MCP.md — SpecNative MCP Server

El servidor MCP de SpecNative expone el repositorio como **recursos**, **herramientas**
y **prompts** para que cualquier agente compatible con MCP pueda trabajar en modo
spec-first sin navegar manualmente el árbol de archivos.

## Requisito

```bash
pip install mcp
```

El servidor vive en el repositorio de SpecNative Development, no en el proyecto adoptante:

```
SpecNative-Development/
└── tools/
    └── specnative_mcp.py   ← servidor MCP
```

---

## Configuración por agente

### Claude Desktop

Agrega al archivo `claude_desktop_config.json`
(`~/Library/Application Support/Claude/` en macOS,
`%APPDATA%\Claude\` en Windows):

```json
{
  "mcpServers": {
    "specnative": {
      "command": "python3",
      "args": [
        "/ruta/a/SpecNative-Development/tools/specnative_mcp.py",
        "--repo", "/ruta/a/tu/proyecto"
      ]
    }
  }
}
```

### Claude Code

Agrega al archivo `.claude/mcp_settings.json` del proyecto (o al global
`~/.claude/mcp_settings.json`):

```json
{
  "mcpServers": {
    "specnative": {
      "command": "python3",
      "args": [
        "/ruta/a/SpecNative-Development/tools/specnative_mcp.py",
        "--repo", "/ruta/a/tu/proyecto"
      ]
    }
  }
}
```

También puedes registrarlo desde la CLI de Claude Code:

```bash
claude mcp add specnative \
  python3 /ruta/a/SpecNative-Development/tools/specnative_mcp.py \
  -- --repo /ruta/a/tu/proyecto
```

### OpenCode

Agrega al archivo `.opencode/config.json` del proyecto:

```json
{
  "mcp": {
    "servers": {
      "specnative": {
        "command": "python3",
        "args": [
          "/ruta/a/SpecNative-Development/tools/specnative_mcp.py",
          "--repo", "/ruta/a/tu/proyecto"
        ]
      }
    }
  }
}
```

### Variable de entorno (alternativa)

Si prefieres no pasar `--repo` como argumento puedes exportar:

```bash
export SPECNATIVE_REPO=/ruta/a/tu/proyecto
python3 /ruta/a/SpecNative-Development/tools/specnative_mcp.py
```

### Transporte SSE (agentes remotos)

```bash
python3 specnative_mcp.py --repo /ruta/al/proyecto --transport sse --port 8765
```

---

## Recursos disponibles

Los recursos permiten al agente leer documentos de contexto por URI sin
necesidad de conocer la ruta física del archivo.

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

| Herramienta          | Descripción                                                    |
|----------------------|----------------------------------------------------------------|
| `status()`           | Estado de cada spec y conteo de tareas por estado              |
| `validate()`         | Verifica que existan todos los archivos obligatorios           |
| `list_specs()`       | Lista specs con ID, estado y owner                             |
| `list_tasks(initiative)` | Lista tareas de una iniciativa con estados               |
| `read_spec(initiative)` | Lee el contenido de una spec                              |
| `read_context(document)` | Lee un documento de contexto por nombre corto           |
| `export_index()`     | Exporta specs y task files con metadata TOML como JSON         |

---

## Prompts disponibles

Los prompts son flujos de trabajo estructurados. El agente los usa como punto
de partida para tareas complejas.

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
- El servidor MCP lee esos documentos; no los reemplaza.
- Las reglas de ownership siguen siendo las de `AGENTS.md` y `SCHEMA.md`.
- El servidor no escribe en el repositorio — las escrituras las hace el agente
  siguiendo los documentos fuente correctos.
