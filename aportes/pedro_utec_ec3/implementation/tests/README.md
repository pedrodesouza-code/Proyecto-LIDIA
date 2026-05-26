# Tests EC3

Los tests son pequenos y no descargan datos. Verifican cuantitativamente
validacion/rechazos, idempotencia por hashes y CDC con alta/modificacion.

```bash
cd implementation
python -m pytest -q tests
```

La prueba integral con PostgreSQL requiere inicializar el DDL y configurar
archivos locales mediante `config/.env`; los conteos reales deben registrarse
en `evidencia/logs/` antes de la defensa.
