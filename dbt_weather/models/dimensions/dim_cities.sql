-- Dimension table for cities
with source as (
    select * from {{ ref('city_metadata') }}
)

select
    md5(city_name) as city_key,
    city_name,
    lat,
    lon,
    province,
    island,
    timezone,
    elevation_m,
    population
from source
