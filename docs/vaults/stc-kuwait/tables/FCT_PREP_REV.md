# FCT_PREP_REV

## Description
Prepaid revenue fact table containing all revenue transactions for prepaid subscribers. This is the primary table for revenue analysis, billing amounts, and financial reporting.

## Keywords
revenue, income, billing, money, sales, arpu, financial, earnings, charges, fees

## Key Metrics
- **BILLAMOUNT**: Primary revenue/billing amount per transaction
- **CONTENT_COST**: Cost of content services
- **CONTENT_REV_PERCENT**: Revenue share percentage

## Common Dimensions
- **APPDATE**: Transaction date (use for time-based analysis)
- **NATIONALITY**: Customer nationality
- **PLAN_NAME**: Subscription plan
- **CONTRACT_CATEGORY**: Customer segment
- **CDR_TYPE**: Type of charge (voice, data, SMS, VAS)

## Columns

- **ACCOUNTID**: VARCHAR2(100) (NULL)
- **APPDATE**: DATE (NULL) — Transaction date
- **BILLAMOUNT**: NUMBER(20,5) (NULL) — Revenue amount in KWD
- **BS_TYPE**: VARCHAR2(5) (NULL)
- **B_BS_TYPE**: VARCHAR2(5) (NULL)
- **B_CONTNRO**: VARCHAR2(40) (NULL)
- **B_CONTRACT_CATEGORY**: VARCHAR2(50) (NULL)
- **B_NATIONALITY**: VARCHAR2(40) (NULL)
- **B_PLAN_ID**: VARCHAR2(20) (NULL)
- **B_PLAN_NAME**: VARCHAR2(100) (NULL)
- **B_PREPOST_PAID**: VARCHAR2(4) (NULL)
- **B_SUBNO**: VARCHAR2(100) (NULL)
- **CALLEDCELLID**: VARCHAR2(100) (NULL)
- **CALLINGCELLID**: VARCHAR2(100) (NULL)
- **CALLTYPE**: VARCHAR2(10) (NULL)
- **CDR_SERIALNO**: VARCHAR2(50) (NULL)
- **CDR_SERIALNO_HASH**: NUMBER (NULL)
- **CDR_TYPE**: VARCHAR2(21) (NULL) — Revenue type: voice, data, sms, vas
- **CHARGINGTYPE**: NUMBER(10,0) (NULL)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: NUMBER (NULL)
- **CONTENT_CATEGORY**: VARCHAR2(50) (NULL)
- **CONTENT_COST**: NUMBER (NULL)
- **CONTENT_INDIRECT_PROVIDER**: VARCHAR2(50) (NULL)
- **CONTENT_NAME**: VARCHAR2(200) (NULL)
- **CONTENT_PROVIDER**: VARCHAR2(50) (NULL)
- **CONTENT_RENTAL**: VARCHAR2(100) (NULL)
- **CONTENT_REV_PERCENT**: NUMBER (NULL)
- **CONTENT_SUB_CATEGORY**: VARCHAR2(50) (NULL)
- **CONTENT_TYPE**: VARCHAR2(28) (NULL)
- **CONTENT_VIVA_RS_PERCNT**: NUMBER (NULL)
- **CONTRACT_CATEGORY**: VARCHAR2(50) (NULL) — Customer segment
- **CONTRNO**: VARCHAR2(40) (NULL)
- **EXEC_DATE**: DATE (NULL)
- **IS_ROAM_REV**: CHAR(1) (NULL) — Roaming revenue flag
- **LOGDATE**: DATE (NULL)
- **NATIONALITY**: VARCHAR2(40) (NULL)
- **PLAN_ID**: VARCHAR2(20) (NULL)
- **PLAN_NAME**: VARCHAR2(100) (NULL)
- **PREPOST_PAID**: VARCHAR2(4) (NULL)
- **SERVICEID**: VARCHAR2(100) (NULL)
- **SUBNO**: VARCHAR2(100) (NULL) — Subscriber number
- **SUBSCRIBERID**: VARCHAR2(100) (NULL)
- **VIRTUAL_IP**: NUMBER (NULL)

## BI Queries

```sql
-- Total revenue by month
SELECT TRUNC(APPDATE, 'MM') AS month, SUM(BILLAMOUNT) AS total_revenue
FROM FCT_PREP_REV
GROUP BY TRUNC(APPDATE, 'MM')
ORDER BY month;

-- Revenue by nationality
SELECT NATIONALITY, SUM(BILLAMOUNT) AS revenue
FROM FCT_PREP_REV
GROUP BY NATIONALITY
ORDER BY revenue DESC;

-- Revenue by CDR type (voice, data, sms)
SELECT CDR_TYPE, SUM(BILLAMOUNT) AS revenue
FROM FCT_PREP_REV
GROUP BY CDR_TYPE;
```

## Usage Notes

- Primary revenue table for prepaid subscribers
- BILLAMOUNT is in KWD (Kuwaiti Dinar)
- Use APPDATE for time-series analysis
- Join with DIM_NATIONALITY for nationality details
