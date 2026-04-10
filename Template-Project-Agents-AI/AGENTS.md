# AGENTS.md

Este archivo define como deben operar los agentes dentro de este repo.

## Regla principal

Antes de trabajar en cualquier carpeta, leer primero su `README.md`.

## Mapa rapido

- `README.md` del root: explica la estructura del repo.
- `agents/README.md`: indice principal del contexto operativo.
- `agents/specs/README.md`: indice de specs disponibles.

## Politica de contexto

- Los archivos en MAYUSCULAS son contexto para agentes.
- Los `README.md` no reemplazan el contexto; lo enrutan.
- Leer el minimo contexto suficiente para ejecutar bien la tarea.
- Actualizar siempre el documento fuente de verdad, no un resumen
  paralelo.

## Flujo de trabajo recomendado

1. Leer el `README.md` de la carpeta actual.
2. Revisar `agents/PRODUCT.md` y el contexto tecnico relevante.
3. Revisar o crear un `SPEC.md` en `agents/` o en `agents/specs/`.
4. Implementar y validar.
5. Registrar decisiones permanentes en `agents/DECISIONS.md`.

## Criterio de actualizacion

- `ROADMAP.md` cambia cuando cambia la direccion.
- `SPEC.md` cambia cuando cambia el alcance del trabajo.
- `DECISIONS.md` cambia cuando se toma una decision que debe persistir.
