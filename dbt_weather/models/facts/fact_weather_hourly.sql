-- Fact table for weather hourly observations
with weather_stg as (
    select * from {{ ref('stg_weather_hourly') }}
),

cities_dim as (
    select * from {{ ref('dim_cities') }}
),

joined as (
    select
        -- Keys
        md5(w.city_name) as city_key,
        to_char(w.observed_at, 'YYYYMMDD')::integer as date_key,
        w.observed_at,

        -- Metrics
        w.temperature_c,
        w.humidity_pct,
        w.apparent_temperature_c,
        w.precipitation_mm,
        w.rain_mm,
        w.wmo_weather_code,
        w.wind_speed_kmh,
        w.wind_gusts_kmh,
        w.uv_index,
        w.pressure_hpa,
        w.cloud_cover_pct,

        -- Derived Columns
        case
            when w.precipitation_mm = 0 then 'None'
            when w.precipitation_mm < 2.5 then 'Light'
            when w.precipitation_mm < 7.6 then 'Moderate'
            else 'Heavy'
        end as rain_intensity,

        case
            when w.wind_speed_kmh < 1 then 0
            when w.wind_speed_kmh < 6 then 1
            when w.wind_speed_kmh < 12 then 2
            when w.wind_speed_kmh < 20 then 3
            when w.wind_speed_kmh < 29 then 4
            when w.wind_speed_kmh < 39 then 5
            else 6
        end as beaufort_scale,

        w.ingested_at
    from weather_stg w
    inner join cities_dim c on w.city_name = c.city_name
)

select * from joined
