"""
HK-Link Logistics Management System (LMS) — v4.0 Full-Stack Backend
Course: COMP 3500SEF Software Engineering
Architecture: 3-Tier MVC (Presentation: HTML/Tailwind -> Business Logic: Flask REST API -> Persistence: SQLite 3)
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, render_template, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Secret key for signing HttpOnly session cookies (in production, load from environment variable)
app.secret_key = os.environ.get("LMS_SECRET_KEY", "hk-link-lms-comp3500sef-2026-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hk_link_lms.db")

# Strict 5-stage parcel lifecycle (FR-05 & NFR-02)
LIFECYCLE_STAGES = [
    "Order Created",
    "Picked Up",
    "Sorting Hub (Kwai Chung)",
    "Out for Delivery",
    "Delivered",
]

# Pre-configured Hong Kong Fleet & Drivers (Updated DRV-308 to Hui Ka Hing)
HK_DRIVERS = [
    {
        "id": "DRV-101",
        "name": "Chan Tai Man (陳大文)",
        "truckId": "TRK-HK-101",
        "routeZone": "Kowloon & Ho Man Tin",
        "phone": "+852 9188 2041",
        "maxCapacityKg": 120.0,
    },
    {
        "id": "DRV-204",
        "name": "Wong Ka Wai (黃家偉)",
        "truckId": "TRK-KLN-204",
        "routeZone": "Hong Kong Island (Central / Wan Chai)",
        "phone": "+852 9302 7719",
        "maxCapacityKg": 100.0,
    },
    {
        "id": "DRV-308",
        "name": "Hui Ka Hing (許家興)",
        "truckId": "TRK-NT-308",
        "routeZone": "New Territories (Sha Tin / Tsuen Wan)",
        "phone": "+852 6421 8803",
        "maxCapacityKg": 150.0,
    },
    {
        "id": "DRV-402",
        "name": "Ho Wan Sze (何韻詩)",
        "truckId": "TRK-EXP-402",
        "routeZone": "Cross-Harbour Express Priority",
        "phone": "+852 9811 5530",
        "maxCapacityKg": 80.0,
    },
]

# Pre-seeded Role-Based Accounts (Passwords hashed via Werkzeug before DB insert)
INITIAL_USERS = [
    ("admin", "admin123", "admin", "Logistics Manager (Admin)", None),
    ("driver_hui", "driver123", "driver", "Hui Ka Hing (許家興)", "DRV-308"),
    ("driver_chan", "driver123", "driver", "Chan Tai Man (陳大文)", "DRV-101"),
    ("driver_wong", "driver123", "driver", "Wong Ka Wai (黃家偉)", "DRV-204"),
    ("driver_ho", "driver123", "driver", "Ho Wan Sze (何韻詩)", "DRV-402"),
]

INITIAL_ORDERS = [
    {
        "id": "LMS-2026-001",
        "senderName": "Pacific Semiconductor HK Ltd",
        "originDistrict": "Sha Tin Science Park",
        "receiverName": "Prof. Kenneth Wong (MU Computing Lab)",
        "receiverPhone": "+852 2768 6800",
        "destAddress": "Block C, 30 Good Shepherd Street, Ho Man Tin, Kowloon",
        "weightKg": 14.5,
        "priority": "Express",
        "packageDesc": "AI Edge Server Blades (Fragile)",
        "status": "Out for Delivery",
        "driverId": "DRV-101",
        "createdAt": "2026-10-21 09:15",
        "estimatedDelivery": "2026-10-22 17:30",
        "history": [
            ("Order Created", "2026-10-21 09:15", "Sha Tin Science Park (Online Booking)", "Shipment order registered and barcode label generated."),
            ("Picked Up", "2026-10-21 11:40", "Sha Tin Science Park Phase 2", "Collected by courier Chan Tai Man (TRK-HK-101)."),
            ("Sorting Hub (Kwai Chung)", "2026-10-21 16:05", "Kwai Chung Logistics Hub (Terminal 4)", "Scanned through automated optical sorting line; routed to Kowloon Bay/Ho Man Tin cage."),
            ("Out for Delivery", "2026-10-22 09:30", "Ho Man Tin / Princess Margaret Rd Corridor", "Out for final delivery with driver Chan Tai Man (+852 9188 2041)."),
        ],
    },
    {
        "id": "LMS-2026-002",
        "senderName": "Harbour Luxury Watch Group",
        "originDistrict": "Tsim Sha Tsui Commercial Hub",
        "receiverName": "Ms. Vivian Chow",
        "receiverPhone": "+852 9088 1122",
        "destAddress": "Suite 3208, Two International Finance Centre (IFC), Central",
        "weightKg": 3.2,
        "priority": "Express",
        "packageDesc": "High-Value Retail Display Consignment",
        "status": "Delivered",
        "driverId": "DRV-402",
        "createdAt": "2026-10-20 10:00",
        "estimatedDelivery": "2026-10-21 15:00",
        "history": [
            ("Order Created", "2026-10-20 10:00", "Tsim Sha Tsui Canton Road Depot", "Express security manifest initialized."),
            ("Picked Up", "2026-10-20 11:15", "Tsim Sha Tsui Harbour City", "Picked up by Ho Wan Sze (TRK-EXP-402)."),
            ("Sorting Hub (Kwai Chung)", "2026-10-20 14:20", "Kwai Chung Logistics Hub (High-Value Vault)", "Cleared security X-ray and cross-docked for HK Island Express."),
            ("Out for Delivery", "2026-10-21 10:05", "Central / Western Harbour Crossing", "Dispatched to Central IFC reception."),
            ("Delivered", "2026-10-21 13:48", "Suite 3208, Two IFC, Central", "Delivered and signed by Receiver (V. Chow). Proof of delivery archived."),
        ],
    },
    {
        "id": "LMS-2026-003",
        "senderName": "Asia Cold-Chain Pharma Supply",
        "originDistrict": "Tsing Yi Cold & Dry Warehouse",
        "receiverName": "Queen Elizabeth Hospital Pharmacy",
        "receiverPhone": "+852 3506 8888",
        "destAddress": "30 Gascoigne Road, King's Park, Yau Ma Tei, Kowloon",
        "weightKg": 28.0,
        "priority": "Express",
        "packageDesc": "Temperature-Controlled Medical Reagents (2-8°C)",
        "status": "Sorting Hub (Kwai Chung)",
        "driverId": "DRV-101",
        "createdAt": "2026-10-22 07:45",
        "estimatedDelivery": "2026-10-22 19:00",
        "history": [
            ("Order Created", "2026-10-22 07:45", "Tsing Yi Cold & Dry Warehouse", "Cold-chain telemetry sensor paired with shipment."),
            ("Picked Up", "2026-10-22 09:10", "Tsing Yi Logistics Bay 12", "Loaded onto insulated truck TRK-HK-101."),
            ("Sorting Hub (Kwai Chung)", "2026-10-22 10:35", "Kwai Chung Logistics Hub (Cold Zone B)", "Undergoing hub consolidation for afternoon Kowloon hospital run."),
        ],
    },
    {
        "id": "LMS-2026-004",
        "senderName": "Global Air Freight Forwarders",
        "originDistrict": "Chek Lap Kok Air Cargo Hub",
        "receiverName": "Mr. Marcus Leung (Apex Retail)",
        "receiverPhone": "+852 6123 9980",
        "destAddress": "Unit 1105, Millennium City 5, 418 Kwun Tong Road, Kwun Tong",
        "weightKg": 42.0,
        "priority": "Standard",
        "packageDesc": "Imported Apparel Sample Cartons (6 Boxes)",
        "status": "Picked Up",
        "driverId": "DRV-308",
        "createdAt": "2026-10-22 08:20",
        "estimatedDelivery": "2026-10-23 18:00",
        "history": [
            ("Order Created", "2026-10-22 08:20", "Chek Lap Kok Air Cargo Terminal (AAT)", "Customs clearance completed; domestic waybill issued."),
            ("Picked Up", "2026-10-22 11:00", "Chek Lap Kok Cargo Apron", "Collected by driver Hui Ka Hing (TRK-NT-308); en route to Kwai Chung."),
        ],
    },
    {
        "id": "LMS-2026-005",
        "senderName": "Kowloon Book & Media Press",
        "originDistrict": "Kwun Tong Industrial Centre",
        "receiverName": "HKMU Library Acquisitions Dept",
        "receiverPhone": "+852 2768 6777",
        "destAddress": "30 Good Shepherd Street, Ho Man Tin, Kowloon",
        "weightKg": 19.5,
        "priority": "Standard",
        "packageDesc": "Software Engineering Reference Textbooks (30 Copies)",
        "status": "Order Created",
        "driverId": "",
        "createdAt": "2026-10-22 11:50",
        "estimatedDelivery": "2026-10-24 16:00",
        "history": [
            ("Order Created", "2026-10-22 11:50", "Kwun Tong Industrial Centre Phase 1", "Order submitted via Admin Portal; awaiting fleet dispatch."),
        ],
    },
    {
        "id": "LMS-2026-006",
        "senderName": "Cyberport FinTech Hardware Lab",
        "originDistrict": "Central Business District",
        "receiverName": "Ms. Chloe Tang",
        "receiverPhone": "+852 9555 3321",
        "destAddress": "Tower 2, Grand Central, Kwun Tong, Kowloon",
        "weightKg": 5.8,
        "priority": "Standard",
        "packageDesc": "POS Terminal Prototypes",
        "status": "Order Created",
        "driverId": "",
        "createdAt": "2026-10-22 12:15",
        "estimatedDelivery": "2026-10-24 18:00",
        "history": [
            ("Order Created", "2026-10-22 12:15", "Central Exchange Square Drop-off", "Order logged; pending driver assignment."),
        ],
    },
]


# =====================================================================
# TIER 3: DATA PERSISTENCE LAYER (SQLite 3 Relational Database)
# =====================================================================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(force_reset=False):
    conn = get_db()
    cur = conn.cursor()

    if force_reset:
        cur.executescript(
            """
            DROP TABLE IF EXISTS tracking_history;
            DROP TABLE IF EXISTS shipments;
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS drivers;
            """
        )

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS drivers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            truckId TEXT NOT NULL,
            routeZone TEXT,
            phone TEXT,
            maxCapacityKg REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'driver')),
            displayName TEXT NOT NULL,
            driverId TEXT,
            FOREIGN KEY (driverId) REFERENCES drivers(id)
        );

        CREATE TABLE IF NOT EXISTS shipments (
            id TEXT PRIMARY KEY,
            senderName TEXT NOT NULL,
            originDistrict TEXT NOT NULL,
            receiverName TEXT NOT NULL,
            receiverPhone TEXT NOT NULL,
            destAddress TEXT NOT NULL,
            weightKg REAL NOT NULL CHECK(weightKg > 0),
            priority TEXT NOT NULL,
            packageDesc TEXT,
            status TEXT NOT NULL,
            driverId TEXT,
            createdAt TEXT NOT NULL,
            estimatedDelivery TEXT,
            FOREIGN KEY (driverId) REFERENCES drivers(id)
        );

        CREATE TABLE IF NOT EXISTS tracking_history (
            logId INTEGER PRIMARY KEY AUTOINCREMENT,
            shipmentId TEXT NOT NULL,
            stage TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            location TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (shipmentId) REFERENCES shipments(id) ON DELETE CASCADE
        );
        """
    )

    # Seed initial records only if tables are empty
    driver_count = cur.execute("SELECT COUNT(*) FROM drivers").fetchone()[0]
    if driver_count == 0:
        for d in HK_DRIVERS:
            cur.execute(
                "INSERT INTO drivers VALUES (?, ?, ?, ?, ?, ?)",
                (d["id"], d["name"], d["truckId"], d["routeZone"], d["phone"], d["maxCapacityKg"]),
            )

    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        for uname, raw_pw, role, disp, drv_id in INITIAL_USERS:
            cur.execute(
                "INSERT INTO users (username, password_hash, role, displayName, driverId) VALUES (?, ?, ?, ?, ?)",
                (uname, generate_password_hash(raw_pw), role, disp, drv_id),
            )

    ship_count = cur.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    if ship_count == 0:
        for o in INITIAL_ORDERS:
            cur.execute(
                "INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    o["id"], o["senderName"], o["originDistrict"], o["receiverName"],
                    o["receiverPhone"], o["destAddress"], o["weightKg"], o["priority"],
                    o["packageDesc"], o["status"], o["driverId"] or None,
                    o["createdAt"], o["estimatedDelivery"],
                ),
            )
            for stage, ts, loc, note in o["history"]:
                cur.execute(
                    "INSERT INTO tracking_history (shipmentId, stage, timestamp, location, note) VALUES (?, ?, ?, ?, ?)",
                    (o["id"], stage, ts, loc, note),
                )

    conn.commit()
    conn.close()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def generate_next_tracking_id(conn):
    rows = conn.execute("SELECT id FROM shipments WHERE id LIKE 'LMS-2026-%'").fetchall()
    max_num = 0
    for r in rows:
        try:
            num = int(r["id"].split("-")[-1])
            if num > max_num:
                max_num = num
        except ValueError:
            pass
    return f"LMS-2026-{max_num + 1:03d}"


