# Template Project Agents AI

Plantilla de SpecNative Development v0.7 para repositorios cuyo contexto
operativo debe poder ser leído y actualizado por agentes de IA.

El punto de entrada es `AGENTS.md`. Todo el contexto persistente del proyecto
vive en `spec-native/`; la infraestructura y documentación del framework vive
en `.specnative/`.

## Entrada rápida

En Claude Code usa `/spec <solicitud>`. En OpenCode y Codex usa el prompt
`spec <solicitud>`. Para flujos explícitos están `spec-decision`, `spec-plan`,
`spec-implement`, `spec-review`, `spec-close`, `spec-backlog`, `spec-context`,
`spec-architecture` y `spec-convention`. El MCP `specnative(request)` decide
el flujo adecuado cuando el usuario no necesita escogerlo.

## Qué incluye

- contrato de operación para agentes en `AGENTS.md`
- contexto de producto, arquitectura, stack, convenciones y comandos en
  `spec-native/`
- specs y tareas organizadas por iniciativa
- workflows de planificación, implementación y revisión
- pipelines documentados para CI/CD
- `SESSION.md` para continuidad entre agentes
- servidor MCP con herramientas de lectura, escritura y prompts de workflow
- comandos nativos para Claude Code, OpenCode y Codex
- archetypes y templates reutilizables desde MCP

## Estructura

```text
.
├── AGENTS.md
├── README.md
├── spec-native/
│   ├── README.md
│   ├── PRODUCT.md
│   ├── ARCHITECTURE.md
│   ├── STACK.md
│   ├── CONVENTIONS.md
│   ├── COMMANDS.md
│   ├── DECISIONS.md
│   ├── ROADMAP.md
│   ├── TRACEABILITY.md
│   ├── SESSION.md
│   ├── specs/
│   ├── tasks/
│   ├── backlog/
│   ├── workflows/
│   └── pipelines/
├── .specnative/
│   ├── README.md
│   ├── MCP.md
│   ├── commands.json           # Fuente de verdad de comandos de agente
│   ├── CLI.md
│   ├── SCHEMA.md
│   ├── archetypes/
│   ├── integrations/
│   └── templates/
├── .claude/commands/
├── .claude/skills/         # Carga automática del flujo SpecNative en Claude/OpenCode
├── .codex/skills/          # Skill de proyecto para entornos Codex compatibles
├── codex.toml
└── opencode.json
```

## Gestion del trabajo

Las tareas en `spec-native/tasks/**/TASKS.md` son la fuente de verdad de
ejecucion. El CLI genera una vista de entrega a partir de su estado,
prioridad y dependencias:

```bash
python3 /path/to/SpecNative-Development/tools/specnative.py board --target .
```

No edites la salida del tablero para mover una tarjeta. Actualiza la tarea
canonica y registra `completion_evidence` al cambiarla a `done`. Consulta
`spec-native/backlog/README.md` para los formatos Markdown, Mermaid y JSON,
y para el plan de exportacion de solo lectura a GitHub Projects.

## Ownership documental

- `spec-native/PRODUCT.md`: problema, usuarios, objetivos y no objetivos.
- `spec-native/ARCHITECTURE.md`: módulos, límites y dependencias permitidas.
- `spec-native/STACK.md`: tecnologías y restricciones de versión.
- `spec-native/CONVENTIONS.md`: reglas de código, testing y commits.
- `spec-native/COMMANDS.md`: comandos reales del proyecto adoptante; nunca
  comandos del framework.
- `spec-native/specs/`: comportamiento y criterios de aceptación por iniciativa.
- `spec-native/tasks/`: descomposición ejecutable y estados de tareas.
- `spec-native/DECISIONS.md`: trade-offs persistentes.
- `spec-native/SESSION.md`: estado activo para continuidad entre agentes.
- `spec-native/TRACEABILITY.md`: relación entre spec, tareas, decisiones,
  artefactos y validación.
- `.specnative/`: contrato y tooling del framework.

## Flujo recomendado

1. Leer `AGENTS.md` y `spec-native/README.md`.
2. Ejecutar `health_check()` vía MCP o revisar manualmente los documentos base.
3. Completar el contexto del proyecto antes de iniciar una implementación.
4. Crear una spec en `spec-native/specs/<iniciativa>/SPEC.md`.
5. Derivar tareas en `spec-native/tasks/<iniciativa>/TASKS.md`.
6. Implementar siguiendo `spec-native/workflows/IMPLEMENTATION.md`.
7. Actualizar tareas, decisiones y `SESSION.md` durante el trabajo.
8. Cerrar la iniciativa actualizando `TRACEABILITY.md` y ejecutando las
   validaciones del proyecto.

## Documentación del framework

- [`.specnative/README.md`](./.specnative/README.md): separación entre
  contexto del proyecto y tooling del framework.
- [`.specnative/MCP.md`](./.specnative/MCP.md): configuración y herramientas
  del servidor MCP.
- [`.specnative/CLI.md`](./.specnative/CLI.md): CLI externa y exportaciones.
- [`.specnative/SCHEMA.md`](./.specnative/SCHEMA.md): contrato documental.

## Adopción

Para instalar esta estructura en un repositorio existente, descarga el
`install.py` desde un release de GitHub. El instalador valida que el worktree
esté limpio, crea una rama dedicada, preserva la configuración existente y deja
el cambio listo para revisión y merge.
