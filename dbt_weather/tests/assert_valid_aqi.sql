-- Test that AQI values are non-negative and within European AQI range (0 to 500)
select
    city_key,
    observed_at,
    aqi_value
from {{ ref('fact_air_quality') }}
where aqi_value < 0 or aqi_value > 500