def build_shipment_dict(conn, row):
    d = dict(row)
    d["driverId"] = d["driverId"] or ""
    logs = conn.execute(
        "SELECT stage, timestamp, location, note FROM tracking_history WHERE shipmentId = ? ORDER BY logId ASC",
        (d["id"],),
    ).fetchall()
    d["history"] = [dict(l) for l in logs]
    return d


def get_transition_metadata(conn, order, next_stage):
    drv_text = "Duty Courier"
    if order.get("driverId"):
        drv = conn.execute("SELECT name, truckId FROM drivers WHERE id = ?", (order["driverId"],)).fetchone()
        if drv:
            drv_text = f"{drv['name']} ({drv['truckId']})"

    if next_stage == "Picked Up":
        return (
            order["originDistrict"],
            f"Parcel collected from sender by {drv_text} and scanned into handheld terminal.",
        )
    if next_stage == "Sorting Hub (Kwai Chung)":
        return (
            "Kwai Chung Logistics Hub (Automated Sorting Terminal 4)",
            "Arrived at Kwai Chung primary sorting facility; weight verified and routed to destination cage.",
        )
    if next_stage == "Out for Delivery":
        return (
            f"En Route to {order['destAddress']}",
            f"Dispatched for final-mile delivery with {drv_text}. Customer SMS notification sent.",
        )
    if next_stage == "Delivered":
        return (
            order["destAddress"],
            f"Successfully delivered and signed by {order['receiverName']}. Electronic Proof of Delivery (ePOD) archived.",
        )
    return (order["originDistrict"], f"Status updated to {next_stage}.")


