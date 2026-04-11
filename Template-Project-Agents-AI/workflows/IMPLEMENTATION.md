# IMPLEMENTATION.md

Procedimiento detallado para ejecutar una iniciativa.
El flujo general de trabajo esta en `AGENTS.md`.

## Pasos

1. Leer la spec activa y confirmar que su estado es `active`.
2. Leer el contexto tecnico relevante: `ARCHITECTURE.md`, `STACK.md`,
   `CONVENTIONS.md` segun lo que la spec requiera.
3. Leer o crear las tareas en `tasks/<iniciativa>/TASKS.md`.
4. Implementar en lotes pequenos siguiendo el orden de dependencias.
5. Ejecutar la validacion definida en la spec o en cada tarea.
   Consultar `pipelines/CI.md` para verificar que los gates
   obligatorios del proyecto estan cubiertos.
6. Actualizar el estado de cada tarea al completarla.
7. Registrar decisiones persistentes en `agents/DECISIONS.md` si
   surgieron tradeoffs nuevos.
8. Actualizar `agents/TRACEABILITY.md` al cerrar la iniciativa.
9. (Opcional) Si el proyecto usa el CLI de SpecNative, ejecutar
   validacion automatica. Ver `.specnative/CLI.md`.

## Regla de cierre

No cerrar una iniciativa si falta alguno de estos puntos:

- spec con estado final consistente
- tareas con estado actualizado
- evidencia de validacion o bloqueo explicitado
- decisiones persistentes registradas si hubo tradeoffs nuevos
