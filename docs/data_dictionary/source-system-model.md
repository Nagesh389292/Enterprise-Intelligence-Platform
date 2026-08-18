# Source System Data Dictionary (Normalized 3NF Model)
### NexaCore Industries Operational Source Database

This document details the normalized Third Normal Form (3NF) relational source-system schema for **NexaCore Industries**. It represents the operational OLTP database layout across 5 core business domains comprising 18 entities.

---

## 1. Customer Domain

### 1.1 `customer_segments`
* **Purpose**: Defines business segmentation tiers and account risk classifications.
* **Primary Key**: `segment_id` (INT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `segment_id` | INT | NOT NULL | PK | Auto-increment | - | Unique segment surrogate identifier |
| `segment_code` | VARCHAR(30) | NOT NULL | - | UNIQUE | - | Business code (e.g., ENTERPRISE, MID_MARKET, SMB) |
| `segment_name` | VARCHAR(100) | NOT NULL | - | - | - | Descriptive segment title |
| `target_annual_revenue` | NUMERIC(15,2) | NULL | - | >= 0 | 0.00 | Targeted annual client spend tier |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Audit timestamp of record creation |

* **Indexes**: `idx_customer_segments_code` ON `(segment_code)`

---

### 1.2 `customers`
* **Purpose**: Master table of all enterprise customer accounts.
* **Primary Key**: `customer_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `customer_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique customer global identifier |
| `company_name` | VARCHAR(255) | NOT NULL | - | - | - | Legal business name of the client |
| `industry` | VARCHAR(100) | NOT NULL | - | - | - | Operating industry (e.g., Automotive, Aerospace) |
| `segment_id` | INT | NOT NULL | FK | FK -> customer_segments.segment_id | - | Reference to business segment |
| `account_status` | VARCHAR(20) | NOT NULL | - | CHECK (status IN ('ACTIVE','INACTIVE','CHURNED')) | 'ACTIVE' | Operational account status |
| `contact_email` | VARCHAR(255) | NOT NULL | - | UNIQUE | - | Primary account holder email |
| `contact_phone` | VARCHAR(50) | NULL | - | - | - | Primary phone contact |
| `credit_limit` | NUMERIC(12,2) | NOT NULL | - | >= 0 | 50000.00 | Approved purchasing credit limit |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Date account was onboarded |
| `updated_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Timestamp of last record update |

* **Indexes**:
  * `idx_customers_segment` ON `(segment_id)`
  * `idx_customers_status` ON `(account_status)`
  * `idx_customers_email` ON `(contact_email)`

---

### 1.3 `customer_addresses`
* **Purpose**: Multi-location shipping and billing physical addresses per customer.
* **Primary Key**: `address_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `address_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique address record ID |
| `customer_id` | UUID | NOT NULL | FK | FK -> customers.customer_id | - | Parent customer account |
| `address_type` | VARCHAR(20) | NOT NULL | - | CHECK (type IN ('BILLING','SHIPPING')) | 'SHIPPING' | Type of address location |
| `street_address` | VARCHAR(255) | NOT NULL | - | - | - | Physical street address line |
| `city` | VARCHAR(100) | NOT NULL | - | - | - | Municipality / City name |
| `state_province` | VARCHAR(100) | NOT NULL | - | - | - | State or administrative region |
| `postal_code` | VARCHAR(20) | NOT NULL | - | - | - | Postal/ZIP code |
| `country_code` | CHAR(2) | NOT NULL | - | ISO-3166-1 alpha-2 | - | 2-letter country code (US, DE, JP, etc.) |
| `is_primary` | BOOLEAN | NOT NULL | - | - | FALSE | Flags primary billing/shipping location |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Audit creation timestamp |

* **Indexes**: `idx_customer_addresses_customer` ON `(customer_id, address_type)`

---

### 1.4 `customer_interactions`
* **Purpose**: Operational touchpoints (sales calls, email exchanges, portal logins).
* **Primary Key**: `interaction_id` (BIGINT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `interaction_id` | BIGINT | NOT NULL | PK | Auto-increment | - | Unique interaction event ID |
| `customer_id` | UUID | NOT NULL | FK | FK -> customers.customer_id | - | Associated customer account |
| `channel` | VARCHAR(30) | NOT NULL | - | CHECK (channel IN ('EMAIL','PHONE','PORTAL','IN_PERSON')) | - | Communication channel used |
| `interaction_type` | VARCHAR(50) | NOT NULL | - | - | - | Activity type (e.g., DEMO_REQUEST, RENEWAL_TALK) |
| `notes` | TEXT | NULL | - | - | - | Interaction summary notes |
| `interaction_timestamp`| TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Exact timestamp of communication |

* **Indexes**: `idx_customer_interactions_lookup` ON `(customer_id, interaction_timestamp)`

---

## 2. Sales Domain

### 2.1 `sales_channels`
* **Purpose**: Master table of distribution channels generating sales orders.
* **Primary Key**: `channel_id` (INT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `channel_id` | INT | NOT NULL | PK | Auto-increment | - | Channel surrogate key |
| `channel_code` | VARCHAR(30) | NOT NULL | - | UNIQUE | - | Code (DIRECT_SALES, E_COMMERCE, DISTRIBUTOR) |
| `channel_name` | VARCHAR(100) | NOT NULL | - | - | - | Full sales channel name |
| `commission_rate` | NUMERIC(5,4) | NOT NULL | - | BETWEEN 0 AND 1 | 0.0000 | Standard channel commission rate |

---

### 2.2 `product_categories`
* **Purpose**: Hierarchical grouping of industrial products.
* **Primary Key**: `category_id` (INT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `category_id` | INT | NOT NULL | PK | Auto-increment | - | Category unique identifier |
| `category_name` | VARCHAR(100) | NOT NULL | - | UNIQUE | - | Category name (e.g., Hydraulics, Fasteners) |
| `parent_category_id` | INT | NULL | FK | FK -> product_categories.category_id | NULL | Self-referencing parent for hierarchy |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Creation timestamp |

---

### 2.3 `products`
* **Purpose**: Master catalog of industrial products and specifications.
* **Primary Key**: `product_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `product_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique product global ID |
| `sku` | VARCHAR(50) | NOT NULL | - | UNIQUE | - | Stock Keeping Unit identifier |
| `product_name` | VARCHAR(255) | NOT NULL | - | - | - | Commercial product name |
| `category_id` | INT | NOT NULL | FK | FK -> product_categories.category_id | - | Associated product category |
| `unit_cost` | NUMERIC(10,2) | NOT NULL | - | >= 0 | - | Standard manufacturing/purchase cost |
| `unit_price` | NUMERIC(10,2) | NOT NULL | - | >= 0 | - | Standard list selling price |
| `reorder_point` | INT | NOT NULL | - | >= 0 | 100 | Minimum stock threshold for reorder |
| `is_active` | BOOLEAN | NOT NULL | - | - | TRUE | Flag for active catalog status |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Catalog entry creation timestamp |

* **Indexes**:
  * `idx_products_sku` ON `(sku)`
  * `idx_products_category` ON `(category_id)`

---

### 2.4 `orders`
* **Purpose**: Header table recording customer purchasing transactions.
* **Primary Key**: `order_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique order identifier |
| `order_number` | VARCHAR(50) | NOT NULL | - | UNIQUE | - | Human-readable order number (e.g., ORD-2026-0001) |
| `customer_id` | UUID | NOT NULL | FK | FK -> customers.customer_id | - | Purchasing customer ID |
| `channel_id` | INT | NOT NULL | FK | FK -> sales_channels.channel_id | - | Sales channel source |
| `shipping_address_id`| UUID | NOT NULL | FK | FK -> customer_addresses.address_id | - | Destination shipping location |
| `order_status` | VARCHAR(20) | NOT NULL | - | CHECK (status IN ('PENDING','PROCESSING','SHIPPED','DELIVERED','CANCELLED')) | 'PENDING' | Transaction fulfillment state |
| `order_timestamp` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Exact date and time order was placed |
| `promised_delivery_date`| DATE | NULL | - | - | - | Contractual delivery target date |
| `total_amount` | NUMERIC(14,2) | NOT NULL | - | >= 0 | 0.00 | Gross total order monetary value |

* **Indexes**:
  * `idx_orders_customer` ON `(customer_id)`
  * `idx_orders_timestamp` ON `(order_timestamp)`
  * `idx_orders_status` ON `(order_status)`

---

### 2.5 `order_items`
* **Purpose**: Line-item details attached to each customer order.
* **Primary Key**: `order_item_id` (BIGINT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_item_id` | BIGINT | NOT NULL | PK | Auto-increment | - | Unique line-item ID |
| `order_id` | UUID | NOT NULL | FK | FK -> orders.order_id | - | Parent order header |
| `product_id` | UUID | NOT NULL | FK | FK -> products.product_id | - | Ordered product SKU reference |
| `quantity` | INT | NOT NULL | - | > 0 | - | Ordered unit quantity |
| `unit_price` | NUMERIC(10,2) | NOT NULL | - | >= 0 | - | Actual agreed price per unit |
| `discount_amount` | NUMERIC(10,2) | NOT NULL | - | >= 0 | 0.00 | Discount applied to line item |
| `total_price` | NUMERIC(12,2) | NOT NULL | - | >= 0 | - | Net line item total ((qty * price) - disc) |

* **Indexes**: `idx_order_items_composite` ON `(order_id, product_id)`

---

## 3. Supply Chain Domain

### 3.1 `suppliers`
* **Purpose**: Master table of component suppliers and vendors.
* **Primary Key**: `supplier_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `supplier_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique supplier ID |
| `supplier_code` | VARCHAR(30) | NOT NULL | - | UNIQUE | - | Business vendor code (e.g., SUP-001) |
| `company_name` | VARCHAR(255) | NOT NULL | - | - | - | Vendor legal business name |
| `quality_rating` | NUMERIC(3,2) | NULL | - | BETWEEN 0 AND 5 | 5.00 | Supplier performance score (0-5 scale) |
| `lead_time_days` | INT | NOT NULL | - | >= 0 | 14 | Average lead time for component delivery |
| `country_code` | CHAR(2) | NOT NULL | - | ISO-3166-1 alpha-2 | - | Vendor country of operation |

---

### 3.2 `warehouses`
* **Purpose**: Master list of storage facilities and fulfillment centers.
* **Primary Key**: `warehouse_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `warehouse_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique warehouse identifier |
| `warehouse_code` | VARCHAR(30) | NOT NULL | - | UNIQUE | - | Facility code (e.g., WH-EU-BERLIN) |
| `warehouse_name` | VARCHAR(100) | NOT NULL | - | - | - | Facility descriptive name |
| `region` | VARCHAR(50) | NOT NULL | - | - | - | Operating region (North America, EU, APAC) |
| `capacity_sqft` | INT | NOT NULL | - | > 0 | - | Total storage footprint capacity |

---

### 3.3 `inventory`
* **Purpose**: Current snapshot of product stock levels per warehouse location.
* **Primary Key**: `inventory_id` (BIGINT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `inventory_id` | BIGINT | NOT NULL | PK | Auto-increment | - | Unique inventory snapshot key |
| `warehouse_id` | UUID | NOT NULL | FK | FK -> warehouses.warehouse_id | - | Storage location facility |
| `product_id` | UUID | NOT NULL | FK | FK -> products.product_id | - | Stocked product SKU |
| `quantity_on_hand` | INT | NOT NULL | - | >= 0 | 0 | Current physical stock count |
| `quantity_allocated`| INT | NOT NULL | - | >= 0 | 0 | Stock reserved for pending orders |
| `last_count_date` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Timestamp of last physical count |

* **Constraints**: `UNIQUE (warehouse_id, product_id)`
* **Indexes**: `idx_inventory_product_wh` ON `(product_id, warehouse_id)`

---

### 3.4 `inventory_transactions`
* **Purpose**: Audit log of all stock receipts, shipments, and manual adjustments.
* **Primary Key**: `transaction_id` (BIGINT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `transaction_id` | BIGINT | NOT NULL | PK | Auto-increment | - | Unique inventory move ID |
| `warehouse_id` | UUID | NOT NULL | FK | FK -> warehouses.warehouse_id | - | Target facility |
| `product_id` | UUID | NOT NULL | FK | FK -> products.product_id | - | Affected product SKU |
| `transaction_type` | VARCHAR(30) | NOT NULL | - | CHECK (type IN ('RECEIPT','SHIPMENT','ADJUSTMENT','TRANSFER')) | - | Inventory movement classification |
| `quantity_change` | INT | NOT NULL | - | - | - | Signed stock change (+ receipt, - shipment) |
| `reference_id` | VARCHAR(100) | NULL | - | - | - | Associated Order or PO reference |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Transaction timestamp |

* **Indexes**: `idx_inventory_trans_lookup` ON `(warehouse_id, product_id, created_at)`

---

## 4. Operations & Industrial IoT Domain

### 4.1 `machine_types`
* **Purpose**: Classification catalog of industrial manufacturing equipment.
* **Primary Key**: `machine_type_id` (INT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `machine_type_id` | INT | NOT NULL | PK | Auto-increment | - | Type identifier |
| `type_name` | VARCHAR(100) | NOT NULL | - | UNIQUE | - | Equipment model type (e.g., CNC_LATHE, ROBOTIC_ARM) |
| `manufacturer` | VARCHAR(100) | NOT NULL | - | - | - | Machine manufacturer name |
| `max_temperature_c` | NUMERIC(5,2) | NOT NULL | - | > 0 | 120.00 | Maximum safe operating temperature |
| `max_vibration_rms` | NUMERIC(5,2) | NOT NULL | - | > 0 | 5.00 | Maximum safe vibration threshold |

---

### 4.2 `machines`
* **Purpose**: Master inventory of operational machines across factories.
* **Primary Key**: `machine_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `machine_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique physical machine ID |
| `serial_number` | VARCHAR(100) | NOT NULL | - | UNIQUE | - | Factory serial number |
| `machine_type_id` | INT | NOT NULL | FK | FK -> machine_types.machine_type_id | - | Equipment category classification |
| `warehouse_id` | UUID | NOT NULL | FK | FK -> warehouses.warehouse_id | - | Installation warehouse/factory site |
| `installation_date`| DATE | NOT NULL | - | - | - | Commissioning date |
| `status` | VARCHAR(20) | NOT NULL | - | CHECK (status IN ('RUNNING','MAINTENANCE','OFFLINE','FAILED')) | 'RUNNING' | Current operational status |

* **Indexes**: `idx_machines_facility` ON `(warehouse_id, status)`

---

### 4.3 `machine_telemetry`
* **Purpose**: High-frequency streaming sensor metrics collected from machines.
* **Primary Key**: `telemetry_id` (BIGINT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `telemetry_id` | BIGINT | NOT NULL | PK | Auto-increment | - | Unique telemetry event ID |
| `machine_id` | UUID | NOT NULL | FK | FK -> machines.machine_id | - | Reporting machine ID |
| `temperature_c` | NUMERIC(5,2) | NOT NULL | - | - | - | Measured operating temperature (°C) |
| `vibration_rms` | NUMERIC(5,2) | NOT NULL | - | - | - | Measured root-mean-square vibration |
| `pressure_psi` | NUMERIC(6,2) | NOT NULL | - | - | - | Operating hydraulic pressure (PSI) |
| `power_kw` | NUMERIC(6,2) | NOT NULL | - | - | - | Power consumption rate (kW) |
| `recorded_at` | TIMESTAMPTZ | NOT NULL | - | - | - | Precise sensor reading timestamp |

* **Indexes**: `idx_telemetry_machine_time` ON `(machine_id, recorded_at DESC)`

---

### 4.4 `maintenance_events`
* **Purpose**: History of scheduled and reactive maintenance actions on machines.
* **Primary Key**: `maintenance_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `maintenance_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique maintenance record ID |
| `machine_id` | UUID | NOT NULL | FK | FK -> machines.machine_id | - | Target machine |
| `maintenance_type` | VARCHAR(30) | NOT NULL | - | CHECK (type IN ('PREVENTIVE','CORRECTIVE','EMERGENCY')) | - | Classification of work performed |
| `description` | TEXT | NOT NULL | - | - | - | Detailed technician work log |
| `technician_name` | VARCHAR(100) | NOT NULL | - | - | - | Assigned technician |
| `performed_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Timestamp maintenance was conducted |
| `cost_usd` | NUMERIC(10,2) | NOT NULL | - | >= 0 | 0.00 | Repair/part monetary cost |

---

### 4.5 `failure_events`
* **Purpose**: Incident log of unplanned machine failure events.
* **Primary Key**: `failure_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `failure_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique failure event ID |
| `machine_id` | UUID | NOT NULL | FK | FK -> machines.machine_id | - | Failed machine ID |
| `failure_code` | VARCHAR(50) | NOT NULL | - | - | - | Diagnostic error code (e.g., OVERHEAT_E4) |
| `failure_reason` | TEXT | NOT NULL | - | - | - | Root cause analysis statement |
| `occurred_at` | TIMESTAMPTZ | NOT NULL | - | - | - | Exact timestamp of breakdown |
| `downtime_hours` | NUMERIC(5,2) | NOT NULL | - | >= 0 | 0.00 | Total production hours lost |

* **Indexes**: `idx_failures_machine_time` ON `(machine_id, occurred_at)`

---

## 5. Support Domain

### 5.1 `support_tickets`
* **Purpose**: Customer service and technical issue tracking requests.
* **Primary Key**: `ticket_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ticket_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Unique support ticket ID |
| `ticket_number` | VARCHAR(50) | NOT NULL | - | UNIQUE | - | Ticket code (e.g., TCK-2026-9901) |
| `customer_id` | UUID | NOT NULL | FK | FK -> customers.customer_id | - | Requesting client account |
| `order_id` | UUID | NULL | FK | FK -> orders.order_id | NULL | Optional linked order reference |
| `issue_category` | VARCHAR(50) | NOT NULL | - | - | - | Issue category (DEFECT, DELAY, BILLING) |
| `priority` | VARCHAR(20) | NOT NULL | - | CHECK (priority IN ('LOW','MEDIUM','HIGH','URGENT')) | 'MEDIUM' | Urgency escalation level |
| `status` | VARCHAR(20) | NOT NULL | - | CHECK (status IN ('OPEN','IN_PROGRESS','RESOLVED','CLOSED')) | 'OPEN' | Ticket lifecycle state |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Opening timestamp |
| `resolved_at` | TIMESTAMPTZ | NULL | - | - | NULL | Resolution completion timestamp |

* **Indexes**:
  * `idx_tickets_customer` ON `(customer_id)`
  * `idx_tickets_status` ON `(status, priority)`

---

### 5.2 `ticket_interactions`
* **Purpose**: Individual communication messages exchanged within a support ticket thread.
* **Primary Key**: `interaction_id` (BIGINT)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `interaction_id` | BIGINT | NOT NULL | PK | Auto-increment | - | Message log identifier |
| `ticket_id` | UUID | NOT NULL | FK | FK -> support_tickets.ticket_id | - | Parent support ticket |
| `sender_type` | VARCHAR(20) | NOT NULL | - | CHECK (sender_type IN ('CUSTOMER','AGENT','SYSTEM')) | - | Author classification |
| `message_text` | TEXT | NOT NULL | - | - | - | Body of interaction message |
| `sent_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Message dispatch timestamp |

---

### 5.3 `customer_satisfaction`
* **Purpose**: Post-ticket resolution survey responses and CSAT ratings.
* **Primary Key**: `survey_id` (UUID)

| Column Name | Data Type | Nullable | Key | Constraints | Default | Business Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `survey_id` | UUID | NOT NULL | PK | UUID v4 | gen_random_uuid() | Survey record ID |
| `ticket_id` | UUID | NOT NULL | FK | FK -> support_tickets.ticket_id | - | UNIQUE constraint per ticket |
| `score` | INT | NOT NULL | - | BETWEEN 1 AND 5 | - | CSAT rating (1 = Poor, 5 = Excellent) |
| `feedback_text` | TEXT | NULL | - | - | - | Optional customer written review |
| `submitted_at` | TIMESTAMPTZ | NOT NULL | - | - | CURRENT_TIMESTAMP | Submission timestamp |

* **Constraints**: `UNIQUE (ticket_id)`
