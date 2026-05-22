# Laboratorio de defensa: pruebas controladas del sistema

Esta guÃ­a sirve para entrenar la defensa frente a una banca exigente. La idea es
poder mostrar quÃ© pasa si se modifican datos, si se insertan duplicados, si hay
valores invÃ¡lidos, si PostgreSQL no estÃ¡ disponible, y cÃ³mo se recupera el
sistema sin improvisar.

## Regla de oro

Antes de tocar datos reales, trabajar siempre dentro de una transacciÃ³n:

```sql
BEGIN;
-- pruebas
ROLLBACK;
```

`ROLLBACK` deshace todo lo que se hizo dentro de la transacciÃ³n. Si se quiere
guardar el cambio, se usa `COMMIT`, pero para defensa conviene usar `ROLLBACK`.

## ConexiÃ³n rÃ¡pida a PostgreSQL

Desde Git Bash:

```bash
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" \
  -h localhost -p 5432 -U postgres -d sinia_uy
```

Verificar tablas principales:

```sql
\dt
```

Ver vistas:

```sql
\dv
```

Ver cantidad de registros:

```sql
SELECT 'focos_calor' AS tabla, COUNT(*) FROM focos_calor
UNION ALL
SELECT 'meteo_diario', COUNT(*) FROM meteo_diario
UNION ALL
SELECT 'calidad_aire_diario', COUNT(*) FROM calidad_aire_diario
UNION ALL
SELECT 'precipitacion_mensual', COUNT(*) FROM precipitacion_mensual
UNION ALL
SELECT 'cobertura_vegetal', COUNT(*) FROM cobertura_vegetal;
```

## Prueba 1: demostrar integridad de coordenadas

Objetivo: mostrar que la base no acepta coordenadas imposibles.

```sql
BEGIN;

INSERT INTO puntos_monitoreo (nombre, pais, latitud, longitud)
VALUES ('Punto_Invalido', 'URY', -999, -56.0);

ROLLBACK;
```

Resultado esperado: PostgreSQL rechaza el registro por el `CHECK` de latitud.

Defensa oral:

> La restricciÃ³n evita cargar coordenadas fÃ­sicamente imposibles. Esto protege
> la calidad desde la propia base de datos, no solo desde Python.

## Prueba 2: demostrar dominio de paÃ­ses

Objetivo: mostrar por quÃ© usamos cÃ³digos normalizados.

```sql
BEGIN;

INSERT INTO paises_referencia (codigo_iso3, codigo_iso2, nombre)
VALUES ('URUGUAY', 'UY', 'Uruguay largo');

ROLLBACK;
```

Resultado esperado: falla porque `codigo_iso3` es `CHAR(3)`.

Defensa oral:

> Se usa ISO alpha-3 para evitar variantes como Uruguay, UY, URU o texto libre.

## Prueba 3: demostrar idempotencia en focos_calor

Objetivo: intentar insertar dos veces el mismo foco.

```sql
BEGIN;

INSERT INTO focos_calor (
    fecha_adq, hora_adq_hhmm, latitud, longitud, pais,
    potencia_radiativa, confianza_raw, confianza_num, satelite,
    instrumento, dia_noche, es_diurno
)
VALUES (
    '2024-01-01', 1230, -30.91000, -55.55000, 'URY',
    15.500, 'h', 3, 'TEST_SAT',
    'VIIRS', 'D', TRUE
);

INSERT INTO focos_calor (
    fecha_adq, hora_adq_hhmm, latitud, longitud, pais,
    potencia_radiativa, confianza_raw, confianza_num, satelite,
    instrumento, dia_noche, es_diurno
)
VALUES (
    '2024-01-01', 1230, -30.91000, -55.55000, 'URY',
    15.500, 'h', 3, 'TEST_SAT',
    'VIIRS', 'D', TRUE
);

ROLLBACK;
```

Resultado esperado: el segundo `INSERT` falla por la restricciÃ³n `UNIQUE`.

Defensa oral:

> La clave natural evita duplicados. Un foco se identifica por ubicaciÃ³n, fecha,
> hora y satÃ©lite.

