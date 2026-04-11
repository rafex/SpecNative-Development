# TASKS.md

```toml
artifact_type = "task_file"
initiative = "authentication"
spec_id = "SPEC-AUTH-0001"
owner = "team-auth"
state = "in_progress"
```

## Metadata

- Iniciativa: authentication
- Spec relacionada: SPEC-AUTH-0001
- Owner: team-auth
- Estado general: `in_progress`

## Tareas

### TASK-AUTH-0001 - Definir modelo de sesion

- Estado: `done`
- Owner: team-auth
- Dependencias: `none`
- Archivos esperados: `src/auth/session.*`
- Criterio de cierre: existe contrato de sesion y validacion unitaria
- Validacion: tests unitarios de creacion y expiracion

### TASK-AUTH-0002 - Implementar middleware de autorizacion

- Estado: `in_progress`
- Owner: team-auth
- Dependencias: `TASK-AUTH-0001`
- Archivos esperados: `src/auth/middleware.*`
- Criterio de cierre: rutas protegidas rechazan requests no autenticadas
- Validacion: test de integracion sobre rutas protegidas

### TASK-AUTH-0003 - Documentar setup operativo

- Estado: `todo`
- Owner: platform
- Dependencias: `TASK-AUTH-0002`
- Archivos esperados: `agents/COMMANDS.md`, `README.md`
- Criterio de cierre: el setup local y variables requeridas estan
  documentadas
- Validacion: walkthrough manual de bootstrap
