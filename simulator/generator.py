"""Procedural vehicle fleet generator for Delhi NCR surveillance simulation.
Generates authentic Indian RTO registration plates, diverse vehicle categories,
realistic speeds, and flagged watch-list profiles.
"""

import random
from typing import List, Dict, Optional
from providers.base import VehicleType


class VehicleGenerator:
    """Generates realistic vehicle profiles with authentic Indian RTO registration numbers,
    vehicle makes/models, colors, and assigned route behaviors.
    """

    STATES = ["DL", "HR", "UP", "PB"]

    # State-wise authentic RTO codes
    RTO_CODES = {
        "DL": [f"{i:02d}" for i in range(1, 15) if i != 4],   # DL01 to DL14 (DL04 reserved for anomaly demos)
        "HR": ["26", "29", "51", "70", "98"],       # Gurugram, Faridabad, etc.
        "UP": ["16", "14", "32", "78"],             # Noida, Ghaziabad, Lucknow, etc.
        "PB": ["01", "02", "10", "65"]              # Chandigarh, Mohali, etc.
    }

    SERIES_LETTERS = ["AB", "AX", "BK", "CQ", "DZ", "EA", "EK", "GA", "HJ", "MN", "XY"]

    MODELS_BY_TYPE = {
        VehicleType.CAR: [
            "Maruti Swift", "Hyundai i20", "Honda City", "Tata Tiago",
            "Maruti Baleno", "Volkswagen Virtus", "Skoda Slavia"
        ],
        VehicleType.SUV: [
            "Hyundai Creta", "Tata Nexon", "Mahindra Scorpio-N",
            "Toyota Fortuner", "Kia Seltos", "Mahindra XUV700"
        ],
        VehicleType.MOTORCYCLE: [
            "Royal Enfield Classic 350", "Hero Splendor Plus",
            "Bajaj Pulsar NS200", "TVS Apache RTR", "KTM Duke 250"
        ],
        VehicleType.AUTO: [
            "Bajaj Compact Auto", "Piaggio Ape Auto", "Mahindra Treo Electric"
        ],
        VehicleType.BUS: [
            "DTC Electric Bus", "Ashok Leyland Viking", "Tata Starbus Ultra"
        ],
        VehicleType.TRUCK: [
            "Tata 407 LPT", "Eicher Pro 2049", "BharatBenz 1217R"
        ]
    }

    COLORS = [
        "Pearl White", "Silver Metallic", "Carbon Black",
        "Deep Navy Blue", "Cherry Red", "Smoke Grey", "Racing Green"
    ]

    @classmethod
    def generate_plate(
        cls,
        state: Optional[str] = None,
        rng: Optional[random.Random] = None
    ) -> str:
        """Generates an authentic Indian registration number, e.g. DL01AB1234."""
        r = rng or random
        st = state if state in cls.STATES else r.choice(cls.STATES)
        rto = r.choice(cls.RTO_CODES[st])
        series = r.choice(cls.SERIES_LETTERS)
        num = r.randint(1001, 9999)
        return f"{st}{rto}{series}{num}"

    @classmethod
    def generate_vehicle_profile(
        cls,
        vehicle_type: Optional[VehicleType] = None,
        is_flagged: bool = False,
        flag_reason: Optional[str] = None,
        rng: Optional[random.Random] = None
    ) -> dict:
        """Generates a complete vehicle entity with realistic specs."""
        r = rng or random
        if vehicle_type is not None:
            v_type = vehicle_type
        else:
            v_type = r.choices(
                [
                    VehicleType.CAR,
                    VehicleType.SUV,
                    VehicleType.MOTORCYCLE,
                    VehicleType.AUTO,
                    VehicleType.BUS,
                    VehicleType.TRUCK
                ],
                weights=[40, 25, 18, 10, 4, 3],
                k=1
            )[0]

        plate = cls.generate_plate(rng=r)
        make_model = r.choice(cls.MODELS_BY_TYPE[v_type])
        color = r.choice(cls.COLORS)
        is_ev = r.random() < 0.12  # 12% EV adoption
        if is_ev and v_type in [VehicleType.CAR, VehicleType.SUV]:
            make_model += " EV"

        # Preferred cruising speed in km/h
        if v_type in [VehicleType.BUS, VehicleType.TRUCK, VehicleType.AUTO]:
            base_speed = r.uniform(35.0, 55.0)
        else:
            base_speed = r.uniform(45.0, 75.0)

        return {
            "plate_number": plate,
            "vehicle_type": v_type,
            "make_model": make_model,
            "color": color,
            "is_ev": is_ev,
            "cruising_speed_kmh": round(base_speed, 1),
            "is_flagged": is_flagged,
            "flag_reason": flag_reason
        }

    @classmethod
    def generate_fleet(
        cls,
        size: int = 60,
        seed: Optional[int] = None
    ) -> List[dict]:
        """Generates a fleet of vehicles with diverse characteristics.
        Supports deterministic seed for demo reproducibility.
        """
        rng = random.Random(seed) if seed is not None else random
        fleet = [cls.generate_vehicle_profile(rng=rng) for _ in range(size)]

        # Tag watch-listed vehicles for demo if fleet size permits
        if len(fleet) > 0:
            fleet[0]["is_flagged"] = True
            fleet[0]["flag_reason"] = "STOLEN_VEHICLE_REPORT_FIR_9021"
        if len(fleet) > 1:
            fleet[1]["is_flagged"] = True
            fleet[1]["flag_reason"] = "SUSPECT_IN_ORGANIZED_CAR_THEFT"

        return fleet
