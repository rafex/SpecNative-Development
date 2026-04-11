# SCHEMA.md

Contrato minimo del framework SpecNative Development v0.3.

## Objetivo

Definir que documentos son obligatorios, que rol cumple cada uno y
que estados o campos minimos deben existir para reducir ambiguedad.

En `v0.3`, specs y archivos de tareas deben incluir un bloque
`toml` parseable para que herramientas externas puedan validar o
exportar el estado del proyecto.

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

## Documentos opcionales

- `tasks/<iniciativa>/TASKS.md`
- `workflows/PLANNING.md`
- `workflows/REVIEW.md`
- specs separadas por iniciativa en `agents/specs/`
- `exports/*.json` generados por tooling

## Ownership documental

- Problema y objetivos: `PRODUCT.md`
- Direccion temporal: `ROADMAP.md`
- Restricciones del sistema: `ARCHITECTURE.md`, `STACK.md`
- Reglas operativas: `CONVENTIONS.md`, `COMMANDS.md`
- Cambio requerido: `SPEC.md` o `agents/specs/**/SPEC.md`
- Descomposicion ejecutable: `tasks/**/TASKS.md`
- Decisiones persistentes: `DECISIONS.md`
- Relaciones entre artefactos: `TRACEABILITY.md`

## Estados obligatorios

## Metadata parseable

Los siguientes artefactos deben incluir un bloque `toml` cercano al
inicio del archivo:

- `agents/SPEC.md`
- `agents/specs/**/SPEC.md`
- `tasks/**/TASKS.md`

Campos minimos para specs:

- `artifact_type = "spec"`
- `id`
- `state`
- `owner`
- `created_at`
- `updated_at`

Campos minimos para archivos de tareas:

- `artifact_type = "task_file"`
- `initiative`
- `spec_id`
- `owner`
- `state`

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
- `Estado`
- `Owner`
- `Spec relacionada`
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
- metadata parseable consistente con el contenido humano del archivo
