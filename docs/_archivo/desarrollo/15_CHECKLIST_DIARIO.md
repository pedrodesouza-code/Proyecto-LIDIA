# 15 â€” Checklist diario

Hoja de cabecera que abrÃ­s cada vez que te sentÃ¡s a trabajar en el proyecto. Hacelo en orden y no salteÃ©s pasos las primeras dos semanas; despuÃ©s se vuelve automÃ¡tico.

## Antes de empezar a programar

- [ ] Abrir terminal en la raÃ­z del proyecto.
- [ ] `git status` â€” Â¿estoy en una rama limpia? Si hay cambios sueltos, decidÃ­ quÃ© hacer con ellos antes de seguir.
- [ ] `git pull origin dev` (o `main` si estÃ¡s en `main`) â€” traer cambios de otros entornos.
- [ ] Si trabajÃ¡s con docker: `docker compose ps` â€” Â¿Postgres y Mongo `healthy`? Si no, `docker compose up -d postgres mongo`.
- [ ] Activar venv: `.venv\Scripts\activate` (Windows) o `source .venv/bin/activate` (Linux).
- [ ] `pip install -r requirements.txt --quiet` â€” por si entraron deps nuevas.

## Al empezar una tarea nueva

- [ ] Crear rama: `git checkout -b feature/<descripcion-corta>` o `fix/<descripcion>`.
- [ ] Anotar en `docs/desarrollo/bitacora/<fecha>.md` quÃ© vas a hacer y por quÃ©.
- [ ] Si la tarea implica una decisiÃ³n tÃ©cnica nueva (no un fix puntual), abrir borrador de ADR en `docs/desarrollo/adr/`.

## Durante el desarrollo

- [ ] Cada 30â€“60 min: `git status` + commit pequeÃ±o con mensaje claro.
- [ ] Si tocÃ¡s SQL: probÃ¡ la query en `psql`/DBeaver antes de meterla al cÃ³digo.
- [ ] Si tocÃ¡s un extractor: corrÃ© el script aislado y mirÃ¡ el archivo de salida.
- [ ] Si tocÃ¡s un transform: validÃ¡ visualmente el parquet (con pandas) antes de cargarlo.
- [ ] Si tocÃ¡s un loader: corrÃ©lo dos veces seguidas para verificar idempotencia.

## Antes de cerrar la sesiÃ³n

- [ ] Correr los tests: `python tests/test_calidad_datos.py`.
- [ ] Si fallaron tests, decidir: arreglo ahora o lo dejo documentado como pendiente.
- [ ] Actualizar `docs/desarrollo/bitacora/<fecha>.md` con: quÃ© hice, quÃ© aprendÃ­, quÃ© quedÃ³ pendiente, prÃ³ximo paso.
- [ ] Si la tarea estÃ¡ completa: PR a `dev`, mergear, borrar rama local y remota.
- [ ] Si la tarea estÃ¡ a medias: commit con mensaje "WIP: ..." y push a tu rama remota (backup).
- [ ] `docker compose stop` si vas a apagar la mÃ¡quina (los datos persisten en el volumen).

## Antes de pushear a `main` (= deploy a UTEC)

- [ ] Todos los tests pasan en local (20/20 PASS).
- [ ] El dashboard levanta sin errores en local.
- [ ] El scheduler corriÃ³ al menos un ciclo completo localmente.
- [ ] El CHANGELOG.md tiene una entrada nueva con la versiÃ³n y los cambios.
- [ ] Tag de versiÃ³n: `git tag -a v1.x.y -m "..."`.
- [ ] `git push origin main --tags`.
- [ ] Conectarte al servidor UTEC y correr `bash scripts/deploy.sh`.
- [ ] Verificar que el dashboard remoto responde y los tests pasan tambiÃ©n allÃ¡.

## Una vez por semana

- [ ] Revisar `docs/desarrollo/bitacora/` y consolidar en `docs/desarrollo/reportes/<semana>.md`.
- [ ] Revisar tamaÃ±o de `data/` y `logs/` en el servidor. Rotar si es necesario.
- [ ] Verificar que el backup del servidor tiene archivos recientes.
- [ ] Probar restore en un entorno aislado (al menos una vez por mes).
- [ ] Revisar ADRs pendientes y completar las que se hayan quedado en borrador.

## Una vez por mes

- [ ] Actualizar dependencias: `pip list --outdated`, evaluar updates conservadores.
- [ ] Revisar logs de errores: Â¿hay patrones recurrentes que justifican un runbook nuevo?
- [ ] Snapshot del repo (clone bare) en un USB externo, por si pasa algo con GitHub.
- [ ] Repasar `README.md`: Â¿sigue describiendo lo que el sistema hace hoy?

## En caso de incidente en producciÃ³n

1. **No entrar en pÃ¡nico.** Los datos estÃ¡n en volÃºmenes persistentes y hay backup diario.
2. Mirar `logs/scheduler.log` y `logs/scheduler.error.log` en el servidor.
3. `docker compose logs <servicio> --tail 100` para el contenedor afectado.
4. Buscar runbook especÃ­fico en `docs/desarrollo/runbooks/`.
5. Si no hay runbook para el sÃ­ntoma: documentÃ¡ el incidente en `docs/desarrollo/bitacora/<fecha>.md` mientras lo resolvÃ©s, y crealo despuÃ©s.
6. Si tenÃ©s que rollback: `git checkout v<version-anterior>` en el servidor y volver a correr `bash scripts/deploy.sh`.

---

**Atajo de "estÃ¡ todo bien"**: si al final del dÃ­a podÃ©s decir "sÃ­" a estas tres preguntas, no te debe el trabajo nada hoy:

1. Â¿Todo lo que cambiÃ© estÃ¡ commiteado y pusheado?
2. Â¿Los tests pasan?
3. Â¿La bitÃ¡cora del dÃ­a tiene al menos 3 lÃ­neas?
