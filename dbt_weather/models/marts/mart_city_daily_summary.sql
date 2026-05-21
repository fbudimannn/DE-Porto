-- Mart: Daily weather & AQI summary per city
with fact_weather as (
    select * from {{ ref('fact_weather_hourly') }}
),

fact_aq as (
    select * from {{ ref('fact_air_quality') }}
),

cities_dim as (
    select * from {{ ref('dim_cities') }}
),

aggregated as (
    select
        fw.city_key,
        fw.date_key,
        c.city_name,
        c.province,
        c.island,
        fw.observed_at::date as observed_date,

        -- Weather aggregates
        round(avg(fw.temperature_c)::numeric, 1) as avg_temperature_c,
        round(min(fw.temperature_c)::numeric, 1) as min_temperature_c,
        round(max(fw.temperature_c)::numeric, 1) as max_temperature_c,
        round(avg(fw.humidity_pct)::numeric, 0) as avg_humidity_pct,
        round(sum(fw.precipitation_mm)::numeric, 1) as total_precipitation_mm,
        round(avg(fw.wind_speed_kmh)::numeric, 1) as avg_wind_speed_kmh,
        round(max(fw.wind_speed_kmh)::numeric, 1) as max_wind_speed_kmh,
        round(max(fw.uv_index)::numeric, 1) as max_uv_index,

        -- AQI aggregates
        round(avg(fa.pm2_5_ugm3)::numeric, 1) as avg_pm2_5_ugm3,
        round(avg(fa.pm10_ugm3)::numeric, 1) as avg_pm10_ugm3,
        round(avg(fa.aqi_value)::numeric, 0) as avg_aqi_value,
        max(fa.aqi_value) as max_aqi_value
    from fact_weather fw
    inner join fact_aq fa on fw.city_key = fa.city_key and fw.observed_at = fa.observed_at
    inner join cities_dim c on fw.city_key = c.city_key
    group by 1, 2, 3, 4, 5, 6
),

final as (
    select
        *,
        case when total_precipitation_mm > 0 then true else false end as is_rainy_day,
        case
            when max_uv_index >= 11 then 'Extreme'
            when max_uv_index >= 8 then 'Very High'
            when max_uv_index >= 6 then 'High'
            when max_uv_index >= 3 then 'Moderate'
            else 'Low'
        end as uv_risk_level,
        {{ aqi_category('max_aqi_value') }} as worst_aqi_category
    from aggregated
)

select * from final
