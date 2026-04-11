# TASKS.md

```toml
artifact_type = "task_file"
initiative = "initiative-name"
spec_id = "SPEC-0001"
owner = "team-name"
state = "todo"
```

## Metadata

- Iniciativa:
- Spec relacionada:
- Owner:
- Estado general: `todo | in_progress | blocked | done`

## Tareas

### TASK-0001 - Titulo

```toml
id = "TASK-0001"
title = "Titulo"
state = "todo"
owner = "team-name"
dependencies = []
expected_files = ["src/example/*"]
close_criteria = "Describe la condicion observable de cierre"
validation = ["pytest tests/example_test.py"]
```

Descripcion humana opcional:

- explicar la responsabilidad de esta tarea
- aclarar riesgos o dependencias no obvias

### TASK-0002 - Titulo

```toml
id = "TASK-0002"
title = "Titulo"
state = "todo"
owner = "team-name"
dependencies = ["TASK-0001"]
expected_files = ["src/example/feature/*"]
close_criteria = "Describe la condicion observable de cierre"
validation = ["manual walkthrough"]
```
