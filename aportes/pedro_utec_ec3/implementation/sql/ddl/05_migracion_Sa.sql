-- Proyecto LIDIA - migracion segura desde tablas legacy de public a Staging Area.
-- Si la tabla esperada no existe, registra cero filas y continua.
DO $$
DECLARE
    v_run UUID := gen_random_uuid();
    v_rows INTEGER := 0;
BEGIN
    INSERT INTO audit.etl_runs (run_id, fuente, etapa, estado, detalle)
    VALUES (v_run, 'FIRMS', 'load', 'iniciado', '{"origen":"public.focos_calor","destino":"staging.stg_firms"}');

    IF to_regclass('public.focos_calor') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='focos_calor' AND column_name='fecha_adq')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='focos_calor' AND column_name='latitud')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='focos_calor' AND column_name='longitud')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='focos_calor' AND column_name='pais') THEN
        EXECUTE $sql$
            INSERT INTO staging.stg_firms
                (record_hash, natural_key, fecha_adq, latitud, longitud, pais_codigo, raw_payload)
            SELECT md5(concat_ws('|', fecha_adq, latitud, longitud)) || md5(concat_ws('|', fecha_adq, latitud, longitud, 'LIDIA')),
                   concat_ws('|', fecha_adq, latitud, longitud),
                   fecha_adq, latitud, longitud,
                   pais,
                   jsonb_build_object('legacy', true)
            FROM public.focos_calor
            WHERE fecha_adq BETWEEN DATE '2018-01-01' AND DATE '2025-12-31'
              AND pais IN ('URY','ARG','BRA')
            ON CONFLICT (record_hash) DO NOTHING
        $sql$;
        GET DIAGNOSTICS v_rows = ROW_COUNT;
    END IF;

    UPDATE audit.etl_runs
    SET estado='ok', filas_leidas=v_rows, filas_insertadas=v_rows, finalizado_en=NOW()
    WHERE run_id=v_run;
END $$;
