# SCHEMA.md

Contrato minimo del framework SpecNative Development v0.4.

## Objetivo

Definir que documentos son obligatorios, que rol cumple cada uno y
que estados o campos minimos deben existir para reducir ambiguedad.

## Documentos obligatorios

- `AGENTS.md`
- `README.md`
- `agents/README.md`
- `agents/PRODUCT.md`
- `agents/ARCHITECTURE.md`
- `agents/STACK.md`
- `agents/CONVENTIONS.md`
- `agents/COMMANDS.md`
- `agents/DECISIONS.md`
- `agents/ROADMAP.md`
- `agents/SPEC.md` o al menos una spec en `agents/specs/`
- `agents/TRACEABILITY.md`
- `tasks/README.md`
- `workflows/README.md`
- `pipelines/README.md`

## Documentos opcionales

- `tasks/<iniciativa>/TASKS.md`
- `workflows/PLANNING.md`
- `workflows/REVIEW.md`
- specs separadas por iniciativa en `agents/specs/`
- `exports/*.json` generados por tooling externo

## Infraestructura del framework (`.specnative/`)

- `SCHEMA.md` — este archivo; contrato del framework
- `CLI.md` — referencia del CLI (`specnative.py`) y el servidor MCP
- `MCP.md` — configuracion del servidor MCP por agente (v0.4+)

## Ownership documental

- Problema y objetivos: `PRODUCT.md`
- Direccion temporal: `ROADMAP.md`
- Restricciones del sistema: `ARCHITECTURE.md`, `STACK.md`
- Reglas operativas: `CONVENTIONS.md`, `COMMANDS.md`
- Contrato del framework: `.specnative/SCHEMA.md`
- Cambio requerido: `SPEC.md` o `agents/specs/**/SPEC.md`
- Descomposicion ejecutable: `tasks/**/TASKS.md`
- Decisiones persistentes: `DECISIONS.md`
- Relaciones entre artefactos: `TRACEABILITY.md`
- Gates de CI y proceso de CD: `pipelines/CI.md`, `pipelines/CD.md`

## Estados obligatorios

### Specs

Toda spec debe declarar:

- `ID`
- `Estado`
- `Owner`
- `Fecha de creacion`
- `Ultima actualizacion`

Estados permitidos:

- `draft`
- `active`
- `blocked`
- `done`
- `superseded`

### Tareas

Toda tarea debe declarar:

- `ID`
- `Title`
- `State`
- `Owner`
- `Criterio de cierre`

Estados permitidos:

- `todo`
- `in_progress`
- `blocked`
- `done`

### Decisiones

Toda decision debe declarar:

- `ID`
- `Fecha`
- `Estado`
- `Contexto`
- `Decision`
- `Consecuencias`

Estados permitidos:

- `proposed`
- `accepted`
- `deprecated`
- `replaced`

## Reglas de trazabilidad

Toda iniciativa relevante deberia permitir navegar:

1. de la spec a sus tareas
2. de las tareas a la validacion
3. de la spec o tareas a decisiones persistentes
4. de los artefactos a los archivos o cambios principales

## Regla de validacion

Antes de cerrar una iniciativa, comprobar:

- estado final consistente
- validacion definida o ejecutada
- trazabilidad minima registrada
- ausencia de contradicciones entre spec, tareas y decisiones

## Metadata parseable (opcional)

Para proyectos que usan el CLI de SpecNative, specs y archivos de
tareas pueden incluir un bloque `toml` que permite validacion y
exportacion automatica del estado del proyecto.

Cuando se usa el CLI, los bloques `toml` deben aparecer cerca del
inicio del archivo y contener al menos los campos requeridos por el
comando `validate`. Ver `.specnative/CLI.md` para referencia completa de
campos y comandos disponibles.

El TOML no es un requisito del contrato base. Los documentos son
validos sin el y pueden adoptarlo de forma incremental.
