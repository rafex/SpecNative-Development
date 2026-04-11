# ADOPTION.md

Como adoptar SpecNative en un repositorio existente.

## Principio

La adopcion del framework no debe mezclarse con el contexto del proyecto
destino.

Por eso:

- `agents/COMMANDS.md` describe comandos del proyecto
- `docs/` describe tooling y operacion del framework

## Flujo recomendado

1. Ejecutar la CLI de instalacion en una rama dedicada.
2. Revisar los archivos agregados.
3. Adaptar `AGENTS.md`, `agents/PRODUCT.md`, `agents/ARCHITECTURE.md`
   y `agents/COMMANDS.md` al proyecto real.
4. Confirmar que los comandos del proyecto queden correctos.
5. Hacer merge de la rama de instalacion a la rama principal.

## Ajustes manuales esperados

- remover ejemplos no necesarios
- completar stack y comandos reales
- definir la primera spec activa
- confirmar ownership documental
