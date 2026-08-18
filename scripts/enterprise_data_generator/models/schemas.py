"""
Domain Schemas and Dataclasses for Enterprise Data Generator.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date

@dataclass
class CustomerSegment:
    segment_id: int
    segment_code: str
    segment_name: str
    target_annual_revenue: float
    created_at: str

@dataclass
class Customer:
    customer_id: str
    company_name: str
    industry: str
    segment_id: int
    account_status: str
    contact_email: str
    contact_phone: str
    credit_limit: float
    created_at: str
    updated_at: str

@dataclass
class CustomerAddress:
    address_id: str
    customer_id: str
    address_type: str
    street_address: str
    city: str
    state_province: str
    postal_code: str
    country_code: str
    is_primary: bool
    created_at: str

@dataclass
class ProductCategory:
    category_id: int
    category_name: str
    parent_category_id: Optional[int]
    created_at: str

@dataclass
class Product:
    product_id: str
    sku: str
    product_name: str
    category_id: int
    unit_cost: float
    unit_price: float
    reorder_point: int
    is_active: bool
    created_at: str

@dataclass
class Supplier:
    supplier_id: str
    supplier_code: str
    company_name: str
    quality_rating: float
    lead_time_days: int
    country_code: str

@dataclass
class Warehouse:
    warehouse_id: str
    warehouse_code: str
    warehouse_name: str
    region: str
    capacity_sqft: int

@dataclass
class Order:
    order_id: str
    order_number: str
    customer_id: str
    channel_id: int
    shipping_address_id: str
    order_status: str
    order_timestamp: str
    promised_delivery_date: Optional[str]
    total_amount: float

@dataclass
class OrderItem:
    order_item_id: int
    order_id: str
    product_id: str
    quantity: int
    unit_price: float
    discount_amount: float
    total_price: float

@dataclass
class Inventory:
    inventory_id: int
    warehouse_id: str
    product_id: str
    quantity_on_hand: int
    quantity_allocated: int
    last_count_date: str

@dataclass
class MachineType:
    machine_type_id: int
    type_name: str
    manufacturer: str
    max_temperature_c: float
    max_vibration_rms: float

@dataclass
class Machine:
    machine_id: str
    serial_number: str
    machine_type_id: int
    warehouse_id: str
    installation_date: str
    status: str

@dataclass
class MachineTelemetry:
    telemetry_id: int
    machine_id: str
    temperature_c: float
    vibration_rms: float
    pressure_psi: float
    power_kw: float
    recorded_at: str

@dataclass
class MaintenanceEvent:
    maintenance_id: str
    machine_id: str
    maintenance_type: str
    description: str
    technician_name: str
    performed_at: str
    cost_usd: float

@dataclass
class FailureEvent:
    failure_id: str
    machine_id: str
    failure_code: str
    failure_reason: str
    occurred_at: str
    downtime_hours: float

@dataclass
class SupportTicket:
    ticket_id: str
    ticket_number: str
    customer_id: str
    order_id: Optional[str]
    issue_category: str
    priority: str
    status: str
    created_at: str
    resolved_at: Optional[str]

@dataclass
class CustomerSatisfaction:
    survey_id: str
    ticket_id: str
    score: int
    feedback_text: Optional[str]
    submitted_at: str
