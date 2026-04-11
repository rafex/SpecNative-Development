# Agents Context

Indice principal del contexto operativo del proyecto.

## Como usar esta carpeta

Si eres un agente o una persona entrando por primera vez:

1. Lee este archivo.
2. Abre solo el documento que corresponde a tu tarea.
3. Si trabajas sobre una spec concreta, ve a `specs/README.md`.
4. Si necesitas ejecutar trabajo, ve a `../tasks/README.md`.
5. Si necesitas entender los gates de CI o el proceso de deploy,
   ve a `../pipelines/README.md`.
6. Si necesitas el contrato del framework o el CLI, ve a
   `../.specnative/README.md`.

## Documentos base

- [`PRODUCT.md`](./PRODUCT.md):
  que problema resuelve el producto, para quien y con que objetivos.
- [`ROADMAP.md`](./ROADMAP.md):
  direccion y prioridades de mediano plazo.
- [`ARCHITECTURE.md`](./ARCHITECTURE.md):
  estructura del sistema, modulos y limites.
- [`STACK.md`](./STACK.md):
  tecnologias, versiones y restricciones tecnicas.
- [`CONVENTIONS.md`](./CONVENTIONS.md):
  reglas de codigo, naming, testing y organizacion.
- [`COMMANDS.md`](./COMMANDS.md):
  comandos de desarrollo, test, lint y operaciones comunes.
- [`DECISIONS.md`](./DECISIONS.md):
  decisiones relevantes ya tomadas y su racional.
- [`TRACEABILITY.md`](./TRACEABILITY.md):
  enlaces entre iniciativas, tareas, decisiones y validacion.
- [`SPEC.md`](./SPEC.md):
  spec activa o spec general cuando aun no se separa por iniciativa.
- [`specs/README.md`](./specs/README.md):
  indice de specs por iniciativa.

## Ownership documental

- Producto y direccion: `PRODUCT.md` y `ROADMAP.md`
- Sistema y restricciones: `ARCHITECTURE.md`, `STACK.md`,
  `CONVENTIONS.md`, `COMMANDS.md`
- Ejecucion: `SPEC.md` y `../tasks/`
- Memoria de decisiones: `DECISIONS.md`
- Trazabilidad: `TRACEABILITY.md`
- Contrato del framework: `.specnative/SCHEMA.md`

## Separacion importante

Los comandos y herramientas del framework no deben documentarse en
`COMMANDS.md`. Ese archivo queda reservado para comandos del proyecto
real que el agente debe usar para desarrollar, probar y construir.
