# Evidencias D1 - Modelo Relacional

Este directorio conserva la evidencia liviana para el criterio D1 de la rubrica
EC3 del Proyecto LIDIA. No contiene datos raw ni credenciales.

## Archivos generados

- `d1_ddl_<timestamp>.log`: salida completa de la ejecucion de los DDL
  requeridos. Permite verificar que existen los esquemas `staging`, `dw` y
  `audit`, y que el modelo relacional puede recrearse con los scripts del
  proyecto. Si el usuario UTEC no tiene permisos de roles, `01_roles.sql` se
  omite y queda registrado en el log.
- `d1_validacion_modelo_relacional_<timestamp>.log`: resultado de
  `sql/validation/d1_validacion_modelo_relacional.sql`. Incluye catalogo de
  tablas, claves primarias, claves foraneas, restricciones `CHECK`, `UNIQUE` y
  `NOT NULL`, indices, vistas analiticas, conteos y validaciones de calidad.
- `d1_resumen_ultima_ejecucion.log`: resumen con fecha UTC, prueba de conexion,
  ruta del log DDL y ruta del log de validacion.

## Como interpretar la evidencia

- En las secciones de existencia, el estado esperado es `OK`.
- En validaciones de paises, coordenadas y rangos, `filas_invalidas = 0`
  significa que los datos aceptados cumplen la regla.
- `dw.fact_incendio` debe existir como tabla de hechos principal.
- Las dimensiones esperadas son fecha, ubicacion, clima, precipitacion,
  cobertura vegetal, calidad del aire y estacion meteorologica.
- `dw.dim_calidad_aire` puede tener cero filas si no hay carga real validada de
  CAMS/Open-Meteo Air Quality; eso no invalida el modelo si la dimension existe.
- INUMET debe aparecer solo con `pais_codigo = 'URY'`.
- FIRMS debe usar `brillo_termico`; ese campo no debe interpretarse como
  temperatura del aire.

## Ejecucion

Desde la raiz del proyecto:

```bash
export DATABASE_URL='postgresql://<oculto>
bash scripts/d1_generar_evidencia.sh
```

El script usa `psql`, captura `stdout` y `stderr` con `2>&1`, y guarda la salida
con `tee` dentro de `evidencia/logs`.
