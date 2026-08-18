{{ config(materialized='table') }}

with date_series as (
    select
        cast(d as date) as full_date
    from generate_series('2025-01-01'::date, '2027-12-31'::date, '1 day'::interval) as d
)

select
    cast(to_char(full_date, 'YYYYMMDD') as integer) as date_key,
    full_date,
    extract(year from full_date)::integer as year,
    extract(quarter from full_date)::integer as quarter,
    extract(month from full_date)::integer as month,
    to_char(full_date, 'Month') as month_name,
    extract(day from full_date)::integer as day_of_month,
    extract(isodow from full_date)::integer as day_of_week,
    to_char(full_date, 'Day') as day_name,
    case when extract(isodow from full_date) in (6, 7) then true else false end as is_weekend,
    case when full_date = (date_trunc('month', full_date) + interval '1 month - 1 day')::date then true else false end as is_month_end
from date_series
