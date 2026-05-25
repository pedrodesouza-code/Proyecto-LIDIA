# 14 â€” Plan de documentaciÃ³n de desarrollo en paralelo

> El proyecto ya tiene documentaciÃ³n acadÃ©mica (defensa, informe EC1/EC2, arquitectura). Esta guÃ­a es **distinta**: cubre la documentaciÃ³n de **desarrollo y operaciÃ³n** que vas a ir escribiendo mientras programÃ¡s. Sirve para vos en 3 meses, para el tribunal de defensa, para tu compaÃ±ero y para quien tome el proyecto despuÃ©s.

## 1. Principio rector

**EscribÃ­ la documentaciÃ³n mientras hacÃ©s el cambio, no despuÃ©s.** Cinco minutos al cerrar cada sesiÃ³n vale mÃ¡s que dos dÃ­as de "ahora sÃ­ me siento a documentar" al final.

Tres preguntas para cada documento:

1. Â¿QuiÃ©n lo va a leer? (vos en el futuro, otro dev, el tribunal)
2. Â¿QuÃ© pregunta concreta responde? (no escribir documentaciÃ³n abstracta)
3. Â¿En cuÃ¡nto tiempo el lector se desbloquea? (objetivo: menos de 10 minutos)

Si no podÃ©s responder estas tres, no escribas todavÃ­a.

## 2. Estructura propuesta para `docs/desarrollo/`

```
docs/desarrollo/
â”œâ”€â”€ 00_INDICE.md                           â† ya creado
â”œâ”€â”€ 10_EXPLICACION_PROYECTO_PASO_A_PASO.md â† ya creado
â”œâ”€â”€ 11_SETUP_LOCAL.md                      â† ya creado
â”œâ”€â”€ 12_WORKFLOW_GIT.md                     â† ya creado
â”œâ”€â”€ 13_DEPLOY_SERVIDOR_UTEC.md             â† ya creado
â”œâ”€â”€ 14_PLAN_DOCUMENTACION_PARALELA.md      â† este archivo
â”œâ”€â”€ 15_CHECKLIST_DIARIO.md                 â† ya creado
â”‚
â”œâ”€â”€ adr/                                   â† decisiones de arquitectura
â”‚   â”œâ”€â”€ 0001-elegimos-postgres-y-mongo.md
â”‚   â”œâ”€â”€ 0002-parquet-como-formato-intermedio.md
â”‚   â””â”€â”€ 0003-apscheduler-en-vez-de-airflow.md
â”‚
â”œâ”€â”€ runbooks/                              â† quÃ© hacer cuando algo pase
â”‚   â”œâ”€â”€ etl-fallo-firms.md
â”‚   â”œâ”€â”€ postgres-no-arranca.md
â”‚   â”œâ”€â”€ disco-lleno.md
â”‚   â””â”€â”€ restaurar-backup.md
â”‚
â”œâ”€â”€ bitacora/                              â† log diario de desarrollo
â”‚   â”œâ”€â”€ 2026-05-11.md
â”‚   â”œâ”€â”€ 2026-05-12.md
â”‚   â””â”€â”€ ...
â”‚
â””â”€â”€ reportes/                              â† snapshots periÃ³dicos
    â”œâ”€â”€ 2026-05-semana1-estado.md
    â””â”€â”€ ...
```

## 3. ADR â€” Architecture Decision Records

Una ADR documenta **una decisiÃ³n tÃ©cnica importante**, **por quÃ© se tomÃ³** y **quÃ© se descartÃ³**. Plantilla:

```markdown
# ADR 0001 â€” Elegimos PostgreSQL como Data Warehouse y MongoDB como base operacional

- **Estado**: aceptada
- **Fecha**: 2026-02-15
- **Decisores**: Rafael Q.

## Contexto
Necesitamos almacenar 3 tipos de datos: estructurados con esquema estable (focos,
meteo, calidad de aire), logs de ejecuciÃ³n con campos variables, y alertas con
estructura semi-libre. Una sola base obliga a comprometer algo.

## DecisiÃ³n
Usar PostgreSQL para datos analÃ­ticos y MongoDB para datos operacionales/logs.

## Alternativas consideradas
1. **Solo PostgreSQL** con columnas JSONB para lo flexible.
   - Descartada: ETL mÃ¡s complejo, pierdes Ã­ndices nativos sobre JSON anidado,
     no aporta diferenciaciÃ³n tÃ©cnica frente al requisito de la materia.
2. **Solo MongoDB**.
   - Descartada: queries analÃ­ticas con JOINs son verbose y lentas en Mongo.
3. **Snowflake / BigQuery**.
   - Descartada: alcance acadÃ©mico, costo, complejidad operativa innecesaria.

## Consecuencias
- (+) Cada motor hace lo que mejor sabe.
- (+) La defensa puede justificar la elecciÃ³n con datos concretos.
- (âˆ’) Mantenimiento doble (dos backups, dos sets de credenciales).
- (âˆ’) ETL debe escribir a dos destinos â€” se mitiga con `etl/load/load_postgres.py`
  y `etl/load/load_mongo.py` separados e idempotentes.
```

**Reglas para ADRs**:

- Una por archivo, numerada.
- Cortas (1 pÃ¡gina).
- Inmutables â€” si revisÃ¡s la decisiÃ³n, no editÃ¡s la ADR vieja: agregÃ¡s una nueva con `Estado: supersedes 0001`.

**ADRs que ya podrÃ­as escribir hoy con lo que ya hay implementado:**

1. PostgreSQL + MongoDB (justificaciÃ³n de complementariedad).
2. Parquet como formato intermedio (vs CSV).
3. APScheduler en vez de Airflow (alcance acadÃ©mico).
4. Streamlit en vez de Dash o React + API (simplicidad).
5. UPSERT por clave natural para idempotencia.
6. Docker Compose en vez de instalaciÃ³n nativa.
7. Tres roles Postgres con mÃ­nimo privilegio.
8. Pesos del Ã­ndice de riesgo (0.25/0.30/0.20/0.25) â€” referencia INIA.

## 4. Runbooks â€” quÃ© hacer cuando algo pasa

Un runbook es una **receta operativa para un incidente puntual**. Plantilla:

```markdown
# Runbook â€” ETL de FIRMS falla con timeout

## SÃ­ntoma
`extract_firms.py` aborta con `requests.exceptions.Timeout` o
`urllib3.exceptions.ReadTimeoutError`.

## Causa probable
- La API de FIRMS estÃ¡ saturada o caÃ­da temporalmente.
- La MAP_KEY excediÃ³ el lÃ­mite diario (5000 transacciones/10min).
- Red del servidor sin acceso a `firms.modaps.eosdis.nasa.gov`.

## DiagnÃ³stico (en orden)
1. Probar la URL directamente:
   ```
   curl -I "https://firms.modaps.eosdis.nasa.gov/api/area/csv/<MAP_KEY>/VIIRS_SNPP_NRT/-82,-56,-34,13/1"
   ```
   Si responde 200, la API estÃ¡ OK; si 401, MAP_KEY invÃ¡lida; si 5xx, FIRMS down.

2. Ver cuÃ¡ntas transacciones llevamos hoy:
   ```
   curl "https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=<...>"
   ```

3. Revisar el Ãºltimo log:
   ```
   tail -20 logs/sinia_$(date +%F).json
   ```

## SoluciÃ³n
- Si es timeout temporal: reintentar en 10 minutos (el scheduler lo harÃ¡ solo).
- Si se excediÃ³ el lÃ­mite: esperar al reset (ventana mÃ³vil de 10 min).
- Si MAP_KEY invÃ¡lida: regenerar en https://firms.modaps.eosdis.nasa.gov/api/map_key/
  y actualizar `docker/.env` y `config/.env`. Reiniciar el scheduler.

## CÃ³mo prevenir
- Cachear extracciones para no rehacer si la data ya estÃ¡ en `data/raw/`.
- Implementar backoff exponencial en `extract_firms.py`.
- Reducir el bbox a Uruguay si el sudamericano es demasiado.
```

