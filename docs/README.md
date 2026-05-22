# Documentacion vigente - SINIA-UY

Fecha de organizacion: 2026-05-22.

Esta carpeta queda ordenada para preparar y defender EC3. Los documentos vigentes estan en la raiz de `docs/`. El material historico, borradores, guias antiguas y documentos de desarrollo se movieron a `docs/_archivo/` para evitar redundancia y contradicciones.

## Leer primero

1. `UNIFICACION_EC1_EC2_EC3_FOCO_EC3_2026-05-22.md`
2. `GUIA_DEFENSA_TECNICA_COMPLETA_2026-05-22.md`
3. `CIERRE_ENTREGA_2026-05-22.md`
4. `ESTADO_ACTUAL_PROYECTO_2026-05-22.md`

## Documentos vigentes

| Documento | Uso |
|---|---|
| `UNIFICACION_EC1_EC2_EC3_FOCO_EC3_2026-05-22.md` | Une las tres consignas y enfoca la defensa EC3 |
| `GUIA_DEFENSA_TECNICA_COMPLETA_2026-05-22.md` | Guia principal para estudiar codigo, bases, ETL, dashboard y conceptos |
| `CIERRE_ENTREGA_2026-05-22.md` | Estado de cierre operativo y validaciones ejecutadas |
| `ESTADO_ACTUAL_PROYECTO_2026-05-22.md` | Fuente de verdad del alcance actual |
| `ENTREGA_EC3_IMPLEMENTACION.md` | Documento formal de cumplimiento EC3 |
| `MATRIZ_CUMPLIMIENTO_CONSIGNA_2026.md` | Mapa requisito -> evidencia |
| `GUIA_DEFENSA_FINAL.md` | Resumen oral corto para defensa |
| `CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md` | Relacion preguntas analiticas -> consultas -> dashboard |
| `SLA_Y_RENDIMIENTO.md` | SLA y evidencia de rendimiento |
| `REPLICACION_Y_SHARDING.md` | Replicacion, sharding simulado y trade-offs |
| `DESPLIEGUE_HIBRIDO.md` | Lectura correcta de local, cloud y UTEC |
| `SEGURIDAD_BACKUP_GOBERNANZA.md` | Seguridad, backup y gobernanza |
| `ANEXO_A_DDL_MYSQL.md` | Anexo de modelo dimensional SQL |
| `ANEXO_B_JSON_SCHEMA_MONGODB.md` | Anexo de modelo documental MongoDB |

## Material archivado

`docs/_archivo/` conserva evidencia historica y documentos de trabajo. No usar esos archivos como estado actual salvo que se cite explicitamente como antecedente.

Motivo:

- algunos reflejan cortes anteriores, por ejemplo 2026-05-15;
- otros describen alcances anteriores que ya no son vigentes;
- varios son borradores o guias internas redundantes;
- mantenerlos fuera de la raiz evita confundir la defensa EC3.

## Fuente de verdad actual

Alcance vigente:

- `ARG`, `BRA`, `CHL`, `URY`;
- 36 puntos de monitoreo;
- Uruguay cubierto por 19 departamentos;
- tests: 20 PASS / 0 FAIL;
- FIRMS procesado: 1.946.361 focos.
