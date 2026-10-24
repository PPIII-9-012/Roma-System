create or replace function public.publicar_circular_psa(
  p_numero_circular text,
  p_mes int,
  p_anio int,
  p_vigencia date,
  p_nombre_archivo text,
  p_cargado_por uuid,
  p_tasas jsonb
)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
  v_circular_id bigint;
begin
  -- Evitar dos circulares para el mismo mes/año
  if exists (
    select 1
    from public.circulares_psa
    where anio = p_anio
      and mes = p_mes
  ) then
    raise exception 'Ya existe una circular publicada para %/%', p_mes, p_anio;
  end if;

  -- Crear la circular
  insert into public.circulares_psa (
    numero_circular,
    mes,
    anio,
    vigencia,
    nombre_archivo,
    cargado_por
  )
  values (
    p_numero_circular,
    p_mes,
    p_anio,
    p_vigencia,
    p_nombre_archivo,
    p_cargado_por
  )
  returning id into v_circular_id;

  -- Crear todas sus tasas
  insert into public.tasas_psa (
    circular_id,
    categoria,
    nombre_linea,
    modelo,
    canal,
    monto_maximo,
    plazo,
    tna,
    aporte_ce,
    cuota_por_1000,
    ltv
  )
  select
    v_circular_id,
    tasa.categoria,
    tasa.nombre_linea,
    tasa.modelo,
    tasa.canal,
    tasa.monto_maximo,
    tasa.plazo,
    tasa.tna,
    tasa.aporte_ce,
    tasa.cuota_por_1000,
    tasa.ltv
  from jsonb_to_recordset(p_tasas) as tasa(
    categoria text,
    nombre_linea text,
    modelo text,
    canal text,
    monto_maximo numeric,
    plazo integer,
    tna numeric,
    aporte_ce numeric,
    cuota_por_1000 numeric,
    ltv numeric
  );

  return v_circular_id;
end;
$$;