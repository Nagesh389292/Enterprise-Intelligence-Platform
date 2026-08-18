# Enterprise Power BI Dashboard UX Wireframes & Interactive Layout Specifications

## 1. Design System & Visual Style Standards

The NexaCore Power BI reporting suite adheres to modern corporate UX standards optimized for C-Suite clarity, rapid decision-making, and high visual appeal.

### Color Palette (Hex Tokens)

| Role / Intent | Color Token Name | Hex Code | Visual Application |
| :--- | :--- | :--- | :--- |
| **Primary Brand** | Executive Navy | `#0F172A` | Page headers, main card container borders, primary text |
| **Success / Target** | Metric Emerald | `#10B981` | Positive YoY growth, stock levels above reorder point, normal telemetry |
| **Warning / Caution** | Alert Amber | `#F59E0B` | Inventory near reorder threshold, moderate telemetry heat, medium priority tickets |
| **Critical / Negative** | Critical Coral | `#EF4444` | Negative revenue trend, stockouts, machine high vibration/temp warnings |
| **Background Dark** | Slate Dark | `#1E293B` | Dark Mode KPI header containers |
| **Background Light** | Off-White Slate | `#F8FAFC` | Dashboard canvas background |

### Typography & Spacing
- **Font Family**: `Segoe UI` or `Inter` (Standard Power BI System Font).
- **KPI Card Numbers**: 28pt Bold (`#0F172A`).
- **Section Headers**: 14pt Semi-Bold (`#475569`).
- **Grid Alignment**: Standard 16:9 canvas (1280x720 pixels or 1920x1080 scaling) with 12px visual margin gutters.

---

## 2. Page 1: Executive Overview Dashboard

**Target Audience**: CEO, CFO, COO, Executive Committee  
**Goal**: High-level summary of financial revenue, operational fleet health, inventory risk, and customer satisfaction in a single screen.

