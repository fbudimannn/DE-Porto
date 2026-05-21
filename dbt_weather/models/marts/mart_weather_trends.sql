-- Mart: Rolling weather and AQI trends using window functions
with fact_weather as (
    select * from {{ ref('fact_weather_hourly') }}
),

fact_aq as (
    select * from {{ ref('fact_air_quality') }}
),

cities_dim as (
    select * from {{ ref('dim_cities') }}
),

joined as (
    select
        fw.city_key,
        c.city_name,
        fw.observed_at,
        fw.temperature_c,
        fw.humidity_pct,
        fa.aqi_value,
        fw.precipitation_mm
    from fact_weather fw
    inner join fact_aq fa on fw.city_key = fa.city_key and fw.observed_at = fa.observed_at
    inner join cities_dim c on fw.city_key = c.city_key
),

trends as (
    select
        *,
        -- 24-hour rolling average temperature
        round(avg(temperature_c) over (
            partition by city_key
            order by observed_at
            rows between 23 preceding and current row
        )::numeric, 2) as rolling_avg_temp_24h,

        -- 24-hour rolling average AQI
        round(avg(aqi_value) over (
            partition by city_key
            order by observed_at
            rows between 23 preceding and current row
        )::numeric, 1) as rolling_avg_aqi_24h,

        -- 24-hour total precipitation
        round(sum(precipitation_mm) over (
            partition by city_key
            order by observed_at
            rows between 23 preceding and current row
        )::numeric, 2) as rolling_sum_precip_24h,

        -- Lag to compare with temperature from exactly 24 hours ago
        lag(temperature_c, 24) over (
            partition by city_key
            order by observed_at
        ) as temp_24h_ago
    from joined
),

final as (
    select
        *,
        round((temperature_c - temp_24h_ago)::numeric, 2) as temp_change_24h
    from trends
)

select * from final
order by city_name, observed_at desc
