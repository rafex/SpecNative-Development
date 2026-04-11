# AGENTS.md

Este archivo define como deben operar los agentes dentro de este repo.

## Regla principal

Antes de trabajar en cualquier carpeta, leer primero su `README.md`.

## Mapa rapido

- `README.md` del root: explica la estructura del repo.
- `agents/README.md`: indice principal del contexto operativo.
- `agents/specs/README.md`: indice de specs disponibles.
- `tasks/README.md`: indice del sistema de ejecucion.
- `workflows/README.md`: procedimientos repetibles de operacion.

## Politica de contexto

- Los archivos en MAYUSCULAS son contexto para agentes.
- Los `README.md` no reemplazan el contexto; lo enrutan.
- Leer el minimo contexto suficiente para ejecutar bien la tarea.
- Actualizar siempre el documento fuente de verdad, no un resumen
  paralelo.
- Si la verdad cambia de manera persistente, actualizar el documento
  correcto antes de cerrar la tarea.

## Flujo de trabajo recomendado

1. Leer el `README.md` de la carpeta actual.
2. Revisar `agents/SCHEMA.md` para entender el contrato documental.
3. Revisar `agents/PRODUCT.md` y el contexto tecnico relevante.
4. Revisar o crear un `SPEC.md` en `agents/` o en `agents/specs/`.
5. Derivar o leer las tareas correspondientes en `tasks/`.
6. Implementar y validar siguiendo `workflows/IMPLEMENTATION.md`.
7. Registrar decisiones permanentes en `agents/DECISIONS.md`.
8. Mantener trazabilidad entre spec, tareas, decisiones y validacion.

## Criterio de actualizacion

- `ROADMAP.md` cambia cuando cambia la direccion.
- `SPEC.md` cambia cuando cambia el alcance del trabajo.
- `DECISIONS.md` cambia cuando se toma una decision que debe persistir.
- `tasks/` cambia cuando cambia el plan ejecutable o el estado real.
- `TRACEABILITY.md` cambia cuando se crea o modifica una relacion
  relevante entre artefactos.

## Estados obligatorios

- Toda spec debe declarar un estado:
  `draft | active | blocked | done | superseded`
- Toda tarea debe declarar un estado:
  `todo | in_progress | blocked | done`
- Toda decision debe declarar un estado:
  `proposed | accepted | deprecated | replaced`