**Runbooks prioritarios para SINIA-UY**:

| # | Runbook | Probabilidad de necesitarlo |
|---|---------|------------------------------|
| 1 | ETL de FIRMS falla con timeout | Alta â€” APIs satelitales fluctÃºan |
| 2 | Postgres no arranca despuÃ©s de reboot | Media |
| 3 | Mongo replica con autenticaciÃ³n fallida | Baja |
| 4 | Disco del servidor casi lleno | Media â€” logs crecen |
| 5 | Restaurar backup tras corrupciÃ³n de datos | Baja |
| 6 | Dashboard muestra "No data" en producciÃ³n | Media |
| 7 | Scheduler dejÃ³ de correr | Media |
| 8 | Test de calidad falla en CI | Alta â€” cada vez que cambies transform |

## 5. BitÃ¡cora diaria

Un archivo por dÃ­a de trabajo, formato libre pero con esta estructura mÃ­nima:

```markdown
# 2026-05-11

## QuÃ© hice
- LevantÃ© Postgres y Mongo localmente con Docker.
- CorrÃ­ la primera carga del ETL.
- 20/20 tests PASS.
- EmpecÃ© a escribir la guÃ­a de desarrollo en docs/desarrollo/.

## QuÃ© aprendÃ­
- El init de Postgres solo corre en el primer arranque. Si edito el schema,
  tengo que aplicarlo con ALTER o `docker compose down -v`.
- `data/raw/` pesa ~50 MB despuÃ©s de extraer toda la histÃ³rica â†’ confirmado que
  estÃ¡ bien excluido del `.gitignore`.

## QuÃ© me trabÃ³
- El healthcheck de Mongo tardÃ³ 45s la primera vez. PensÃ© que estaba roto.

## PrÃ³ximo paso
- Inicializar git y subir a GitHub.
- Pedir datos del servidor UTEC al docente.
```

**Por quÃ© importa**: cuando llegues a defensa o a un final de proyecto, tener 60 entradas como esta te da material concreto para responder "Â¿quÃ© desafÃ­os enfrentaste?", "Â¿cÃ³mo evolucionÃ³ tu decisiÃ³n sobre X?", "Â¿cuÃ¡nto te llevÃ³ implementar Y?".

## 6. Reportes semanales / por sprint

Cada viernes (o cierre de iteraciÃ³n), un archivo con:

- Lo que se completÃ³.
- Lo que quedÃ³ pendiente y por quÃ©.
- Decisiones tomadas (linkeadas a ADRs).
- Riesgos identificados.
- MÃ©tricas (tests passing, lÃ­neas de cÃ³digo, tablas con datos).

Esto sirve para informes parciales que pide la materia.

## 7. Docstrings dentro del cÃ³digo

Cada funciÃ³n pÃºblica del ETL deberÃ­a tener un docstring corto:

```python
def calcular_indice_riesgo(temp: float, humedad: float, viento: float, sequia: float) -> tuple[float, str]:
    """Calcula el Ã­ndice de riesgo de incendio.

    Suma ponderada de 4 componentes normalizados a [0,1].
    Pesos segÃºn metodologÃ­a INIA: temp=0.25, humedad=0.30, viento=0.20, sequia=0.25.

    Args:
        temp: Componente de temperatura [0,1].
        humedad: Componente de humedad [0,1].
        viento: Componente de viento [0,1].
        sequia: Componente de sequÃ­a [0,1].

    Returns:
        Tupla (indice [0,1], nivel ['bajo','moderado','alto','muy_alto']).

    Raises:
        ValueError: si algÃºn componente estÃ¡ fuera de [0,1].
    """
```

