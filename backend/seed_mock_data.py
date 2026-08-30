"""
FloatChat AI — Mock Data Seeder
Populates PostgreSQL with sample ARGO data near Mumbai and Maldives
so that the stress test and globe can be verified.
"""
import sys
import os
import random
from datetime import datetime, timedelta

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.postgres import get_pool

def seed():
    print("🌊 Seeding FloatChat AI with mock ARGO data...")
    try:
        pool = get_pool()
        if not pool:
            print("⚠️ PostgreSQL pool unavailable. Skipping live DB seed.")
            return
    except Exception as e:
        print(f"⚠️ PostgreSQL unavailable ({e}). Skipping live DB seed.")
        return

    locations = [
        {"name": "Mumbai Near", "lat": 19.1, "lon": 72.9, "count": 5},
        {"name": "Maldives Near", "lat": 3.4, "lon": 73.2, "count": 5},
        {"name": "Arabian Sea Central", "lat": 15.0, "lon": 65.0, "count": 8},
        {"name": "Bay of Bengal", "lat": 12.0, "lon": 88.0, "count": 7},
        {"name": "Equatorial IO", "lat": 0.0, "lon": 80.0, "count": 5},
    ]

    platforms = [1902301, 1902302, 1902303, 1902304, 1902305, 5906781, 5906782]
    all_rows = []
    now = datetime.now()

    for loc in locations:
        count = int(loc["count"])
        base_lat = float(loc["lat"])
        base_lon = float(loc["lon"])
        for i in range(count):
            p_id = random.choice(platforms)
            lat = base_lat + random.uniform(-0.5, 0.5)
            lon = base_lon + random.uniform(-0.5, 0.5)
            time = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))

            all_rows.append((
                p_id, time, lat, lon,
                random.uniform(5.0, 10.0),
                random.uniform(25.0, 31.0),
                random.uniform(34.0, 36.5),
                random.uniform(180.0, 220.0),
                random.uniform(0.1, 0.8),
                random.uniform(0.1, 5.0),
                8.1
            ))

    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE public.marine_data CASCADE")
                sql = """
                    INSERT INTO public.marine_data (
                        platform_number, time, latitude, longitude,
                        pres, temp, psal, doxy, chla, nitrate, ph_in_situ_total
                    ) VALUES (
                        %(p_id)s, %(time)s, %(lat)s, %(lon)s,
                        %(pres)s, %(temp)s, %(psal)s, %(doxy)s, %(chla)s, %(nitrate)s, %(ph)s
                    )
                """
                for r in all_rows:
                    params = {
                        "p_id": r[0], "time": r[1], "lat": r[2], "lon": r[3],
                        "pres": r[4], "temp": r[5], "psal": r[6],
                        "doxy": r[7], "chla": r[8], "nitrate": r[9], "ph": r[10]
                    }
                    cur.execute(sql, params)

                conn.commit()
        print(f"✅ Successfully seeded {len(all_rows)} data points across {len(platforms)} floats.")
    except Exception as e:
        print(f"⚠️ Live DB seeding error: {e}")

if __name__ == "__main__":
    seed()
