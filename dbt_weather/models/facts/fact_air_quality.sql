-- Fact table for air quality hourly observations
with aq_stg as (
    select * from {{ ref('stg_air_quality') }}
),

cities_dim as (
    select * from {{ ref('dim_cities') }}
),

joined as (
    select
        -- Keys
        md5(a.city_name) as city_key,
        to_char(a.observed_at, 'YYYYMMDD')::integer as date_key,
        a.observed_at,

        -- Metrics
        a.pm10_ugm3,
        a.pm2_5_ugm3,
        a.co_ugm3,
        a.no2_ugm3,
        a.so2_ugm3,
        a.o3_ugm3,
        a.aqi_value,
        a.aqi_pm2_5,
        a.aqi_pm10,

        -- Derived Columns
        {{ aqi_category('a.aqi_value') }} as aqi_category,
        case when a.aqi_value > 100 then true else false end as is_aqi_alert,

        a.ingested_at
    from aq_stg a
    inner join cities_dim c on a.city_name = c.city_name
)

select * from joined
