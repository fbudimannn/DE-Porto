-- Test that temperatures are within realistic limits (-10C to 55C)
select
    city_key,
    observed_at,
    temperature_c
from {{ ref('fact_weather_hourly') }}
where temperature_c < -10.0 or temperature_c > 55.0
