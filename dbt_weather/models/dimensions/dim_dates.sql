-- Dimension table for dates using PostgreSQL generate_series
with date_series as (
    select generate_series(
        '2026-01-01'::date,
        '2027-12-31'::date,
        '1 day'::interval
    )::date as date_day
),

date_dimension as (
    select
        to_char(date_day, 'YYYYMMDD')::integer as date_key,
        date_day,
        extract(year from date_day)::integer as year,
        extract(month from date_day)::integer as month,
        extract(day from date_day)::integer as day,
        extract(quarter from date_day)::integer as quarter,
        to_char(date_day, 'Month') as month_name,
        to_char(date_day, 'TMMonth') as month_name_id, -- Indonesian month name
        to_char(date_day, 'Day') as day_name,
        extract(isodow from date_day)::integer as day_of_week,
        case when extract(isodow from date_day) in (6, 7) then true else false end as is_weekend
    from date_series
)

select * from date_dimension
