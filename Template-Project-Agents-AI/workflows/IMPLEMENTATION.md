# IMPLEMENTATION.md

Workflow base para ejecutar una iniciativa.

## Pasos

1. Leer `AGENTS.md` y el `README.md` de la carpeta actual.
2. Leer `agents/SCHEMA.md` para recordar el contrato.
3. Leer la spec activa y su contexto tecnico relevante.
4. Leer o crear tareas en `tasks/`.
5. Implementar en lotes pequenos.
6. Ejecutar validacion definida en la spec o en las tareas.
7. Actualizar estados, trazabilidad y decisiones persistentes.
8. Ejecutar `python3 ./tools/specnative.py validate`.

## Regla de cierre

No cerrar una iniciativa si falta alguno de estos puntos:

- spec con estado final consistente
- tareas con estado actualizado
- evidencia de validacion o bloqueo explicitado
- decisiones persistentes registradas si hubo tradeoffs nuevos
