"""
Optional one-time seed script. Run with `python seed_data.py`.
Pre-populates services (from njspacecleaning.com) with realistic pricing
units matched to how cleaning companies actually charge, and the
competitors identified so far. Rates are left blank (None) - fill them in
via the app as you gather real numbers.
"""

import db

db.init_db()

# (name, category, pricing_unit)
SERVICES = [
    ("Standard Cleaning", "Residential", "per hour"),
    ("Deep Cleaning", "Residential", "per hour"),
    ("Move-In Cleaning", "Residential", "flat rate"),
    ("Move-Out Cleaning", "Residential", "flat rate"),
    ("Office Cleaning", "Commercial", "per sq ft"),
    ("Post-Construction Cleaning", "Commercial", "per sq ft"),
    ("Event Venue Cleaning", "Commercial", "per event"),
    ("Warehouse Cleaning", "Commercial", "per sq ft"),
    ("Window Cleaning", "Specialty", "per room"),
    ("Tile & Grout Cleaning", "Specialty", "per room"),
    ("Eco-Friendly Cleaning", "Specialty", "per hour"),
]

COMPETITORS = [
    ("Beyond Clean Team", "https://www.beyondcleanteam.com/", "Union County, NJ"),
    ("CJM Cleaning", "https://www.cjmclean.com/", "Union County, NJ"),
    ("Cleaning World Inc.", "https://cleaningworldinc.com/", "Northern NJ"),
    ("Squeaky Clean Services", "https://squeakycleannj.com/", "NJ"),
    ("Jersey Garden Cleaning Company", "https://jerseygardencleaningcompany.com/", "NJ"),
    ("The Maids - Westfield", "https://www.maids.com/nj/westfield/", "Westfield, NJ"),
    ("The Cleaning Authority - Westfield", "https://www.thecleaningauthority.com/westfield/", "Westfield, NJ"),
    ("Cool Peaches Cleaning", "https://coolpeaches.com/", "NJ"),
]

EMPLOYEES = [
    ("Crew A", "Residential Team"),
    ("Crew B", "Commercial Team"),
]

existing_services = {s["name"] for s in db.get_services()}
for name, category, unit in SERVICES:
    if name not in existing_services:
        db.add_service(name, category, unit, None, "")

existing_competitors = {c["name"] for c in db.get_competitors()}
for name, website, area in COMPETITORS:
    if name not in existing_competitors:
        db.add_competitor(name, website, area, "")

existing_employees = {e["name"] for e in db.get_employees()}
for name, role in EMPLOYEES:
    if name not in existing_employees:
        db.add_employee(name, role)

print("Seed complete.")
print(f"Services: {len(db.get_services())}")
print(f"Competitors: {len(db.get_competitors())}")
print(f"Employees: {len(db.get_employees())}")
