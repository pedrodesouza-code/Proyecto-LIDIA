"""
===============================================================================
SINIA-UY - Creacion inicial de bases de datos en Postgres y Mongo nativos
===============================================================================

Este script prepara la infraestructura de bases para dos escenarios:

1. Instalacion local / nativa:
   - Crea la base PostgreSQL si no existe
   - Aplica roles, esquema, indices, vistas y seed
   - Crea usuarios y colecciones de Mongo

2. Servidor remoto con base ya asignada (por ejemplo grp03db):
   - Usa la base existente sin crear otra
   - Aplica solo esquema/indices/vistas/seed en Postgres
   - Crea solo las colecciones del proyecto en Mongo
   - No toca colecciones ajenas, por ejemplo 'eventos'

Uso:
    python scripts/crear_bases_datos.py
    python scripts/crear_bases_datos.py --solo-postgres
    python scripts/crear_bases_datos.py --solo-mongo
    python scripts/crear_bases_datos.py --reset-postgres
    python scripts/crear_bases_datos.py --reset-mongo
    python scripts/crear_bases_datos.py --base-existente

Credenciales:
    El script intenta leer config/.env. Si no encuentra las contrasenas o
    faltan datos, los pide por consola y sigue.
===============================================================================
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
ENV_PATH = RAIZ / "config" / ".env"

try:
    from dotenv import load_dotenv

    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
        print(f"[info] config/.env cargado desde {ENV_PATH}")
    else:
        print("[info] no hay config/.env (se pediran credenciales por consola)")
except ImportError:
    print("[aviso] python-dotenv no instalado - corre: pip install python-dotenv")


def banner(texto: str) -> None:
    print()
    print("=" * 78)
    print(f"  {texto}")
    print("=" * 78)


def paso(n: str, texto: str) -> None:
    print(f"\n[paso {n}] {texto}")


def ok(texto: str) -> None:
    print(f"  [OK] {texto}")


def err(texto: str) -> None:
    print(f"  [ERROR] {texto}")


def pedir(prompt: str, default: str = "", secreto: bool = False) -> str:
    sufijo = f" [{default}]" if default else ""
    if secreto:
        valor = getpass.getpass(f"  {prompt}{sufijo}: ")
    else:
        valor = input(f"  {prompt}{sufijo}: ").strip()
    return valor or default


def _pedir_host_puerto(prefijo: str, default_host: str, default_port: str) -> tuple[str, int]:
    host = os.getenv(f"{prefijo}_HOST", default_host) or pedir("Host", default_host)
    port = int(os.getenv(f"{prefijo}_PORT", default_port) or pedir("Puerto", default_port))
    return host, port


def _aplicar_scripts_sql(cur, scripts: list[Path], base_existente: bool = False) -> bool:
    for script in scripts:
        if not script.exists():
            err(f"No encontrado: {script}")
            return False
        print(f"\n  -> aplicando {script.relative_to(RAIZ)}")
        try:
            sql_text = script.read_text(encoding="utf-8")
            if base_existente and script.name == "02_schema.sql":
                # En servidores asignados suele no haber permiso para CREATE EXTENSION.
                sql_text = sql_text.replace(
                    'CREATE EXTENSION IF NOT EXISTS "pgcrypto";',
                    "-- pgcrypto omitido en modo base existente",
                )
            if base_existente and script.name == "04_vistas.sql":
                # En servidores asignados no siempre existen roles locales del proyecto.
                lineas = []
                for linea in sql_text.splitlines():
                    if "TO sinia_readonly" in linea:
                        lineas.append(f"-- grant omitido en modo base existente: {linea}")
                    else:
                        lineas.append(linea)
                sql_text = "\n".join(lineas)
            cur.execute(sql_text)
            ok(f"{script.name} aplicado")
        except Exception as exc:
            err(f"Error en {script.name}: {exc}")
            return False
    return True


def _verificar_postgres(cur, base_existente: bool) -> bool:
    tablas_requeridas = [
        "focos_calor",
        "meteo_diario",
        "calidad_aire_diario",
        "precipitacion_mensual",
        "cobertura_vegetal",
        "paises_referencia",
        "puntos_monitoreo",
        "etl_ejecuciones",
    ]
    vistas_requeridas = [
        "v_riesgo_actual",
        "v_riesgo_historico",
        "v_focos_resumen_diario",
        "v_alertas_calidad_aire",
        "v_dias_criticos",
        "v_forecast_riesgo",
        "v_riesgo_por_pais",
        "v_focos_por_pais_mes",
    ]

    cur.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
        ORDER BY table_name
        """
    )
    tablas_presentes = [r[0] for r in cur.fetchall()]

    cur.execute(
        """
        SELECT table_name FROM information_schema.views
        WHERE table_schema='public'
        ORDER BY table_name
        """
    )
    vistas_presentes = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*) FROM puntos_monitoreo")
    n_puntos = cur.fetchone()[0]

    n_tablas = len(tablas_presentes)
    n_vistas = len(vistas_presentes)
    faltan_tablas = [t for t in tablas_requeridas if t not in tablas_presentes]
    faltan_vistas = [v for v in vistas_requeridas if v not in vistas_presentes]

    roles: list[str] = []
    if not base_existente:
        cur.execute(
            """
            SELECT rolname FROM pg_roles
            WHERE rolname LIKE 'sinia%'
            ORDER BY rolname
            """
        )
        roles = [r[0] for r in cur.fetchall()]

    print(f"  Tablas:            {n_tablas} (esperado: 8)")
    print(f"  Vistas:            {n_vistas} (esperado: 8)")
    print(f"  Puntos cargados:   {n_puntos} (esperado: > 0)")
    if faltan_tablas:
        print(f"  Tablas faltantes:  {', '.join(faltan_tablas)}")
    if faltan_vistas:
        print(f"  Vistas faltantes:  {', '.join(faltan_vistas)}")
    if base_existente:
        print("  Roles/usuarios:    omitido en modo base existente")
    else:
        print(f"  Roles/usuarios:    {', '.join(roles) if roles else '(ninguno)'}")

    return not faltan_tablas and not faltan_vistas and n_puntos > 0


