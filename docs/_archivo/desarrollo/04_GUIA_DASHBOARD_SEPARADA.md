# Guia separada del dashboard

Este archivo explica solo el dashboard.

## Archivos

```text
dashboard/app.py
dashboard/db.py
```

`app.py` dibuja la interfaz.

`db.py` trae datos: primero intenta PostgreSQL y si falla usa Parquet.

## Secciones

| Seccion | Que muestra | Que defiende |
|---|---|---|
| Resumen General | KPIs, mapa, alertas | Vision ejecutiva |
| Focos de Calor | FIRMS, FRP, confianza, mapa | Hechos satelitales |
| Indice de Riesgo | Riesgo calculado | Transformacion meteorologica |
| Calidad del Aire | PM10, PM2.5, OMS | Agregacion CAMS |
| Analisis de Riesgo | Dias criticos y patrones | Analitica con vistas |
| Comparativo por Pais | URY/BRA/ARG | Alcance regional |
| Tiempo Real | NRT y forecast | Operacion reciente |
| Fuentes y Datos Crudos | Archivos y columnas crudas | Trazabilidad |

## Preguntas clave

El dashboard no calcula todo. Visualiza y filtra datos que vienen del ETL, PostgreSQL, vistas y `dashboard/db.py`.

Si PostgreSQL falla, usa Parquet cuando existe.

Los mapas pueden limitar puntos por rendimiento, pero los KPIs usan conteos reales.
