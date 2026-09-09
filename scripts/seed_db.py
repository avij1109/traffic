#!/usr/bin/env python3
"""Database seeding script for Intelligent Traffic Surveillance Platform.
Initializes SQLite database schema, populates camera checkpoints across Delhi NCR,
registers diverse demo vehicle fleet (including EVs, flagged, and watch-listed targets),
and inserts realistic historical detections and anomaly alerts.
"""

import sys
import os
import uuid
from datetime import datetime, timezone, timedelta

# Add repository root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import engine, SessionLocal, Base
from backend.app.models.camera import Camera
from backend.app.models.vehicle import Vehicle
from backend.app.models.detection import Detection
from backend.app.models.alert import Alert
from simulator.mock_data import CAMERAS_SEED
from simulator.generator import VehicleGenerator
from providers.simulator_provider import SimulatorVisionProvider
from providers.base import VehicleType


def seed_database():
    print("[+] Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    vision_provider = SimulatorVisionProvider()

    try:
        # 1. Seed Cameras
        print(f"[+] Seeding {len(CAMERAS_SEED)} camera checkpoints...")
        cameras_count = 0
        for seed in CAMERAS_SEED:
            existing = db.query(Camera).filter(Camera.id == seed["id"]).first()
            if not existing:
                cam = Camera(
                    id=seed["id"],
                    name=seed["name"],
                    zone=seed["zone"],
                    latitude=seed["latitude"],
                    longitude=seed["longitude"],
                    speed_limit_kmh=seed["speed_limit_kmh"],
                    status=seed["status"],
                    fps=seed["fps"]
                )
                db.add(cam)
                cameras_count += 1
            else:
                existing.name = seed["name"]
                existing.zone = seed["zone"]
                existing.latitude = seed["latitude"]
                existing.longitude = seed["longitude"]
                existing.speed_limit_kmh = seed["speed_limit_kmh"]
                existing.status = seed["status"]
                existing.fps = seed["fps"]
        db.commit()
        print(f"    -> Cameras ready ({len(CAMERAS_SEED)} active nodes).")

        # 2. Seed Pre-configured Demo Vehicles
        now = datetime.now(timezone.utc)
        demo_profiles = [
            {
                "plate_number": "DL04EQ9999",
                "vehicle_type": "SUV",
                "color": "Cherry Red",
                "make_model": "Mahindra Scorpio-N",
                "is_ev": False,
                "is_flagged": True,
                "flag_reason": "SUSPECT_INTERDICTION_HIGH_SPEED"
            },
            {
                "plate_number": "HR26CL0001",
                "vehicle_type": "CAR",
                "color": "Pearl White",
                "make_model": "Hyundai Verna",
                "is_ev": False,
                "is_flagged": True,
                "flag_reason": "CLONED_PLATE_WATCHLIST"
            },
            {
                "plate_number": "UP16AB1234",
                "vehicle_type": "CAR",
                "color": "Deep Navy Blue",
                "make_model": "Tata Nexon EV",
                "is_ev": True,
                "is_flagged": True,
                "flag_reason": "STOLEN_VEHICLE_REPORT_FIR_4011"
            },
            {
                "plate_number": "DL01AX9921",
                "vehicle_type": "TRUCK",
                "color": "Smoke Grey",
                "make_model": "Tata 407 LPT",
                "is_ev": False,
                "is_flagged": False,
                "flag_reason": None
            },
            {
                "plate_number": "DL02BY5544",
                "vehicle_type": "MOTORCYCLE",
                "color": "Carbon Black",
                "make_model": "Royal Enfield Classic 350",
                "is_ev": False,
                "is_flagged": False,
                "flag_reason": None
            },
            {
                "plate_number": "HR29QR1122",
                "vehicle_type": "BUS",
                "color": "Pearl White",
                "make_model": "DTC Electric Bus",
                "is_ev": True,
                "is_flagged": False,
                "flag_reason": None
            },
            {
                "plate_number": "UP14EF3344",
                "vehicle_type": "SUV",
                "color": "Silver Metallic",
                "make_model": "Toyota Fortuner",
                "is_ev": False,
                "is_flagged": False,
                "flag_reason": None
            },
            {
                "plate_number": "DL08KL8899",
                "vehicle_type": "CAR",
                "color": "Racing Green",
                "make_model": "Honda City",
                "is_ev": False,
                "is_flagged": False,
                "flag_reason": None
            }
        ]

        # Add procedural fleet
        generated_fleet = VehicleGenerator.generate_fleet(size=40, seed=42)
        for gen in generated_fleet:
            v_type_str = gen["vehicle_type"].value if hasattr(gen["vehicle_type"], "value") else str(gen["vehicle_type"])
            demo_profiles.append({
                "plate_number": gen["plate_number"],
                "vehicle_type": v_type_str,
                "color": gen["color"],
                "make_model": gen["make_model"],
                "is_ev": gen.get("is_ev", False),
                "is_flagged": gen.get("is_flagged", False),
                "flag_reason": gen.get("flag_reason")
            })

        print(f"[+] Seeding {len(demo_profiles)} vehicle registry records...")
        for vp in demo_profiles:
            veh = db.query(Vehicle).filter(Vehicle.plate_number == vp["plate_number"]).first()
            if not veh:
                veh = Vehicle(
                    plate_number=vp["plate_number"],
                    vehicle_type=vp["vehicle_type"],
                    color=vp["color"],
                    make_model=vp["make_model"],
                    is_ev=vp["is_ev"],
                    first_seen_at=now - timedelta(hours=3),
                    last_seen_at=now - timedelta(minutes=5),
                    is_flagged=vp["is_flagged"],
                    flag_reason=vp["flag_reason"]
                )
                db.add(veh)
            else:
                veh.vehicle_type = vp["vehicle_type"]
                veh.color = vp["color"]
                veh.make_model = vp["make_model"]
                veh.is_ev = vp["is_ev"]
                veh.is_flagged = vp["is_flagged"]
                veh.flag_reason = vp["flag_reason"]
        db.commit()
        print("    -> Vehicle profiles created.")

        # 3. Seed Detections
        print("[+] Seeding historical detections across checkpoints...")
        sample_detections = []

        # Target 1: DL04EQ9999 (Impossible travel scenario: CAM-01 then CAM-09 60s later)
        crop1 = vision_provider.generate_hsrp_plate_svg("DL04EQ9999", bg_color="#F8FAFC", text_color="#0F172A")
        sample_detections.append({
            "id": "det_seed_imp_1",
            "camera_id": "CAM-01",
            "plate_number": "DL04EQ9999",
            "ocr_plate_text": "DL04EQ9999",
            "ocr_confidence": 0.98,
            "vehicle_type": "SUV",
            "vehicle_color": "Cherry Red",
            "speed_kmh": 46.5,
            "fused_confidence": 0.98,
            "reid_hash": "A1B2C3D4E5F6",
            "synthetic_crop_svg": crop1,
            "timestamp": now - timedelta(minutes=15)
        })
        sample_detections.append({
            "id": "det_seed_imp_2",
            "camera_id": "CAM-09",
            "plate_number": "DL04EQ9999",
            "ocr_plate_text": "DL04EQ9999",
            "ocr_confidence": 0.97,
            "vehicle_type": "SUV",
            "vehicle_color": "Cherry Red",
            "speed_kmh": 650.0,
            "fused_confidence": 0.97,
            "reid_hash": "A1B2C3D4E5F6",
            "synthetic_crop_svg": crop1,
            "timestamp": now - timedelta(minutes=14)
        })

        # Target 2: HR26CL0001 (Cloned plate scenario: CAM-02 and CAM-07 within 30s)
        crop2 = vision_provider.generate_hsrp_plate_svg("HR26CL0001", bg_color="#F8FAFC", text_color="#0F172A")
        sample_detections.append({
            "id": "det_seed_cln_1",
            "camera_id": "CAM-02",
            "plate_number": "HR26CL0001",
            "ocr_plate_text": "HR26CL0001",
            "ocr_confidence": 0.96,
            "vehicle_type": "CAR",
            "vehicle_color": "Pearl White",
            "speed_kmh": 48.0,
            "fused_confidence": 0.96,
            "reid_hash": "F6E5D4C3B2A1",
            "synthetic_crop_svg": crop2,
            "timestamp": now - timedelta(minutes=18)
        })
        sample_detections.append({
            "id": "det_seed_cln_2",
            "camera_id": "CAM-07",
            "plate_number": "HR26CL0001",
            "ocr_plate_text": "HR26CL0001",
            "ocr_confidence": 0.95,
            "vehicle_type": "CAR",
            "vehicle_color": "Pearl White",
            "speed_kmh": 52.0,
            "fused_confidence": 0.95,
            "reid_hash": "F6E5D4C3B2A1",
            "synthetic_crop_svg": crop2,
            "timestamp": now - timedelta(minutes=17, seconds=30)
        })

        # Target 3: UP16AB1234 (Multi-hop trajectory: CAM-05 -> CAM-04 -> CAM-08 -> CAM-07)
        crop3 = vision_provider.generate_hsrp_plate_svg("UP16AB1234", bg_color="#15803D", text_color="#FFFFFF")
        trajectory_hops = [
            ("CAM-05", 40, 68.0),
            ("CAM-04", 31, 58.4),
            ("CAM-08", 22, 54.1),
            ("CAM-07", 10, 61.2),
        ]
        for idx, (cam_id, mins_ago, speed) in enumerate(trajectory_hops):
            sample_detections.append({
                "id": f"det_seed_up16_{idx}",
                "camera_id": cam_id,
                "plate_number": "UP16AB1234",
                "ocr_plate_text": "UP16AB1234",
                "ocr_confidence": 0.97,
                "vehicle_type": "CAR",
                "vehicle_color": "Deep Navy Blue",
                "speed_kmh": speed,
                "fused_confidence": 0.97,
                "reid_hash": "C3D4E5F6A1B2",
                "synthetic_crop_svg": crop3,
                "timestamp": now - timedelta(minutes=mins_ago)
            })

        # General network traffic: add 50+ background detections across all cameras
        cam_ids = [c["id"] for c in CAMERAS_SEED]
        for i in range(1, 45):
            veh_prof = demo_profiles[i % len(demo_profiles)]
            c_id = cam_ids[i % len(cam_ids)]
            bg_color = "#15803D" if veh_prof.get("is_ev") else "#F8FAFC"
            txt_color = "#FFFFFF" if veh_prof.get("is_ev") else "#0F172A"
            crop_svg = vision_provider.generate_hsrp_plate_svg(veh_prof["plate_number"], bg_color=bg_color, text_color=txt_color)
            sample_detections.append({
                "id": f"det_seed_gen_{i}",
                "camera_id": c_id,
                "plate_number": veh_prof["plate_number"],
                "ocr_plate_text": veh_prof["plate_number"],
                "ocr_confidence": round(0.92 + (i % 8) * 0.01, 2),
                "vehicle_type": veh_prof["vehicle_type"],
                "vehicle_color": veh_prof["color"],
                "speed_kmh": round(42.0 + (i % 25) * 1.5, 1),
                "fused_confidence": 0.95,
                "reid_hash": uuid.uuid4().hex[:12].upper(),
                "synthetic_crop_svg": crop_svg,
                "timestamp": now - timedelta(minutes=2 + (i * 2))
            })

        for det in sample_detections:
            existing = db.query(Detection).filter(Detection.id == det["id"]).first()
            if not existing:
                db_det = Detection(**det)
                db.add(db_det)
        db.commit()
        print(f"    -> Seeded {len(sample_detections)} telemetry detections.")

        # 4. Seed Realistic Initial Anomaly Alerts
        print("[+] Seeding system anomaly alerts...")
        demo_alerts = [
            {
                "id": "alt_seed_imp_01",
                "alert_type": "IMPOSSIBLE_TRAVEL",
                "severity": "CRITICAL",
                "plate_number": "DL04EQ9999",
                "camera_id": "CAM-09",
                "details_json": '{"calculated_speed_kmh": 650.0, "distance_km": 25.2, "elapsed_seconds": 60, "prev_camera_id": "CAM-01", "curr_camera_id": "CAM-09", "speed_limit_kmh": 90.0, "root_cause": "Calculated transit speed of 650.0 km/h exceeds physical corridor threshold of 140.0 km/h."}',
                "status": "ACTIVE",
                "created_at": now - timedelta(minutes=14)
            },
            {
                "id": "alt_seed_cln_01",
                "alert_type": "PLATE_CLONE",
                "severity": "CRITICAL",
                "plate_number": "HR26CL0001",
                "camera_id": "CAM-07",
                "details_json": '{"plate_number": "HR26CL0001", "camera_1": "CAM-02", "camera_2": "CAM-07", "time_delta_seconds": 30, "distance_km": 21.4, "root_cause": "Simultaneous discordant geographic sightings across distant camera nodes within 30 seconds."}',
                "status": "ACTIVE",
                "created_at": now - timedelta(minutes=17)
            },
            {
                "id": "alt_seed_spd_01",
                "alert_type": "SUSPICIOUS_ROUTE",
                "severity": "HIGH",
                "plate_number": "UP16AB1234",
                "camera_id": "CAM-08",
                "details_json": '{"plate_number": "UP16AB1234", "camera_id": "CAM-08", "flag_reason": "STOLEN_VEHICLE_REPORT_FIR_4011", "root_cause": "Flagged vehicle intercepted at Cantonment Corridor checkpoint."}',
                "status": "ACTIVE",
                "created_at": now - timedelta(minutes=22)
            }
        ]

        for alt in demo_alerts:
            existing = db.query(Alert).filter(Alert.id == alt["id"]).first()
            if not existing:
                db_alt = Alert(**alt)
                db.add(db_alt)
        db.commit()
        print("    -> Seeded initial anomaly alerts.")

        # Summary count verification
        total_cams = db.query(Camera).count()
        total_vehs = db.query(Vehicle).count()
        total_dets = db.query(Detection).count()
        total_alts = db.query(Alert).count()

        print("\n=======================================================")
        print(" DATABASE SEEDING COMPLETED SUCCESSFULLY")
        print("=======================================================")
        print(f"  • Cameras:    {total_cams}")
        print(f"  • Vehicles:   {total_vehs}")
        print(f"  • Detections: {total_dets}")
        print(f"  • Alerts:     {total_alts}")
        print("=======================================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
