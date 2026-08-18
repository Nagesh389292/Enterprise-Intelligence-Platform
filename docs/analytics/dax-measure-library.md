# Enterprise DAX Measure Library & Metric Dictionary

## 1. Overview & Measure Table Organization

All DAX measures in the NexaCore Enterprise Semantic Layer are organized into specialized **Measure Tables** (prefixed with `_`) to maintain clean navigation and separation from physical data columns in Power BI reports.

### Display Folders Hierarchy
```text
├── _Sales Measures
│   ├── Core Financial Totals
│   ├── Time Intelligence (YTD / PY / YoY)
│   └── Order Averages & Rates
├── _Customer Measures
│   ├── Customer Counts
│   └── CSAT & Experience
├── _Inventory Measures
│   ├── Stock Quantities
│   └── Stockout Risk Metrics
└── _Operations Measures
    ├── Equipment Telemetry
    └── Maintenance & Downtime
```

---

## 2. Commercial & Financial Sales Measures

### 1. `[Net Revenue]`
- **Description**: Total actual revenue net of line item discounts. Must reconcile to exact control total.
- **Display Folder**: `_Sales Measures\Core Financial Totals`
- **Format String**: `$#,##0.00`
- **Expected Baseline Value**: `$18,274,577.78`
- **DAX Formula**:
```dax
Net Revenue = 
SUM(fact_orders[total_amount])
```

---

### 2. `[Gross Revenue]`
- **Description**: Total undiscounted revenue generated across all order items before applying discounts.
- **Display Folder**: `_Sales Measures\Core Financial Totals`
- **Format String**: `$#,##0.00`
- **Expected Baseline Value**: `$19,330,862.00`
- **DAX Formula**:
```dax
Gross Revenue = 
SUM(fact_order_items[total_price]) + SUM(fact_order_items[discount_amount])
```

---

### 3. `[Total Discounts]`
- **Description**: Aggregate value of promotional and order line discounts.
- **Display Folder**: `_Sales Measures\Core Financial Totals`
- **Format String**: `$#,##0.00`
- **Expected Baseline Value**: `$1,056,284.22`
- **DAX Formula**:
```dax
Total Discounts = 
SUM(fact_order_items[discount_amount])
```

---

### 4. `[Units Sold]`
- **Description**: Total physical quantity of products sold across all orders.
- **Display Folder**: `_Sales Measures\Core Financial Totals`
- **Format String**: `#,##0`
- **Expected Baseline Value**: `193,309`
- **DAX Formula**:
```dax
Units Sold = 
SUM(fact_order_items[quantity])
```

---

### 5. `[Total Orders]`
- **Description**: Distinct count of completed and processed customer order header records.
- **Display Folder**: `_Sales Measures\Core Financial Totals`
- **Format String**: `#,##0`
- **Expected Baseline Value**: `10,000`
- **DAX Formula**:
```dax
Total Orders = 
COUNTROWS(fact_orders)
```

---

### 6. `[Average Order Value (AOV)]`
- **Description**: Average net revenue generated per order header.
- **Display Folder**: `_Sales Measures\Order Averages & Rates`
- **Format String**: `$#,##0.00`
- **Expected Baseline Value**: `$1,827.46`
- **DAX Formula**:
```dax
Average Order Value = 
DIVIDE([Net Revenue], [Total Orders], 0)
```

---

### 7. `[Revenue YTD]`
- **Description**: Year-To-Date cumulative net revenue based on calendar year starting Jan 1.
- **Display Folder**: `_Sales Measures\Time Intelligence`
- **Format String**: `$#,##0.00`
- **DAX Formula**:
```dax
Revenue YTD = 
TOTALYTD([Net Revenue], dim_date[date_key])
```

---

### 8. `[Revenue Prior Year (PY)]`
- **Description**: Net revenue generated in the equivalent period of the previous calendar year.
- **Display Folder**: `_Sales Measures\Time Intelligence`
- **Format String**: `$#,##0.00`
- **DAX Formula**:
```dax
Revenue Prior Year = 
CALCULATE(
    [Net Revenue],
    SAMEPERIODLASTYEAR(dim_date[date_key])
)
```

---

### 9. `[YoY Revenue Growth %]`
- **Description**: Percentage change in net revenue compared to the prior year period.
- **Display Folder**: `_Sales Measures\Time Intelligence`
- **Format String**: `0.00%`
- **DAX Formula**:
```dax
YoY Revenue Growth % = 
VAR _Current = [Net Revenue]
VAR _Prior = [Revenue Prior Year]
RETURN
DIVIDE(_Current - _Prior, _Prior, 0)
```

---

### 10. `[30-Day Rolling Net Revenue]`
- **Description**: Moving sum of net revenue over the trailing 30-day window.
- **Display Folder**: `_Sales Measures\Time Intelligence`
- **Format String**: `$#,##0.00`
- **DAX Formula**:
```dax
30-Day Rolling Net Revenue = 
CALCULATE(
    [Net Revenue],
    DATESINPERIOD(dim_date[date_key], MAX(dim_date[date_key]), -30, DAY)
)
```

---

## 3. Customer Experience & CSAT Measures

