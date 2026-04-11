# SCHEMA.md

Contrato minimo del framework SpecNative Development v0.2.

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

## Documentos opcionales

- `tasks/<iniciativa>/TASKS.md`
- `workflows/PLANNING.md`
- `workflows/REVIEW.md`
- specs separadas por iniciativa en `agents/specs/`

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