# =====================================================================
# ROLE-BASED ACCESS CONTROL (RBAC) DECORATOR
# =====================================================================
def require_roles(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                return jsonify({"error": "Authentication required. Please sign in first."}), 401
            if allowed_roles and user["role"] not in allowed_roles:
                return jsonify({"error": f"Forbidden: Requires {' or '.join(allowed_roles)} role."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# =====================================================================
# PRESENTATION ROUTE
# =====================================================================
@app.route("/")
def index():
    return render_template("index.html")


# =====================================================================
# AUTHENTICATION API (LOGIN / LOGOUT / SESSION CHECK)
# =====================================================================
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    conn = get_db()
    user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not user_row or not check_password_hash(user_row["password_hash"], password):
        return jsonify({"error": "Invalid username or password. Access denied."}), 401

    user_payload = {
        "id": user_row["id"],
        "username": user_row["username"],
        "role": user_row["role"],
        "displayName": user_row["displayName"],
        "driverId": user_row["driverId"] or "",
    }
    session["user"] = user_payload
    return jsonify({"message": "Login successful", "user": user_payload}), 200


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.pop("user", None)
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/api/auth/me", methods=["GET"])
def api_me():
    user = session.get("user")
    return jsonify({"authenticated": bool(user), "user": user}), 200


# =====================================================================
# PUBLIC CUSTOMER TRACKING API (NO LOGIN REQUIRED - FR-07 & FR-08)
# =====================================================================
@app.route("/api/public/demo-ids", methods=["GET"])
def api_public_demo_ids():
    conn = get_db()
    rows = conn.execute("SELECT id, status FROM shipments ORDER BY id ASC").fetchall()
    conn.close()
    return jsonify({"items": [dict(r) for r in rows]}), 200


@app.route("/api/public/track/<tracking_id>", methods=["GET"])
def api_public_track(tracking_id):
    tid = tracking_id.strip().upper()
    conn = get_db()
    row = conn.execute("SELECT * FROM shipments WHERE UPPER(id) = ?", (tid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": f"Shipment Not Found ({tracking_id})", "code": 404}), 404

    order = build_shipment_dict(conn, row)
    driver_info = None
    if order["driverId"]:
        drv = conn.execute(
            "SELECT id, name, truckId, routeZone, phone FROM drivers WHERE id = ?",
            (order["driverId"],),
        ).fetchone()
        if drv:
            driver_info = dict(drv)
    conn.close()
    return jsonify({"shipment": order, "driver": driver_info}), 200


# =====================================================================
# PROTECTED OPERATIONS API (ADMIN & DRIVER PORTALS)
# =====================================================================
@app.route("/api/drivers", methods=["GET"])
@require_roles("admin", "driver")
def api_get_drivers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM drivers ORDER BY id ASC").fetchall()
    conn.close()
    return jsonify({"drivers": [dict(r) for r in rows]}), 200


@app.route("/api/shipments", methods=["GET"])
@require_roles("admin", "driver")
def api_get_shipments():
    user = session["user"]
    conn = get_db()
    if user["role"] == "driver":
        rows = conn.execute(
            "SELECT * FROM shipments WHERE driverId = ? ORDER BY id ASC",
            (user["driverId"],),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM shipments ORDER BY id ASC").fetchall()

    shipments = [build_shipment_dict(conn, r) for r in rows]
    next_id = generate_next_tracking_id(conn)
    conn.close()
    return jsonify({"shipments": shipments, "nextTrackingId": next_id}), 200


@app.route("/api/shipments", methods=["POST"])
@require_roles("admin")
def api_create_shipment():
    data = request.get_json(silent=True) or {}
    sender = (data.get("senderName") or "").strip()
    origin = (data.get("originDistrict") or "").strip()
    receiver = (data.get("receiverName") or "").strip()
    phone = (data.get("receiverPhone") or "").strip()
    dest = (data.get("destAddress") or "").strip()
    priority = data.get("priority") or "Standard"
    package_desc = (data.get("packageDesc") or "").strip() or "Standard Commercial Parcel"
    driver_id = (data.get("driverId") or "").strip() or None

    errors = []
    if not sender:
        errors.append("Sender Name / Company is required.")
    if not receiver:
        errors.append("Receiver Full Name is required.")
    if not phone:
        errors.append("Receiver Contact Phone is required.")
    if not dest:
        errors.append("Full Destination Address in Hong Kong is required.")
    try:
        weight = float(data.get("weightKg"))
        if weight <= 0 or weight > 500:
            errors.append("Parcel Weight must be a valid positive number between 0.1 kg and 500 kg.")
    except (TypeError, ValueError):
        errors.append("Parcel Weight must be a valid positive number between 0.1 kg and 500 kg.")

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    conn = get_db()
    tracking_id = generate_next_tracking_id(conn)
    ts = now_str()
    est = "Same-Day HK (By 19:00)" if priority == "Express" else "Next-Day HK (By 18:00)"

    drv_note = " Awaiting fleet dispatch."
    if driver_id:
        drv = conn.execute("SELECT name, truckId FROM drivers WHERE id = ?", (driver_id,)).fetchone()
        if drv:
            drv_note = f" Pre-assigned to {drv['name']} ({drv['truckId']})."

    init_note = f"Shipment registered via Admin Portal.{drv_note}"

    conn.execute(
        "INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (tracking_id, sender, origin, receiver, phone, dest, weight, priority, package_desc, "Order Created", driver_id, ts, est),
    )
    conn.execute(
        "INSERT INTO tracking_history (shipmentId, stage, timestamp, location, note) VALUES (?, ?, ?, ?, ?)",
        (tracking_id, "Order Created", ts, origin, init_note),
    )
    conn.commit()
    created = build_shipment_dict(conn, conn.execute("SELECT * FROM shipments WHERE id = ?", (tracking_id,)).fetchone())
    conn.close()
    return jsonify({"message": f"Created shipment {tracking_id}", "shipment": created}), 201


@app.route("/api/shipments/<order_id>", methods=["PUT"])
@require_roles("admin")
def api_update_shipment(order_id):
    data = request.get_json(silent=True) or {}
    sender = (data.get("senderName") or "").strip()
    origin = (data.get("originDistrict") or "").strip()
    receiver = (data.get("receiverName") or "").strip()
    phone = (data.get("receiverPhone") or "").strip()
    dest = (data.get("destAddress") or "").strip()
    priority = data.get("priority") or "Standard"
    package_desc = (data.get("packageDesc") or "").strip() or "Standard Commercial Parcel"
    driver_id = (data.get("driverId") or "").strip() or None

    errors = []
    if not sender:
        errors.append("Sender Name / Company is required.")
    if not receiver:
        errors.append("Receiver Full Name is required.")
    if not phone:
        errors.append("Receiver Contact Phone is required.")
    if not dest:
        errors.append("Full Destination Address in Hong Kong is required.")
    try:
        weight = float(data.get("weightKg"))
        if weight <= 0 or weight > 500:
            errors.append("Parcel Weight must be a valid positive number between 0.1 kg and 500 kg.")
    except (TypeError, ValueError):
        errors.append("Parcel Weight must be a valid positive number between 0.1 kg and 500 kg.")

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM shipments WHERE id = ?", (order_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Shipment not found"}), 404

    conn.execute(
        """
        UPDATE shipments
        SET senderName = ?, originDistrict = ?, receiverName = ?, receiverPhone = ?,
            destAddress = ?, weightKg = ?, priority = ?, packageDesc = ?, driverId = ?
        WHERE id = ?
        """,
        (sender, origin, receiver, phone, dest, weight, priority, package_desc, driver_id, order_id),
    )
    conn.commit()
    updated = build_shipment_dict(conn, conn.execute("SELECT * FROM shipments WHERE id = ?", (order_id,)).fetchone())
    conn.close()
    return jsonify({"message": f"Updated shipment {order_id}", "shipment": updated}), 200


@app.route("/api/shipments/<order_id>", methods=["DELETE"])
@require_roles("admin")
def api_delete_shipment(order_id):
    conn = get_db()
    existing = conn.execute("SELECT id FROM shipments WHERE id = ?", (order_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Shipment not found"}), 404

    conn.execute("DELETE FROM shipments WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Deleted shipment {order_id}"}), 200


@app.route("/api/shipments/<order_id>/assign", methods=["PATCH"])
@require_roles("admin")
def api_assign_driver(order_id):
    data = request.get_json(silent=True) or {}
    driver_id = (data.get("driverId") or "").strip() or None

    conn = get_db()
    order = conn.execute("SELECT * FROM shipments WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"error": "Shipment not found"}), 404

    drv = None
    if driver_id:
        drv = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
        if not drv:
            conn.close()
            return jsonify({"error": "Driver not found"}), 404

    conn.execute("UPDATE shipments SET driverId = ? WHERE id = ?", (driver_id, order_id))
    if drv:
        conn.execute(
            "INSERT INTO tracking_history (shipmentId, stage, timestamp, location, note) VALUES (?, ?, ?, ?, ?)",
            (order_id, order["status"], now_str(), "Kwai Chung Central Dispatch Desk", f"Assigned to courier {drv['name']} (Vehicle: {drv['truckId']})."),
        )
    conn.commit()
    updated = build_shipment_dict(conn, conn.execute("SELECT * FROM shipments WHERE id = ?", (order_id,)).fetchone())
    conn.close()
    msg = f"Assigned {drv['name']} to {order_id}" if drv else f"Unassigned driver from {order_id}"
    return jsonify({"message": msg, "shipment": updated}), 200


@app.route("/api/shipments/<order_id>/advance", methods=["POST"])
@require_roles("admin", "driver")
def api_advance_stage(order_id):
    user = session["user"]
    conn = get_db()
    row = conn.execute("SELECT * FROM shipments WHERE id = ?", (order_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Shipment not found"}), 404

    order = dict(row)
    # Drivers can only advance parcels assigned to them
    if user["role"] == "driver" and order["driverId"] != user["driverId"]:
        conn.close()
        return jsonify({"error": "Forbidden: This parcel is not assigned to your account."}), 403

    try:
        current_idx = LIFECYCLE_STAGES.index(order["status"])
    except ValueError:
        conn.close()
        return jsonify({"error": "Invalid current shipment status."}), 400

    if current_idx >= len(LIFECYCLE_STAGES) - 1:
        conn.close()
        return jsonify({"error": 'Shipment has already reached the final "Delivered" state.'}), 400

    # NFR-02 / TC-02 Business Rule: Must assign a driver before advancing past "Order Created"
    if current_idx == 0 and not order["driverId"]:
        conn.close()
        return jsonify({"error": 'Business Rule Violation: Assign a Driver / Truck before advancing from "Order Created" to "Picked Up".'}), 400

    next_stage = LIFECYCLE_STAGES[current_idx + 1]
    loc, note = get_transition_metadata(conn, order, next_stage)
    ts = now_str()

    conn.execute("UPDATE shipments SET status = ? WHERE id = ?", (next_stage, order_id))
    conn.execute(
        "INSERT INTO tracking_history (shipmentId, stage, timestamp, location, note) VALUES (?, ?, ?, ?, ?)",
        (order_id, next_stage, ts, loc, note),
    )
    conn.commit()
    updated = build_shipment_dict(conn, conn.execute("SELECT * FROM shipments WHERE id = ?", (order_id,)).fetchone())
    conn.close()
    return jsonify({"message": f'{order_id} transitioned to "{next_stage}"', "shipment": updated}), 200


# =====================================================================
# DATABASE EXPORT & RESET UTILITIES (ADMIN ONLY)
# =====================================================================
@app.route("/api/db/export", methods=["GET"])
@require_roles("admin")
def api_export_db():
    return send_file(DB_PATH, as_attachment=True, download_name="hk_link_lms_database.sqlite")


@app.route("/api/db/reset", methods=["POST"])
@require_roles("admin")
def api_reset_db():
    init_db(force_reset=True)
    return jsonify({"message": "SQLite database reset and re-seeded with default Hong Kong data!"}), 200


if __name__ == "__main__":
    init_db()
    print("=" * 65)
    print("  HK-Link Logistics Management System (LMS) v4.0 — Flask Server")
    print("  Open in browser: http://127.0.0.1:5000")
    print("  Admin Login:  admin / admin123")
    print("  Driver Login: driver_hui / driver123  (Hui Ka Hing 許家興)")
    print("=" * 65)
    app.run(host="127.0.0.1", port=5000, debug=True)
