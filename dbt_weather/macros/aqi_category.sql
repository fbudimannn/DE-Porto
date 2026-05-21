{% macro aqi_category(aqi_value) %}
case
    when {{ aqi_value }} is null then 'Unknown'
    when {{ aqi_value }} <= 50 then 'Good'
    when {{ aqi_value }} <= 100 then 'Moderate'
    when {{ aqi_value }} <= 150 then 'Unhealthy for Sensitive Groups'
    when {{ aqi_value }} <= 200 then 'Unhealthy'
    when {{ aqi_value }} <= 300 then 'Very Unhealthy'
    else 'Hazardous'
end
{% endmacro %}
