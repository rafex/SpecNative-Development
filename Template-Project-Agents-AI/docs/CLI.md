# CLI.md

Documentacion de la CLI del framework.

## Archivo

- `tools/specnative.py`

## Comandos disponibles

### Validacion

```bash
python3 ./tools/specnative.py validate
```

Valida que la estructura del framework sea consistente.

### Exportar indice

```bash
python3 ./tools/specnative.py export-index --output exports/index.json
```

Genera un indice JSON de specs y archivos de tareas.

### Exportar trazabilidad

```bash
python3 ./tools/specnative.py export-traceability --output exports/traceability.json
```

Genera un JSON de relaciones entre specs y tareas.

### Instalar en otro repositorio

```bash
python3 ./tools/specnative.py install \
  --target /ruta/al/repo \
  --profile minimal \
  --include-examples \
  --branch specnative/install-v0.3
```

## Regla de seguridad

Antes de copiar archivos, la CLI:

1. valida que el destino sea un repositorio git
2. valida que el worktree este limpio
3. crea una rama dedicada
4. copia solo la estructura seleccionada

## Perfiles

- `minimal`: instala el framework sin tocar el `README.md` existente
  del repo destino
- `full`: intenta instalar tambien el `README.md` de la plantilla

## Notas

- Si un archivo ya existe y no se usa `--force`, la CLI lo omite.
- El objetivo es aislar la adopcion en una rama integrable por merge.