```text
+---------------------------------------------------------------------------------------------------+
|  NexaCore Executive Overview  [ Date Range Slicer: YTD ]  [ Region: All ]  [ Reset Filters ]      |
+---------------------------------------------------------------------------------------------------+
| +-------------------+ +-------------------+ +-------------------+ +-------------------+           |
| | Net Revenue       | | Total Orders      | | CSAT Score        | | Fleet Vibration   |           |
| | $18.27M           | | 10,000            | | 4.15 / 5.0        | | 2.14 mm/s         |           |
| | (+12.4% vs PY)    | | (35.2k items)     | | (2.5k surveys)    | | (50 machines)   |           |
| +-------------------+ +-------------------+ +-------------------+ +-------------------+           |
+---------------------------------------------------------------------------------------------------+
| +-----------------------------------------------+ +---------------------------------------------+ |
| | Monthly Net Revenue vs Prior Year (Combo Bar) | | Top 5 Products by Revenue (Horizontal Bar)  | |
| | [ Jan - Dec 2026 Timeline ]                   | | 1. Premium Industrial Sensor A   $2.4M      | |
| |                                               | | 2. Heavy Duty Motor Model B     $1.9M      | |
| +-----------------------------------------------+ +---------------------------------------------+ |
+---------------------------------------------------------------------------------------------------+
| +-----------------------------------------------+ +---------------------------------------------+ |
| | Regional Revenue Distribution (Choropleth Map)| | Operational Fleet Risk Matrix (Scatter Plot)| |
| | North America | Europe | Asia Pacific         | | Temp vs Vibration per Machine             | |
| +-----------------------------------------------+ +---------------------------------------------+ |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Page 2: Commercial & Sales Performance

**Target Audience**: VP of Sales, Commercial Directors, Regional Sales Managers  
**Goal**: Deep dive into revenue drivers, product category performance, discount impacts, and customer purchasing trends.

### Visual Grid Layout
1. **Top KPI Strip**:
   - `[Net Revenue]` ($18.27M)
   - `[Gross Revenue]` ($19.33M)
   - `[Total Discounts]` ($1.06M)
   - `[Average Order Value]` ($1,827.46)
   - `[YoY Revenue Growth %]`
2. **Main Content Area**:
   - **Visual 1 (Line & Stacked Column Chart)**: Monthly Gross Revenue vs Discounts & Net Revenue trend.
   - **Visual 2 (Treemap)**: Sales revenue segmented by Product Category and Product Sub-category.
   - **Visual 3 (Matrix Grid)**: Customer performance table with drill-down (`Customer Name -> Order ID -> Product`).
3. **Interactive Slicers**:
   - Order Status (`DELIVERED`, `SHIPPED`, `PENDING`).
   - Customer Segment (`Enterprise`, `SMB`, `Consumer`).

---

## 4. Page 3: Supply Chain & Inventory Snapshot

**Target Audience**: VP of Supply Chain, Logistics Operations, Warehouse Managers  
**Goal**: Monitor inventory stock levels across 5 distribution centers, flag stockout risks, and optimize reorder points.

### Visual Grid Layout
1. **Top KPI Strip**:
   - `[Current Inventory On Hand]` (184,520 units)
   - `[Items Below Reorder Point]` (87 items - High Alert Amber)
   - `[Stockout Risk Ratio %]` (17.4%)
   - `[Total Warehouses]` (5 locations)
2. **Main Content Area**:
   - **Visual 1 (Clustered Column Chart)**: Stock On Hand vs Safety Reorder Point per Warehouse (`WH-001` through `WH-005`).
   - **Visual 2 (Heatmap Grid)**: Product stock level severity matrix (Red = Stockout, Yellow = Below Reorder, Green = Healthy).
   - **Visual 3 (Table with Data Bars)**: Top 10 items requiring immediate reorder (Product Name, Warehouse Region, On Hand, Reorder Point, Deficit).

---

## 5. Page 4: Plant Equipment & Telemetry Health

**Target Audience**: Plant Managers, Chief Maintenance Engineers, Reliability Technicians  
**Goal**: Real-time IoT sensor telemetry monitoring across 50 manufacturing machines to prevent unplanned downtime.

### Visual Grid Layout
1. **Top KPI Strip**:
   - `[Active Fleet Size]` (50 machines)
   - `[Fleet Temperature Avg]` (72.4°C)
   - `[Fleet Vibration Avg]` (2.14 mm/s)
   - `[Total Maintenance Downtime Hours]` (180.0 hrs)
2. **Main Content Area**:
   - **Visual 1 (Scatter Plot)**: Machine Health Risk Matrix (X-Axis = Avg Vibration, Y-Axis = Avg Temp, Bubble Size = Telemetry Event Count, Color = Anomaly Alert Status).
   - **Visual 2 (Real-time Stepped Line Chart)**: 24-hour telemetry trend line for selected machine (`avg_temperature` & `avg_vibration` overlay).
   - **Visual 3 (Maintenance Log Table)**: Downtime events breakdown (`Machine ID`, `Failure Reason`, `Downtime Hours`, `Technician Notes`).

---

## 6. Page 5: Customer Experience & CSAT Analysis

**Target Audience**: Chief Customer Officer, Head of Support, Operations Quality Lead  
**Goal**: Track support ticket volume, customer satisfaction trends, and feedback sentiment.

### Visual Grid Layout
1. **Top KPI Strip**:
   - `[Total Customers]` (1,000)
   - `[Total Support Tickets]` (2,500)
   - `[Average CSAT Score]` (4.15 / 5.00)
   - `[CSAT Response Rate %]`
2. **Main Content Area**:
   - **Visual 1 (Donut Chart)**: Support Ticket Distribution by Issue Category (`Billing`, `Shipping Delay`, `Hardware Fault`, `General`).
   - **Visual 2 (Gauge Chart)**: CSAT Target Gauge (Current: 4.15 vs Target: 4.25).
   - **Visual 3 (Verbatim Feedback Word Cloud / Table)**: Filtered verbatim survey feedback entries sorted by lowest CSAT score.

---

## 7. Page 6: Executive RLS & Security Governance View

**Target Audience**: Security Administrators, Compliance Officers, Data Governance Leads  
**Goal**: Audit row-level security role behavior and regional data entitlement rules.

### Visual Grid Layout
1. **Role Tester Toolbar**: Dynamic parameter switcher to simulate `Executive_RLS`, `Regional_Manager_RLS (US)`, and `Plant_Operations_RLS (Plant-1)`.
2. **Data Entitlement Verification Matrix**: Shows filtered row counts across `dim_customer`, `fact_orders`, `dim_warehouse`, and `dim_machine` under active security impersonation.

---

## 8. Interactive Features & Navigation Design

### 1. Dynamic Page Navigation Sidebar
- Hover-state collapse/expand navigation panel with custom SVG icon buttons for fast switching between all 6 pages.

### 2. Contextual Drill-Through Pathways
- **Sales Drill-Through**: Right-click on any Product on Page 1 or 2 -> Drill-through to **Product Performance Detail Page**.
- **Equipment Drill-Through**: Right-click on any Machine bubble on Page 4 -> Drill-through to **Machine Sensor Diagnostics Page**.

### 3. Customized Tooltip Pages
- Hovering over a Warehouse column on Page 3 displays a floating micro-chart showing 30-day stock depletion rates.
- Hovering over a Machine ID displays last 5 maintenance logs and technician assignment.
