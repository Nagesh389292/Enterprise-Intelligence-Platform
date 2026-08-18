"""
Operations, Industrial IoT & Machine Telemetry Entity Generators.
"""

import uuid
from typing import List, Tuple
from datetime import datetime, timedelta
from .base import BaseGenerator
from ..models import Warehouse, MachineType, Machine, MachineTelemetry, MaintenanceEvent, FailureEvent

class OperationsGenerator(BaseGenerator):
    MACHINE_TYPES = [
        ("CNC_LATHE", "Haas Automation", 125.00, 5.50),
        ("ROBOTIC_ARM", "KUKA Robotics", 95.00, 3.50),
        ("HYDRAULIC_PRESS", "Bosch Rexroth", 140.00, 6.00),
        ("INJECTION_MOLDER", "Sumitomo Demag", 160.00, 4.50),
        ("CONVEYOR_SYSTEM", "Siemens Motion", 85.00, 2.50)
    ]

    def generate_machine_types(self) -> List[MachineType]:
        types = []
        for i, (name, mfr, temp, vib) in enumerate(self.MACHINE_TYPES, 1):
            types.append(MachineType(i, name, mfr, temp, vib))
        return types

    def generate_machines(self, count: int, machine_types: List[MachineType], warehouses: List[Warehouse]) -> List[Machine]:
        machines = []
        start_date = datetime(2022, 1, 1)
        
        for i in range(count):
            m_id = str(uuid.UUID(int=self.random.getrandbits(128)))
            sn = f"SN-2022-{i+1001:04d}"
            m_type = self.random.choice(machine_types)
            wh = self.random.choice(warehouses)
            
            inst_date = (start_date + timedelta(days=self.random.randint(0, 1000))).date().isoformat()
            status = self.np_random.choice(["RUNNING", "MAINTENANCE", "OFFLINE", "FAILED"], p=[0.85, 0.08, 0.04, 0.03])
            
            machines.append(Machine(m_id, sn, m_type.machine_type_id, wh.warehouse_id, inst_date, status))
            
        return machines

    def generate_telemetry_and_events(
        self,
        machines: List[Machine],
        readings_per_machine: int
    ) -> Tuple[List[MachineTelemetry], List[MaintenanceEvent], List[FailureEvent]]:
        telemetry = []
        maintenance = []
        failures = []
        
        start_time = datetime(2026, 1, 1, 0, 0, 0)
        telemetry_counter = 1
        
        for m in machines:
            # 5% of machines have elevated failure probability scenario
            is_degrading = (self.random.random() < 0.15)
            
            curr_time = start_time
            base_temp = 65.0
            base_vib = 1.2
            base_press = 90.0
            base_power = 45.0
            
            for r in range(readings_per_machine):
                curr_time += timedelta(minutes=5)
                
                # Add Gaussian noise
                temp = base_temp + float(self.np_random.normal(0, 2.0))
                vib = base_vib + float(self.np_random.normal(0, 0.2))
                press = base_press + float(self.np_random.normal(0, 3.0))
                power = base_power + float(self.np_random.normal(0, 2.0))
                
                # Injected Probabilistic Degradation Scenario
                if is_degrading and r > (readings_per_machine * 0.7):
                    degrade_factor = (r - readings_per_machine * 0.7) / (readings_per_machine * 0.3)
                    temp += degrade_factor * 35.0  # Temperature creep up to +35C
                    vib += degrade_factor * 3.5    # Vibration spike
                    
                    # Probabilistic Failure Event Trigger
                    if temp > 95.0 and self.random.random() < 0.02:
                        fail_id = str(uuid.UUID(int=self.random.getrandbits(128)))
                        failures.append(FailureEvent(
                            failure_id=fail_id,
                            machine_id=m.machine_id,
                            failure_code="OVERHEAT_ERR_E4",
                            failure_reason="Thermal creep exceeding safe operating threshold",
                            occurred_at=curr_time.isoformat(),
                            downtime_hours=round(float(self.np_random.uniform(2.0, 12.0)), 2)
                        ))
                        # Maintenance action after failure
                        maint_id = str(uuid.UUID(int=self.random.getrandbits(128)))
                        maintenance.append(MaintenanceEvent(
                            maintenance_id=maint_id,
                            machine_id=m.machine_id,
                            maintenance_type="CORRECTIVE",
                            description="Replaced thermal sensor and recalibrated hydraulic press",
                            technician_name=f"Tech-{self.random.randint(10,99)}",
                            performed_at=(curr_time + timedelta(hours=2)).isoformat(),
                            cost_usd=round(float(self.np_random.uniform(500.0, 2500.0)), 2)
                        ))
                        # Reset degradation state
                        is_degrading = False
                        
                t_record = MachineTelemetry(
                    telemetry_id=telemetry_counter,
                    machine_id=m.machine_id,
                    temperature_c=round(temp, 2),
                    vibration_rms=round(max(0.1, vib), 2),
                    pressure_psi=round(max(10.0, press), 2),
                    power_kw=round(max(5.0, power), 2),
                    recorded_at=curr_time.isoformat()
                )
                telemetry.append(t_record)
                telemetry_counter += 1
                
        return telemetry, maintenance, failures