### 11. `[Total Customers]`
- **Description**: Total count of unique active customers registered in the platform.
- **Display Folder**: `_Customer Measures\Customer Counts`
- **Format String**: `#,##0`
- **Expected Baseline Value**: `1,000`
- **DAX Formula**:
```dax
Total Customers = 
DISTINCTCOUNT(dim_customer[customer_id])
```

---

### 12. `[Average CSAT Score]`
- **Description**: Mean customer satisfaction score recorded across post-ticket survey responses (Scale 1 to 5).
- **Display Folder**: `_Customer Measures\CSAT & Experience`
- **Format String**: `0.00`
- **Expected Baseline Value**: `4.15`
- **DAX Formula**:
```dax
Average CSAT Score = 
AVERAGE(fact_support_tickets[csat_score])
```

---

### 13. `[Total Support Tickets]`
- **Description**: Total volume of customer support tickets created.
- **Display Folder**: `_Customer Measures\CSAT & Experience`
- **Format String**: `#,##0`
- **Expected Baseline Value**: `2,500`
- **DAX Formula**:
```dax
Total Support Tickets = 
COUNTROWS(fact_support_tickets)
```

---

### 14. `[CSAT Response Rate %]`
- **Description**: Percentage of support tickets that received a CSAT survey rating response.
- **Display Folder**: `_Customer Measures\CSAT & Experience`
- **Format String**: `0.0%`
- **DAX Formula**:
```dax
CSAT Response Rate % = 
VAR _Responded = CALCULATE(COUNTROWS(fact_support_tickets), NOT(ISBLANK(fact_support_tickets[csat_score])))
VAR _Total = COUNTROWS(fact_support_tickets)
RETURN
DIVIDE(_Responded, _Total, 0)
```

---

## 4. Supply Chain & Inventory Measures

### 15. `[Current Inventory On Hand]`
- **Description**: Semi-additive total inventory units on hand evaluated at the latest available snapshot date in filter context.
- **Display Folder**: `_Inventory Measures\Stock Quantities`
- **Format String**: `#,##0`
- **Expected Baseline Value**: `184,520` (as of latest snapshot)
- **DAX Formula**:
```dax
Current Inventory On Hand = 
CALCULATE(
    SUM(fact_inventory_snapshot[quantity_on_hand]),
    LASTDATE(dim_date[date_key])
)
```

---

### 16. `[Items Below Reorder Point]`
- **Description**: Count of warehouse-product snapshot combinations where current stock is below the safety reorder point.
- **Display Folder**: `_Inventory Measures\Stockout Risk Metrics`
- **Format String**: `#,##0`
- **Expected Baseline Value**: `87`
- **DAX Formula**:
```dax
Items Below Reorder Point = 
CALCULATE(
    COUNTROWS(fact_inventory_snapshot),
    fact_inventory_snapshot[quantity_on_hand] <= fact_inventory_snapshot[reorder_point],
    LASTDATE(dim_date[date_key])
)
```

---

### 17. `[Stockout Risk Ratio %]`
- **Description**: Percentage of inventory items operating below safety reorder threshold.
- **Display Folder**: `_Inventory Measures\Stockout Risk Metrics`
- **Format String**: `0.00%`
- **DAX Formula**:
```dax
Stockout Risk Ratio % = 
VAR _LowStock = [Items Below Reorder Point]
VAR _TotalItems = CALCULATE(COUNTROWS(fact_inventory_snapshot), LASTDATE(dim_date[date_key]))
RETURN
DIVIDE(_LowStock, _TotalItems, 0)
```

---

## 5. Plant Operations & Telemetry Measures

### 18. `[Active Fleet Size]`
- **Description**: Distinct count of manufacturing plant machinery actively transmitting telemetry.
- **Display Folder**: `_Operations Measures\Equipment Telemetry`
- **Format String**: `#,##0`
- **Expected Baseline Value**: `50`
- **DAX Formula**:
```dax
Active Fleet Size = 
DISTINCTCOUNT(dim_machine[machine_id])
```

---

### 19. `[Fleet Temperature Avg (°C)]`
- **Description**: Average operating temperature recorded across all active machine telemetry rollups.
- **Display Folder**: `_Operations Measures\Equipment Telemetry`
- **Format String**: `0.0°C`
- **DAX Formula**:
```dax
Fleet Temperature Avg (°C) = 
AVERAGE(fact_machine_telemetry[avg_temperature])
```

---

### 20. `[Fleet Vibration Avg (mm/s)]`
- **Description**: Average vibration level recorded across active machine telemetry rollups.
- **Display Folder**: `_Operations Measures\Equipment Telemetry`
- **Format String**: `0.00 mm/s`
- **DAX Formula**:
```dax
Fleet Vibration Avg (mm/s) = 
AVERAGE(fact_machine_telemetry[avg_vibration])
```

---

### 21. `[Total Maintenance Downtime Hours]`
- **Description**: Total hours lost to machine repair and maintenance events.
- **Display Folder**: `_Operations Measures\Maintenance & Downtime`
- **Format String**: `#,##0.0 hrs`
- **Expected Baseline Value**: `180.0 hrs`
- **DAX Formula**:
```dax
Total Maintenance Downtime Hours = 
SUM(fact_maintenance_events[downtime_hours])
```