## Prueba 4: demostrar upsert controlado en focos_calor

Objetivo: mostrar cÃ³mo el ETL actualiza un dato existente en vez de duplicarlo.

```sql
BEGIN;

INSERT INTO focos_calor (
    fecha_adq, hora_adq_hhmm, latitud, longitud, pais,
    potencia_radiativa, confianza_raw, confianza_num, satelite,
    instrumento, dia_noche, es_diurno
)
VALUES (
    '2024-01-02', 1010, -30.91000, -55.55000, 'URY',
    10.000, 'n', 2, 'TEST_SAT',
    'VIIRS', 'D', TRUE
);

INSERT INTO focos_calor (
    fecha_adq, hora_adq_hhmm, latitud, longitud, pais,
    potencia_radiativa, confianza_raw, confianza_num, satelite,
    instrumento, dia_noche, es_diurno
)
VALUES (
    '2024-01-02', 1010, -30.91000, -55.55000, 'URY',
    99.000, 'h', 3, 'TEST_SAT',
    'VIIRS', 'D', TRUE
)
ON CONFLICT (latitud, longitud, fecha_adq, hora_adq_hhmm, satelite)
DO UPDATE SET
    potencia_radiativa = EXCLUDED.potencia_radiativa,
    confianza_num = EXCLUDED.confianza_num;

SELECT fecha_adq, hora_adq_hhmm, latitud, longitud, potencia_radiativa, confianza_num
FROM focos_calor
WHERE satelite = 'TEST_SAT'
  AND fecha_adq = '2024-01-02';

ROLLBACK;
```

Resultado esperado: queda un solo registro con `potencia_radiativa = 99.000`.

Defensa oral:

> Esto demuestra CDC/upsert: si el registro ya existe y cambiÃ³ un valor, se
> actualiza; si no cambiÃ³, no se duplica.

## Prueba 5: demostrar rango del Ã­ndice de riesgo

Objetivo: intentar insertar un Ã­ndice invÃ¡lido.

```sql
BEGIN;

SELECT id FROM puntos_monitoreo WHERE nombre = 'Rivera';

INSERT INTO meteo_diario (
    fecha, id_punto, tipo_dato,
    temperature_2m_max, relative_humidity_2m_min,
    wind_speed_10m_max, et0_fao_evapotranspiration,
    riesgo_temp, riesgo_humedad, riesgo_viento, riesgo_sequia,
    indice_riesgo, nivel_riesgo
)
VALUES (
    '2026-01-01',
    (SELECT id FROM puntos_monitoreo WHERE nombre = 'Rivera'),
    'historico',
    30, 40, 20, 5,
    0.5, 0.5, 0.5, 0.5,
    1.5, 'alto'
);

ROLLBACK;
```

Resultado esperado: falla porque `indice_riesgo` debe estar entre 0 y 1.

Defensa oral:

> El Ã­ndice estÃ¡ normalizado. La base impide guardar riesgos fuera del rango
> matemÃ¡tico definido por el modelo.

## Prueba 6: demostrar dominio de nivel_riesgo

Objetivo: intentar insertar una categorÃ­a no permitida.

```sql
BEGIN;

INSERT INTO meteo_diario (
    fecha, id_punto, tipo_dato,
    indice_riesgo, nivel_riesgo
)
VALUES (
    '2026-01-02',
    (SELECT id FROM puntos_monitoreo WHERE nombre = 'Rivera'),
    'historico',
    0.8, 'peligrosisimo'
);

ROLLBACK;
```

Resultado esperado: falla por el `CHECK` de `nivel_riesgo`.

Defensa oral:

> Usamos dominio controlado: bajo, moderado, alto y muy_alto. Eso evita errores
> semÃ¡nticos en consultas y dashboard.

## Prueba 7: demostrar calidad de aire y lÃ­mite OMS

Objetivo: insertar un dÃ­a de PM10 alto y ver cÃ³mo aparece en la vista de alertas.

