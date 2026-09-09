"""Delhi NCR realistic camera network coordinates, zones, and road segments."""

CAMERAS_SEED = [
    {
        "id": "CAM-01",
        "name": "Connaught Place",
        "zone": "Central Delhi",
        "latitude": 28.6328,
        "longitude": 77.2197,
        "speed_limit_kmh": 40.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-02",
        "name": "India Gate Hexagon",
        "zone": "Central Delhi",
        "latitude": 28.6129,
        "longitude": 77.2295,
        "speed_limit_kmh": 50.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-03",
        "name": "ITO Junction / Vikas Marg",
        "zone": "East Delhi Link",
        "latitude": 28.6289,
        "longitude": 77.2415,
        "speed_limit_kmh": 50.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-04",
        "name": "AIIMS Flyover / Ring Road",
        "zone": "South Delhi",
        "latitude": 28.5672,
        "longitude": 77.2100,
        "speed_limit_kmh": 60.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-05",
        "name": "DND Flyway Toll Plaza",
        "zone": "Noida Border Expressway",
        "latitude": 28.5702,
        "longitude": 77.2884,
        "speed_limit_kmh": 80.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-06",
        "name": "Akshardham Setu",
        "zone": "East Delhi Highway",
        "latitude": 28.6139,
        "longitude": 77.2773,
        "speed_limit_kmh": 70.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-07",
        "name": "IGI Airport Terminal 3 Gateway",
        "zone": "South-West Delhi",
        "latitude": 28.5562,
        "longitude": 77.0856,
        "speed_limit_kmh": 60.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-08",
        "name": "Dhaula Kuan Interchange",
        "zone": "Cantonment Corridor",
        "latitude": 28.5921,
        "longitude": 77.1615,
        "speed_limit_kmh": 60.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-09",
        "name": "Cyber Hub Toll Corridor",
        "zone": "Gurugram Expressway",
        "latitude": 28.4950,
        "longitude": 77.0895,
        "speed_limit_kmh": 90.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-10",
        "name": "Kashmere Gate ISBT",
        "zone": "North Delhi Arterial",
        "latitude": 28.6675,
        "longitude": 77.2285,
        "speed_limit_kmh": 50.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-11",
        "name": "Nehru Place Outer Ring",
        "zone": "South Delhi Commercial",
        "latitude": 28.5494,
        "longitude": 77.2514,
        "speed_limit_kmh": 50.0,
        "status": "ACTIVE",
        "fps": 30
    },
    {
        "id": "CAM-12",
        "name": "Delhi-Meerut Expressway / Ghazipur",
        "zone": "East NCR Highway",
        "latitude": 28.6258,
        "longitude": 77.3298,
        "speed_limit_kmh": 90.0,
        "status": "ACTIVE",
        "fps": 30
    }
]

# Physical road connections between cameras (bidirectional with distance in KM)
ROAD_EDGES_SEED = [
    ("CAM-01", "CAM-02", 2.8),   # Connaught Place <-> India Gate
    ("CAM-01", "CAM-03", 2.6),   # Connaught Place <-> ITO
    ("CAM-01", "CAM-10", 4.2),   # Connaught Place <-> Kashmere Gate
    ("CAM-02", "CAM-03", 2.5),   # India Gate <-> ITO
    ("CAM-02", "CAM-04", 5.4),   # India Gate <-> AIIMS
    ("CAM-03", "CAM-06", 4.1),   # ITO <-> Akshardham
    ("CAM-03", "CAM-10", 4.8),   # ITO <-> Kashmere Gate
    ("CAM-04", "CAM-05", 8.2),   # AIIMS <-> DND Flyway
    ("CAM-04", "CAM-08", 6.1),   # AIIMS <-> Dhaula Kuan
    ("CAM-04", "CAM-11", 4.6),   # AIIMS <-> Nehru Place
    ("CAM-05", "CAM-06", 6.8),   # DND <-> Akshardham
    ("CAM-05", "CAM-11", 5.2),   # DND <-> Nehru Place
    ("CAM-06", "CAM-12", 5.8),   # Akshardham <-> Ghazipur DME
    ("CAM-07", "CAM-08", 8.4),   # Airport T3 <-> Dhaula Kuan
    ("CAM-07", "CAM-09", 9.1),   # Airport T3 <-> Cyber Hub
    ("CAM-08", "CAM-01", 8.5),   # Dhaula Kuan <-> Connaught Place
    ("CAM-08", "CAM-09", 11.2),  # Dhaula Kuan <-> Cyber Hub
]
