# SINIA-UY - Guia de desarrollo y defensa

Esta carpeta contiene documentacion operativa para moverse por el proyecto,
entenderlo, defenderlo y hacer pruebas controladas.

## Punto de entrada recomendado

Leer en este orden:

1. `01_NAVEGACION_RAPIDA.md`
2. `02_GUIA_ETL_SEPARADA.md`
3. `03_GUIA_MODELO_ER_TABLAS.md`
4. `04_GUIA_DASHBOARD_SEPARADA.md`
5. `05_GUIA_PRUEBAS_TRIBUNAL.md`
6. `06_EVIDENCIA_CDC_EC3.md`
7. `07_AUDITORIA_EC3_Y_TERCERA_ENTREGA.md`
8. `08_EVIDENCIA_DASHBOARD_EC3.md`

## Indice

| Doc | Proposito | Cuando leerlo |
|---|---|---|
| `01_NAVEGACION_RAPIDA.md` | Ubicarse por carpetas, archivos y comandos | Cada vez que abras el proyecto |
| `02_GUIA_ETL_SEPARADA.md` | Entender extract, transform y load | Para defender el pipeline |
| `03_GUIA_MODELO_ER_TABLAS.md` | Entender ER, tablas, claves y tipos | Para defender base de datos |
| `04_GUIA_DASHBOARD_SEPARADA.md` | Explicar cada seccion del dashboard | Para defender la interfaz |
| `05_GUIA_PRUEBAS_TRIBUNAL.md` | Pruebas seguras si modifican datos | Para practicar con el profesor |
| `06_EVIDENCIA_CDC_EC3.md` | Script y lectura de evidencia CDC reproducible | Para cerrar EC3 |
| `07_AUDITORIA_EC3_Y_TERCERA_ENTREGA.md` | Auditoria de cumplimiento, riesgos y pendientes | Para preparar la tercera entrega |
| `08_EVIDENCIA_DASHBOARD_EC3.md` | Verificacion tecnica del dashboard | Para defender la demo Streamlit |
| `10_EXPLICACION_PROYECTO_PASO_A_PASO.md` | Explicacion amplia del proyecto | Para entender el todo |
| `11_SETUP_LOCAL.md` | Levantar el sistema local | Antes de correr dashboard o ETL |
| `12_WORKFLOW_GIT.md` | Flujo de Git | Para versionar cambios |
| `13_DEPLOY_SERVIDOR_UTEC.md` | Deploy en servidor UTEC | Cuando local funcione |
| `14_PLAN_DOCUMENTACION_PARALELA.md` | Plan de documentacion | Para ordenar entregables |
| `15_CHECKLIST_DIARIO.md` | Checklist de trabajo diario | Al iniciar una sesion |
| `16_DEPLOY_STREAMLIT_CLOUD.md` | Deploy en Streamlit Cloud | Para URL publica |
| `17_LAB_DEFENSA_PRUEBAS_TRIBUNAL.md` | Laboratorio SQL detallado | Para simulacro tecnico |
| `18_DEFENSA_DASHBOARD_SECCIONES.md` | Defensa larga del dashboard | Para estudiar preguntas del dashboard |

## Flujo de estudio

```text
Navegacion -> ETL -> Modelo ER -> Dashboard -> Pruebas
```

## Comandos basicos

```bash
python -m pytest tests/test_calidad_datos.py -q
python -m streamlit run dashboard/app.py --server.port 8502
git status --short
```
