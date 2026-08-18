{{ config(materialized='table') }}

with tickets as (
    select * from {{ ref('stg_support_tickets') }}
),

csat as (
    select * from {{ ref('stg_customer_satisfaction') }}
)

select
    t.ticket_id,
    t.ticket_number,
    t.customer_id,
    t.order_id,
    cast(to_char(t.created_at, 'YYYYMMDD') as integer) as date_key,
    t.issue_category,
    t.priority,
    t.status,
    t.created_at,
    t.resolved_at,
    case
        when t.resolved_at is not null then
            round(extract(epoch from (t.resolved_at - t.created_at)) / 3600.0, 2)
        else null
    end as resolution_time_hours,
    c.survey_id as csat_survey_id,
    c.score as csat_score,
    c.feedback_text as csat_feedback_text,
    c.submitted_at as csat_submitted_at,
    t._ingested_at
from tickets t
left join csat c on t.ticket_id = c.ticket_id
