# Evidencia dashboard EC3

Este documento resume la verificacion tecnica del dashboard Streamlit para la
tercera entrega.

## 1. Archivo principal

El dashboard esta implementado en:

```text
dashboard/app.py
dashboard/db.py
```

`dashboard/app.py` contiene la interfaz, filtros, KPIs y visualizaciones.
`dashboard/db.py` contiene la capa de acceso a datos, usando PostgreSQL como
fuente principal y Parquet como fallback.

## 2. Verificacion local

Comando usado:

```bash
python -m streamlit run dashboard/app.py --server.port 8502 --server.headless true
```

Resultado HTTP:

```text
http://localhost:8502 -> 200
```

Lectura para defensa:

> El dashboard levanta correctamente y responde por HTTP. Esto prueba que la
> aplicacion Streamlit esta disponible para demo local.

## 3. Verificacion con Streamlit AppTest

Se ejecuto una prueba de renderizado con `streamlit.testing.v1.AppTest`.

Resultado observado:

```text
exceptions: 0
title_count: 2
subheader_count: 5
metric_count: 4
```

Lectura para defensa:

> La pantalla inicial renderiza sin excepciones y muestra elementos de interfaz:
> titulos, subtitulos y metricas. Las consultas llegan a `dashboard/db.py` y el
> dashboard puede construir la vista inicial.

## 4. Captura visual

Se genero una captura real del dashboard renderizado:

```text
reports/dashboard_evidencia_ultimo.png
```

La captura muestra:

- barra lateral con secciones del dashboard;
- titulo principal del sistema;
- explicacion del problema;
- integracion de las fuentes NASA FIRMS, Open-Meteo, CAMS, CHIRPS y MODIS.

Lectura para defensa:

> La evidencia visual confirma que el dashboard no solo responde por HTTP, sino
> que renderiza la pantalla inicial con contenido funcional y navegacion por
> secciones.

## 5. Optimizacion para demo

Antes, el mapa podia intentar renderizar hasta `100.000` focos en la pantalla
inicial. Eso era correcto analiticamente, pero pesado para una demo con navegador
headless o equipo limitado.

Se ajusto la muestra visual a:

```text
MAX_FOCOS_MAPA = 25000
```

Importante:

- los KPIs no pierden exactitud;
- los totales siguen usando `COUNT(*)` en PostgreSQL;
- solo se acota la muestra usada por mapas, tablas y graficos de detalle;
- la muestra se prioriza por `potencia_radiativa`, mostrando los focos mas
  intensos primero.

Frase de defensa:

> El dashboard separa conteo analitico de visualizacion. Para los KPIs usamos
> agregaciones reales sobre toda la tabla. Para mapas usamos una muestra acotada,
> porque renderizar millones de puntos no aporta claridad visual y afecta la
> experiencia de usuario.

## 6. Secciones del dashboard

La interfaz incluye:

- Resumen General.
- Focos de Calor.
- Indice de Riesgo.
- Calidad del Aire.
- Analisis de Riesgo.
- Comparativo por Pais.
- Tiempo Real.
- Fuentes y Datos Crudos.

Estas secciones estan explicadas en detalle en:

```text
docs/desarrollo/18_DEFENSA_DASHBOARD_SECCIONES.md
```

## 7. Comando recomendado para la defensa

```bash
python -m streamlit run dashboard/app.py --server.port 8502
```

Luego abrir:

```text
http://localhost:8502
```

## 8. Que mostrar ante el tribunal

1. Abrir el dashboard.
2. Mostrar el selector de secciones.
3. Explicar los filtros de periodo y pais.
4. Mostrar los KPIs principales.
5. Explicar que el total viene de PostgreSQL.
6. Mostrar mapa o serie temporal.
7. Cambiar de pais para demostrar interactividad.
8. Ir a "Fuentes y Datos Crudos" para mostrar datos antes de transformacion.

## 9. Riesgo residual

Microsoft Edge headless quedo en pantalla de carga de Streamlit, por eso se uso
el navegador integrado para obtener la captura final. Si el tribunal pide demo
en vivo, abrir el dashboard en navegador normal y esperar a que carguen KPIs y
graficos antes de navegar por secciones.