```sql
BEGIN;

INSERT INTO calidad_aire_diario (
    fecha, id_punto,
    pm10_media, pm10_max, pm10_p95,
    pm2_5_media, pm2_5_max,
    horas_validas, supera_oms_pm10, nivel_pm10
)
VALUES (
    '2026-01-03',
    (SELECT id FROM puntos_monitoreo WHERE nombre = 'Rivera'),
    120.0, 180.0, 170.0,
    40.0, 60.0,
    24, TRUE, 'alerta'
);

SELECT *
FROM v_alertas_calidad_aire
WHERE fecha = '2026-01-03';

ROLLBACK;
```

Resultado esperado: la vista muestra el dÃ­a como alerta.

Defensa oral:

> CAMS crudo viene horario, el ETL lo agrega a diario y marca si supera el
> umbral OMS de PM10. La vista consume esa lÃ³gica para alertas.

## Prueba 8: demostrar vista de riesgo actual

Objetivo: ver el Ãºltimo riesgo disponible por punto.

```sql
SELECT *
FROM v_riesgo_actual
ORDER BY indice_riesgo DESC;
```

Defensa oral:

> La vista encapsula una consulta analÃ­tica: Ãºltimo registro histÃ³rico por
> punto. El dashboard no necesita recalcular esta lÃ³gica.

## Prueba 9: demostrar vista de dÃ­as crÃ­ticos

Objetivo: ver dÃ­as con riesgo alto o muy alto.

```sql
SELECT *
FROM v_dias_criticos
ORDER BY fecha DESC
LIMIT 10;
```

Defensa oral:

> Esta vista transforma registros diarios por punto en una lectura ejecutiva:
> quÃ© dÃ­as fueron crÃ­ticos, cuÃ¡ntos puntos y paÃ­ses estuvieron afectados.

## Prueba 10: demostrar fallback del dashboard

Objetivo: explicar comportamiento si PostgreSQL no estÃ¡ disponible.

En `dashboard/db.py`, cada funciÃ³n intenta primero PostgreSQL y si falla usa
Parquet desde `data/processed/`.

Defensa oral:

> El sistema prioriza PostgreSQL como fuente analÃ­tica, pero mantiene Parquet
> como respaldo procesado. Esto permite que el dashboard funcione en entornos
> sin base activa, como Streamlit Cloud o una demo local limitada.

## Comandos Python seguros para verificar calidad

Ejecutar tests:

```bash
python -m pytest tests/test_calidad_datos.py -q
```

Resultado esperado:

```text
20 passed
```

Generar reporte JSON limpio:

```bash
python tests/test_calidad_datos.py
```

Resultado esperado:

```text
Resultado: 20 PASS / 0 FAIL
```

## Preguntas trampa y respuestas

### Si modifico un dato manualmente, se rompe el sistema?

Depende del dato. Si viola una restricciÃ³n, PostgreSQL lo rechaza. Si es vÃ¡lido
pero cambia una mÃ©trica, las vistas lo reflejan automÃ¡ticamente.

### Por quÃ© hay validaciones en Python y tambiÃ©n en SQL?

Porque son capas distintas. Python limpia antes de cargar. SQL protege la
integridad final aunque alguien intente insertar datos manualmente.

### QuÃ© pasa si cargo dos veces el mismo archivo?

El modelo usa claves naturales y `ON CONFLICT`. El registro no se duplica. Si
cambiÃ³, se actualiza; si es igual, queda sin cambio.

### Por quÃ© usar ROLLBACK en defensa?

Porque permite demostrar errores y comportamientos sin ensuciar la base real.

### CuÃ¡l es la prueba mÃ¡s fuerte para base de datos?

Mostrar una restricciÃ³n fallando, un upsert funcionando, una vista reflejando el
cambio y luego hacer `ROLLBACK`.

## Secuencia recomendada para practicar frente al tribunal

1. Mostrar conteos de tablas.
2. Mostrar ER verbalmente: puntos como dimensiÃ³n, tablas ambientales como hechos.
3. Ejecutar una prueba de restricciÃ³n invÃ¡lida.
4. Ejecutar una prueba de duplicado.
5. Ejecutar una prueba de upsert.
6. Mostrar una vista analÃ­tica.
7. Ejecutar tests de calidad.
8. Cerrar explicando idempotencia, CDC y fallback a Parquet.
