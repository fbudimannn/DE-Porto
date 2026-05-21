-- Clean & cast raw weather data
with source as (
    select * from {{ source('raw_weather', 'weather_hourly') }}
),

renamed as (
    select
        city_name,
        timestamp as observed_at,
        temperature_2m as temperature_c,
        relative_humidity_2m as humidity_pct,
        apparent_temperature as apparent_temperature_c,
        precipitation as precipitation_mm,
        rain as rain_mm,
        weather_code as wmo_weather_code,
        wind_speed_10m as wind_speed_kmh,
        wind_gusts_10m as wind_gusts_kmh,
        uv_index,
        surface_pressure as pressure_hpa,
        cloud_cover as cloud_cover_pct,
        ingested_at
    from source
)

select * from renamed