def setup_postgres(reset: bool = False, base_existente: bool = False) -> bool:
    banner("PostgreSQL - setup")
    try:
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        err("psycopg2 no instalado. Corre: pip install psycopg2-binary")
        return False

    pg_host, pg_port = _pedir_host_puerto("PG", "localhost", "5432")
    pg_db = os.getenv("PG_DATABASE", "sinia_uy") or "sinia_uy"

    if base_existente:
        paso("PG-1", "Credenciales de la base existente")
        print("  (Modo servidor remoto: usa PG_DATABASE tal cual, por ejemplo grp03db)")
        if reset:
            err("El modo --base-existente no permite --reset-postgres por seguridad.")
            return False

        pg_user = os.getenv("PG_USER", "") or pedir("Usuario", "postgres")
        pg_pass = os.getenv("PG_PASSWORD", "") or pedir(
            f"Password de {pg_user}", secreto=True
        )

        paso("PG-2", f"Conectando a {pg_host}:{pg_port}/{pg_db} como {pg_user}")
        try:
            conn = psycopg2.connect(
                host=pg_host,
                port=pg_port,
                user=pg_user,
                password=pg_pass,
                dbname=pg_db,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            ok("Conexion exitosa")
        except psycopg2.OperationalError as exc:
            err(f"No pude conectar: {exc}")
            print("\n  Verifica:")
            print("  - host, puerto y base de PostgreSQL asignados por UTEC")
            print("  - usuario y contrasena")
            print("  - acceso de red al servidor")
            return False

        paso("PG-3", f"Aplicando esquema SQL sobre '{pg_db}'")
        scripts = [
            RAIZ / "sql" / "ddl" / "02_schema.sql",
            RAIZ / "sql" / "ddl" / "03_indices.sql",
            RAIZ / "sql" / "ddl" / "04_vistas.sql",
            RAIZ / "sql" / "dml" / "01_seed_puntos.sql",
        ]

        if not _aplicar_scripts_sql(cur, scripts, base_existente=True):
            cur.close()
            conn.close()
            return False

        paso("PG-4", "Verificando estado de la base")
        ok_postgres = _verificar_postgres(cur, base_existente=True)
        cur.close()
        conn.close()
        if ok_postgres:
            ok("PostgreSQL listo")
            return True
        err("Algo no quedo como esperado - revisa los mensajes arriba")
        return False

    paso("PG-1", "Credenciales del superusuario de PostgreSQL")
    print("  (Normalmente: usuario='postgres', con la contrasena que elegiste.)")

    pg_super_user = os.getenv("PG_SUPERUSER", "postgres") or pedir("Superusuario", "postgres")
    pg_super_pass = os.getenv("PG_SUPERPASS", "") or pedir(
        f"Password de {pg_super_user}", secreto=True
    )

    paso("PG-2", f"Conectando a {pg_host}:{pg_port} como {pg_super_user}")
    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            user=pg_super_user,
            password=pg_super_pass,
            dbname="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        ok("Conexion exitosa")
    except psycopg2.OperationalError as exc:
        err(f"No pude conectar: {exc}")
        print("\n  Verifica:")
        print("  - PostgreSQL esta corriendo")
        print("  - el puerto es correcto (default 5432)")
        print("  - el usuario y contrasena estan bien")
        return False

    if reset:
        paso("PG-3", f"RESET - eliminando base '{pg_db}' si existe")
        confirma = input(f"  Seguro que queres borrar {pg_db}? (escribi SI): ").strip()
        if confirma == "SI":
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(pg_db)))
            ok(f"Base '{pg_db}' eliminada")
        else:
            print("  Cancelado.")

    paso("PG-4", f"Creando base '{pg_db}' si no existe")
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (pg_db,))
    if cur.fetchone():
        ok(f"La base '{pg_db}' ya existe")
    else:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(pg_db)))
        ok(f"Base '{pg_db}' creada")

    cur.close()
    conn.close()

    paso("PG-5", f"Aplicando scripts SQL sobre '{pg_db}'")
    scripts = [
        RAIZ / "sql" / "ddl" / "01_roles.sql",
        RAIZ / "sql" / "ddl" / "02_schema.sql",
        RAIZ / "sql" / "ddl" / "03_indices.sql",
        RAIZ / "sql" / "ddl" / "04_vistas.sql",
        RAIZ / "sql" / "dml" / "01_seed_puntos.sql",
    ]

    conn = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        user=pg_super_user,
        password=pg_super_pass,
        dbname=pg_db,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    if not _aplicar_scripts_sql(cur, scripts, base_existente=False):
        cur.close()
        conn.close()
        return False

    paso("PG-6", "Verificando estado de la base")
    ok_postgres = _verificar_postgres(cur, base_existente=False)
    cur.close()
    conn.close()

    if ok_postgres:
        ok("PostgreSQL listo")
        return True

    err("Algo no quedo como esperado - revisa los mensajes arriba")
    return False


