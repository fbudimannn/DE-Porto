-- Clean & cast raw air quality data
with source as (
    select * from {{ source('raw_weather', 'air_quality_hourly') }}
),

renamed as (
    select
        city_name,
        timestamp as observed_at,
        pm10 as pm10_ugm3,
        pm2_5 as pm2_5_ugm3,
        carbon_monoxide as co_ugm3,
        nitrogen_dioxide as no2_ugm3,
        sulphur_dioxide as so2_ugm3,
        ozone as o3_ugm3,
        european_aqi as aqi_value,
        european_aqi_pm2_5 as aqi_pm2_5,
        european_aqi_pm10 as aqi_pm10,
        ingested_at
    from source
)

select * from renamed