Para clases SQL, comentarios `COMMENT ON TABLE` y `COMMENT ON COLUMN` (ya estÃ¡n en `02_schema.sql`, mantenlos al dÃ­a si agregÃ¡s campos).

## 8. Mantener `README.md` actualizado

El `README.md` raÃ­z es lo primero que ve cualquiera (incluido el tribunal). Mantenelo asÃ­:

- Una lÃ­nea sobre quÃ© hace el proyecto.
- Levantamiento rÃ¡pido (3 comandos).
- Link al doc `00_INDICE.md` para detalle.
- Tabla de tests y estado.

Cuando cambies algo grande (nueva tabla, nueva API, nuevo deploy), actualizÃ¡ el README en el mismo commit. **No dejes el README desincronizado del cÃ³digo.**

## 9. Material para la defensa acadÃ©mica (`docs/`)

La carpeta `docs/` actual ya tiene:

- `DEFENSA.md`
- `ARQUITECTURA.md`
- `FUENTES_Y_DATOS.md`
- `INFORME_EC1.md`
- `PROYECTO_FINAL_EC1_EC2.md`
- `CHECKLIST_CUMPLIMIENTO_EC1_EC2.md`
- `figures/*.svg`

**No mezcles**: la documentaciÃ³n acadÃ©mica vive en `docs/` y la operativa/desarrollo en `docs/desarrollo/`. Cuando termines, vas a tener:

```
docs/
â”œâ”€â”€ (defensa acadÃ©mica)
â””â”€â”€ desarrollo/
    â””â”€â”€ (operaciÃ³n, runbooks, ADRs, bitÃ¡cora)
```

Si la defensa pide "documentaciÃ³n de desarrollo", linkeÃ¡s `docs/desarrollo/00_INDICE.md`.

## 10. Calendario sugerido para escribir la doc

Si vas a defender en, digamos, 6 semanas:

| Semana | Foco de documentaciÃ³n |
|--------|----------------------|
| 1 | BitÃ¡cora diaria. Crear `00_INDICE.md` (ya hecho). Empezar primeras 3 ADRs (las decisiones obvias). |
| 2 | Setup local + git workflow ya documentados. Empezar 2 runbooks (FIRMS, Postgres). |
| 3 | Deploy al servidor + runbook de backup. Tercera tanda de ADRs. |
| 4 | Reporte semanal. Refinar README. Docstrings en funciones clave. |
| 5 | Ensayo de defensa con la doc: Â¿alguien externo levanta el proyecto siguiendo solo los docs? |
| 6 | Pulido final. PDF de informe. Checklist EC2. |

## 11. Reglas para que la documentaciÃ³n no se pudra

1. **Una sola fuente de verdad**: si el dato estÃ¡ en `config/settings.py`, no lo repitas hardcodeado en la doc â€” linkeÃ¡ al archivo.
2. **Si lo cambiÃ¡s en el cÃ³digo, abrÃ­ la doc en el mismo commit.**
3. **Si la doc miente, es peor que no tener doc.** BorrÃ¡ lo que ya no aplica.
4. **Las fechas se ponen explÃ­citas**: "Ãºltima actualizaciÃ³n: 2026-05-11" arriba de los docs que cambian seguido.
5. **EvitÃ¡ copy-paste de comandos sin testear.** ProbÃ¡ cada comando que pongas.

## 12. Convenciones de estilo

- Markdown estÃ¡ndar (CommonMark). Sin extensiones rebuscadas.
- Bloques de cÃ³digo con lenguaje declarado (` ```bash`, ` ```sql`, ` ```python `).
- Tablas para enumeraciones tÃ©cnicas (puertos, variables, errores).
- Listas para pasos imperativos.
- Negrita para conceptos clave que el lector necesita recordar.
- Sin emojis en docs tÃ©cnicos.

---

**PrÃ³ximo paso:** [15_CHECKLIST_DIARIO.md](15_CHECKLIST_DIARIO.md) â€” el checklist que abrÃ­s cada dÃ­a.