def _build_mongo_uri(
    host: str,
    port: int,
    database: str,
    user: str = "",
    password: str = "",
    auth_source: str = "",
) -> str:
    if user and password:
        origen = auth_source or database
        return f"mongodb://{user}:{password}@{host}:{port}/{database}?authSource={origen}"
    return f"mongodb://{host}:{port}/"


def setup_mongo(reset: bool = False, base_existente: bool = False) -> bool:
    banner("MongoDB - setup")
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
    except ImportError:
        err("pymongo no instalado. Corre: pip install pymongo")
        return False

    mg_host, mg_port = _pedir_host_puerto("MONGO", "localhost", "27017")
    mg_db = os.getenv("MONGO_DATABASE", "sinia_uy") or "sinia_uy"
    mg_auth_source = os.getenv("MONGO_AUTH_SOURCE", mg_db) or mg_db

    paso("MG-1", "Credenciales del Mongo")
    if base_existente:
        print("  (Modo servidor remoto: usa la base asignada y preserva colecciones ajenas.)")
        if reset:
            err("El modo --base-existente no permite --reset-mongo por seguridad.")
            return False

        mg_user = os.getenv("MONGO_USER", "") or pedir("Usuario de la base Mongo", "")
        mg_pass = os.getenv("MONGO_PASSWORD", "") or (
            pedir(f"Password de {mg_user}", secreto=True) if mg_user else ""
        )
        usar_auth = bool(mg_user and mg_pass)
        uri = _build_mongo_uri(
            host=mg_host,
            port=mg_port,
            database=mg_db,
            user=mg_user,
            password=mg_pass,
            auth_source=mg_auth_source,
        )
    else:
        print("  (Instalacion nativa Windows: por defecto Mongo no pide autenticacion)")
        usar_auth = pedir("Tu Mongo requiere autenticacion? (s/n)", "n").lower().startswith("s")
        if usar_auth:
            mg_root_user = os.getenv("MONGO_ROOT_USER", "") or pedir(
                "Usuario admin de Mongo", "mongo_admin"
            )
            mg_root_pass = os.getenv("MONGO_ROOT_PASS", "") or pedir(
                f"Password de {mg_root_user}", secreto=True
            )
            uri = f"mongodb://{mg_root_user}:{mg_root_pass}@{mg_host}:{mg_port}/?authSource=admin"
        else:
            uri = f"mongodb://{mg_host}:{mg_port}/"

    paso("MG-2", f"Conectando a {mg_host}:{mg_port}")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        ok("Conexion exitosa")
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        err(f"No pude conectar: {exc}")
        print("\n  Verifica:")
        print("  - MongoDB esta corriendo")
        print("  - el puerto es correcto")
        print("  - si tiene auth: las credenciales y authSource son correctos")
        return False

    if reset:
        paso("MG-3", f"RESET - eliminando base '{mg_db}'")
        confirma = input(f"  Seguro que queres borrar {mg_db}? (escribi SI): ").strip()
        if confirma == "SI":
            client.drop_database(mg_db)
            ok(f"Base '{mg_db}' eliminada")
        else:
            print("  Cancelado.")

    paso("MG-4", f"Creando usuarios y colecciones en '{mg_db}'")
    db = client[mg_db]

    mg_etl_user = os.getenv("MONGO_USER", "sinia_etl_user")
    mg_etl_pass = os.getenv("MONGO_PASSWORD", "sinia_etl_2026")
    mg_dash_user = "sinia_dash_user"
    mg_dash_pass = os.getenv("MONGO_DASH_PASSWORD", "sinia_dash_2026")

    def crear_usuario(usuario: str, password: str, rol: str) -> None:
        try:
            db.command(
                "createUser",
                usuario,
                pwd=password,
                roles=[{"role": rol, "db": mg_db}],
            )
            ok(f"Usuario '{usuario}' creado (rol={rol})")
        except OperationFailure as exc:
            if "already exists" in str(exc):
                try:
                    db.command("updateUser", usuario, pwd=password)
                    ok(f"Usuario '{usuario}' ya existia - password actualizado")
                except OperationFailure as exc2:
                    print(f"  [aviso] no pude actualizar '{usuario}': {exc2}")
            else:
                print(f"  [aviso] no pude crear '{usuario}': {exc}")

    if usar_auth and not base_existente:
        crear_usuario(mg_etl_user, mg_etl_pass, "readWrite")
        crear_usuario(mg_dash_user, mg_dash_pass, "read")
    elif not usar_auth:
        print("  (omitiendo creacion de usuarios - Mongo esta sin auth)")
    else:
        print("  (omitiendo createUser - se asume que UTEC ya entrego el usuario)")

    for coleccion in ["ejecuciones_etl", "alertas", "focos_snapshots"]:
        if coleccion not in db.list_collection_names():
            db.create_collection(coleccion)
            ok(f"Coleccion '{coleccion}' creada")
        else:
            ok(f"Coleccion '{coleccion}' ya existe")

    paso("MG-5", "Verificando estado de la base")
    colecciones = sorted(db.list_collection_names())
    print(f"  Base:        {mg_db}")
    print(f"  Colecciones: {', '.join(colecciones)}")
    if "eventos" in colecciones:
        print("  Coleccion 'eventos': detectada y preservada (no se modifica)")

    if usar_auth and not base_existente:
        try:
            usuarios_info = db.command("usersInfo")
            usuarios = [u["user"] for u in usuarios_info.get("users", [])]
            print(f"  Usuarios:    {', '.join(usuarios) if usuarios else '(ninguno)'}")
        except OperationFailure as exc:
            print(f"  [aviso] no pude listar usuarios: {exc}")

    client.close()
    ok("MongoDB listo")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crea las bases de datos SINIA-UY en Postgres y Mongo nativos."
    )
    parser.add_argument("--solo-postgres", action="store_true", help="Solo aplica Postgres")
    parser.add_argument("--solo-mongo", action="store_true", help="Solo aplica Mongo")
    parser.add_argument("--reset-postgres", action="store_true", help="DROP + recrear Postgres")
    parser.add_argument("--reset-mongo", action="store_true", help="dropDatabase en Mongo")
    parser.add_argument(
        "--base-existente",
        action="store_true",
        help="Usa una base ya creada en servidor remoto (sin crear DB ni usuarios).",
    )
    args = parser.parse_args()

    hacer_pg = not args.solo_mongo
    hacer_mg = not args.solo_postgres

    banner("SINIA-UY - creacion de bases de datos")
    print(f"Raiz del proyecto: {RAIZ}")
    print(f"Archivo .env:      {ENV_PATH}{' (existe)' if ENV_PATH.exists() else ' (no existe)'}")
    if args.base_existente:
        print("Modo:              base existente / servidor remoto")

    pg_ok = True
    mg_ok = True

    if hacer_pg:
        pg_ok = setup_postgres(
            reset=args.reset_postgres,
            base_existente=args.base_existente,
        )

    if hacer_mg:
        mg_ok = setup_mongo(
            reset=args.reset_mongo,
            base_existente=args.base_existente,
        )

    banner("Resumen")
    if hacer_pg:
        print(f"  PostgreSQL: {'OK' if pg_ok else 'FALLO'}")
    if hacer_mg:
        print(f"  MongoDB:    {'OK' if mg_ok else 'FALLO'}")

    if (not hacer_pg or pg_ok) and (not hacer_mg or mg_ok):
        print("\nTodo listo. Proximo paso: correr el ETL.")
        print("  python etl/extract/extract_meteo.py")
        print("  python etl/transform/transform_meteo.py")
        print("  python etl/load/load_postgres.py")
        print("  python etl/load/load_mongo.py")
        return 0

    print("\nHubo errores - revisa los mensajes arriba.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
