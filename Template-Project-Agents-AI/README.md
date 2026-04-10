# Template Project Agents AI

Framework de spec-driven development para operar repos AI-native.
Inspirado en Agent OS (Builder Methods), adaptado a una regla simple:
la navegacion empieza por carpeta, no por un unico documento global.

## Principios

- Los `README.md` de cada carpeta son el punto de entrada y el indice
  de navegacion.
- Los archivos en MAYUSCULAS son contexto operativo para agentes.
- Cada verdad vive en un solo documento. No duplicar entre archivos.
- Leer el minimo contexto suficiente para ejecutar bien la tarea.

## Documentos del framework

- `PRODUCT.md` define el problema, usuarios, objetivos y alcance.
- `SPEC.md` define una capacidad o cambio que debe implementarse.
- `DECISIONS.md` registra decisiones relevantes y sus tradeoffs.
- `ARCHITECTURE.md`, `STACK.md`, `CONVENTIONS.md` y `COMMANDS.md`
  reducen ambiguedad operativa para agentes y humanos.
- `ROADMAP.md` mantiene direccion, no detalle de implementacion.

Todos estos documentos viven dentro de `agents/`.

## Estructura

- [`AGENTS.md`](./AGENTS.md):
  contrato de comportamiento para agentes dentro del proyecto.
- [`agents/README.md`](./agents/README.md):
  indice principal del sistema de contexto.

## Como usar este template

1. Copiar este template a un repo nuevo.
2. Personalizar `AGENTS.md` con las reglas del proyecto.
3. Completar los documentos base dentro de `agents/`.
4. Crear specs nuevas dentro de `agents/specs/`.

## Flujo recomendado

1. Entender el producto en `agents/PRODUCT.md`.
2. Revisar restricciones en `agents/ARCHITECTURE.md`,
   `agents/STACK.md` y `agents/CONVENTIONS.md`.
3. Escribir o actualizar `agents/SPEC.md` o crear una spec separada
   en `agents/specs/`.
4. Implementar.
5. Registrar decisiones en `agents/DECISIONS.md` si cambian supuestos,
   estructura o tradeoffs.

## Regla de lectura

1. Entrar por el `README.md` de la carpeta actual.
2. Elegir el documento contextual correcto desde ese indice.
3. Leer solo el contexto necesario para la tarea.
4. Actualizar el documento fuente de verdad adecuado.
