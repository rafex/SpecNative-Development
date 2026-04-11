# Template Project Agents AI

Framework de spec-driven development para operar repos AI-native.
Inspirado en Agent OS (Builder Methods), adaptado a una regla simple:
la navegacion empieza por carpeta, no por un unico documento global.

Esta version `v0.3` endurece el framework agregando:

- contrato documental explicito
- estados obligatorios para specs, tareas y decisiones
- trazabilidad entre artefactos
- capa de ejecucion con `tasks/`
- workflows operativos repetibles
- metadata parseable en TOML dentro de markdown
- metadata canonica por tarea, no solo por archivo
- tooling en Python para validar y exportar
- instalacion segura sobre repos existentes con branch dedicado
- ejemplo end-to-end por iniciativa

## Principios

- Los `README.md` de cada carpeta son el punto de entrada y el indice
  de navegacion.
- Los archivos en MAYUSCULAS son contexto operativo para agentes.
- Cada verdad vive en un solo documento. No duplicar entre archivos.
- Leer el minimo contexto suficiente para ejecutar bien la tarea.
- Toda iniciativa relevante debe poder trazarse desde spec hasta
  validacion.

## Documentos del framework

- `PRODUCT.md` define el problema, usuarios, objetivos y alcance.
- `SPEC.md` define una capacidad o cambio que debe implementarse.
- `DECISIONS.md` registra decisiones relevantes y sus tradeoffs.
- `ARCHITECTURE.md`, `STACK.md`, `CONVENTIONS.md` y `COMMANDS.md`
  reducen ambiguedad operativa para agentes y humanos.
- `ROADMAP.md` mantiene direccion, no detalle de implementacion.
- `SCHEMA.md` define el contrato minimo del framework.
- `TRACEABILITY.md` registra relaciones entre specs, tareas,
  decisiones, codigo y validacion.

Todos estos documentos viven dentro de `agents/`.

## Estructura

- [`AGENTS.md`](./AGENTS.md):
  contrato de comportamiento para agentes dentro del proyecto.
- [`agents/README.md`](./agents/README.md):
  indice principal del sistema de contexto.
- [`tasks/README.md`](./tasks/README.md):
  indice del sistema de ejecucion y estado de tareas.
- [`workflows/README.md`](./workflows/README.md):
  procedimientos repetibles para planificar, implementar y validar.
- [`docs/README.md`](./docs/README.md):
  documentacion del framework y de su tooling.

## Como usar este template

1. Copiar este template a un repo nuevo.
2. Personalizar `AGENTS.md` con las reglas del proyecto.
3. Completar `agents/SCHEMA.md` y los documentos base dentro de
   `agents/`.
4. Crear specs nuevas dentro de `agents/specs/`.
5. Derivar tareas ejecutables en `tasks/`.
6. Revisar [`docs/README.md`](./docs/README.md) si necesitas usar la
   CLI del framework o adoptar la plantilla en otro repo.

## Flujo recomendado

1. Entender el producto en `agents/PRODUCT.md`.
2. Revisar restricciones en `agents/ARCHITECTURE.md`,
   `agents/STACK.md` y `agents/CONVENTIONS.md`.
3. Escribir o actualizar `agents/SPEC.md` o crear una spec separada
   en `agents/specs/`.
4. Crear o actualizar tareas en `tasks/`.
5. Implementar siguiendo `workflows/IMPLEMENTATION.md`.
6. Registrar decisiones en `agents/DECISIONS.md` si cambian supuestos,
   estructura o tradeoffs.
7. Registrar trazabilidad en `agents/TRACEABILITY.md`.

## Regla de lectura

1. Entrar por el `README.md` de la carpeta actual.
2. Elegir el documento contextual correcto desde ese indice.
3. Leer solo el contexto necesario para la tarea.
4. Actualizar el documento fuente de verdad adecuado.

## Regla de cierre

Una iniciativa no deberia considerarse cerrada hasta que existan:

- spec con estado actualizado
- tareas con estado final consistente
- validacion ejecutada o plan de validacion explicitado
- trazabilidad minima hacia decisiones o artefactos relevantes

## Regla de separacion

- `agents/` contiene contexto del proyecto adoptante.
- `docs/` contiene documentacion del framework y su tooling.
- `tools/` contiene implementacion tecnica del framework.
