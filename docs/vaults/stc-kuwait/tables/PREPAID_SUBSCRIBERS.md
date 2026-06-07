# PREPAID_SUBSCRIBERS

Prepaid subscriber master table containing core subscriber information.

## Columns

**SUBSCRIBER_ID**: NUMBER (Primary Key)
Unique identifier for each prepaid subscriber.

**MSISDN**: VARCHAR2(20) (NOT NULL)
Mobile Subscriber Integrated Services Digital Network Number (phone number).

**STATUS**: VARCHAR2(20)
Current status of the subscriber (ACTIVE, SUSPENDED, INACTIVE, etc.).

**ACTIVATION_DATE**: DATE
Date when the subscriber was activated.

**PLAN_NAME**: VARCHAR2(50)
Name of the current prepaid plan.

## Business Context

This table stores the core subscriber information for prepaid customers. It is the primary reference for subscriber-level queries and is typically joined with usage and billing tables for comprehensive analysis.

## Sample Queries

- Count active subscribers: `SELECT COUNT(*) FROM PREPAID_SUBSCRIBERS WHERE STATUS = 'ACTIVE'`
- New activations by month: `SELECT TRUNC(ACTIVATION_DATE, 'MM'), COUNT(*) FROM PREPAID_SUBSCRIBERS GROUP BY TRUNC(ACTIVATION_DATE, 'MM')`
