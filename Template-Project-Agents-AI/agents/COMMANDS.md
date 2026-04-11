# COMMANDS.md

Lista de comandos operativos del proyecto.

## Objetivo

Reducir la ambiguedad de ejecucion para agentes y humanos.

## Template

### Setup

```bash
# instalar dependencias
```

### Desarrollo

```bash
# iniciar app
```

### Tests

```bash
# correr tests
```

### Lint y formato

```bash
# lint
# format
```

### Build

```bash
# build
```

### Utilidad

```bash
# seed
# migrate
# generar tipos
# validar estructura del framework
python3 ./tools/specnative.py validate
# exportar indice del proyecto
python3 ./tools/specnative.py export-index --output exports/index.json
# exportar trazabilidad
python3 ./tools/specnative.py export-traceability --output exports/traceability.json
# instalar SpecNative en otro repo
python3 ./tools/specnative.py install --target /ruta/al/repo --branch specnative/install-v0.3
```
