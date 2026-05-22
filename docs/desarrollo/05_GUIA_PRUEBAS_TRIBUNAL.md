# Guia separada de pruebas para el tribunal

Usa esta guia para practicar cuando el profesor quiera tocar datos o buscar errores.

## Regla principal

```sql
BEGIN;
-- prueba
ROLLBACK;
```

`ROLLBACK` deshace todo.

## Pruebas seguras

### Coordenada invalida

```sql
BEGIN;
INSERT INTO puntos_monitoreo (nombre, pais, latitud, longitud)
VALUES ('Punto_Invalido', 'URY', -999, -56.0);
ROLLBACK;
```

Debe fallar por `CHECK`.

### Duplicado en focos

Insertar dos veces el mismo foco debe fallar por `UNIQUE`, salvo que se use `ON CONFLICT`.

Clave:

```text
latitud + longitud + fecha_adq + hora_adq_hhmm + satelite
```

### Indice fuera de rango

Insertar `indice_riesgo = 1.5` debe fallar.

### Nivel invalido

Insertar `nivel_riesgo = 'peligroso'` debe fallar.

Valores validos:

```text
bajo
moderado
alto
muy_alto
```

## Tests Python

```bash
python -m pytest tests/test_calidad_datos.py -q
```

Resultado esperado:

```text
20 passed
```

Para ejemplos SQL mas largos:

```text
docs/desarrollo/17_LAB_DEFENSA_PRUEBAS_TRIBUNAL.md
```
