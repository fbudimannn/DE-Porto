-- Mart: Active and historical poor air quality alert events (AQI > 100)
with fact_aq as (
    select * from {{ ref('fact_air_quality') }}
),

cities_dim as (
    select * from {{ ref('dim_cities') }}
)

select
    fa.city_key,
    c.city_name,
    c.province,
    c.island,
    fa.observed_at,
    fa.aqi_value,
    fa.aqi_category,
    fa.pm2_5_ugm3,
    fa.pm10_ugm3,
    fa.co_ugm3,
    fa.no2_ugm3,
    -- Simple alert classification
    case
        when fa.aqi_value > 300 then 'Critical - Hazardous'
        when fa.aqi_value > 200 then 'Severe - Very Unhealthy'
        else 'Warning - Unhealthy'
    end as alert_level
from fact_aq fa
inner join cities_dim c on fa.city_key = c.city_key
where fa.aqi_value > 100
order by fa.observed_at desc, fa.aqi_value desc
