import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

API_URL = (
    "https://api.data.stats.govt.nz/rest/data/"
    "STATSNZ,CEN18_HAD_001/"
    ".....2018"
    "?format=jsondata"
)

HEADERS = {
    "Ocp-Apim-Subscription-Key": "4438fa53f1e54ed093d06793b131e0b8",
    "Accept": "application/vnd.sdmx.data+json"
}

DB_CONFIG = {
    "dbname": "data-pipeline-api",
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
}

DATASET_ID   = "CEN18_HAD_001"
BATCH_SIZE   = 5000          # rows per bulk INSERT


# =========================================================
# FETCH DATA
# =========================================================

def fetch_data():

    print("📡 Fetching API data...")

    response = requests.get(
        API_URL,
        headers=HEADERS,
        timeout=120
    )

    print("Status Code:", response.status_code)
    response.raise_for_status()

    return response.json()


# =========================================================
# CREATE TABLE
# =========================================================

def create_table(conn):

    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS census_population (
                id             SERIAL PRIMARY KEY,
                dataset_id     TEXT,
                age_group      TEXT,
                area           TEXT,
                smoking_status TEXT,
                ethnicity      TEXT,
                sex            TEXT,
                period         TEXT,
                value          NUMERIC,
                created_at     TIMESTAMP DEFAULT NOW()
            );
        """)

    conn.commit()
    print("✅ Table ready")


# =========================================================
# TRANSFORM + LOAD  (bulk insert — one round-trip per batch)
# =========================================================

def transform_and_load(conn, data):

    print("🔄 Transforming data...")

    # --------------------------------------------------
    # ROOT STRUCTURE
    # --------------------------------------------------

    root      = data.get('data', data)
    dataset   = root.get('dataSets',   [{}])[0]
    structure = root.get('structures', [{}])[0]

    observations = dataset.get('observations', {})

    if not observations:
        print("❌ No observations found")
        return

    print(f"📊 Total observations: {len(observations)}")

    # --------------------------------------------------
    # BUILD DIMENSION LOOKUP
    # --------------------------------------------------

    dimensions = structure['dimensions']['observation']
    dim_map    = {}
    dim_values = []

    for index, dim in enumerate(dimensions):
        dim_map[dim['id']] = index
        dim_values.append(dim['values'])

    def get_dimension(dim_id, indexes):
        if dim_id not in dim_map:
            return None
        dim_index   = dim_map[dim_id]
        value_index = indexes[dim_index]
        return dim_values[dim_index][value_index]['name']

    # --------------------------------------------------
    # BUILD ROWS IN MEMORY  (no DB calls inside loop)
    # --------------------------------------------------

    rows    = []
    skipped = 0
    now     = datetime.now()          # single timestamp for entire run

    for key, val in observations.items():
        try:
            indexes = list(map(int, key.split(":")))

            value = val[0] if isinstance(val, list) else val
            if value is None:
                skipped += 1
                continue

            rows.append((
                DATASET_ID,
                get_dimension('AGE_CEN18_HAD_001',    indexes),
                get_dimension('AREA_CEN18_HAD_001',   indexes),
                get_dimension('CIG_CEN18_HAD_001',    indexes),
                get_dimension('ETHNIC_CEN18_HAD_001', indexes),
                get_dimension('SEX_CEN18_HAD_001',    indexes),
                get_dimension('YEAR_CEN18_HAD_001',   indexes),
                value,
                now,
            ))

        except Exception as e:
            print(f"❌ Transform error on key {key}: {e}")

    print(f"✅ Built {len(rows)} rows  ({skipped} skipped null values)")

    if not rows:
        print("⚠️  Nothing to insert.")
        return

    # --------------------------------------------------
    # BULK INSERT — one execute_values call per batch
    # --------------------------------------------------

    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE

    with conn.cursor() as cur:
        for batch_num, offset in enumerate(range(0, len(rows), BATCH_SIZE), start=1):
            batch = rows[offset : offset + BATCH_SIZE]

            execute_values(
                cur,
                """
                INSERT INTO census_population (
                    dataset_id, age_group, area, smoking_status,
                    ethnicity, sex, period, value, created_at
                ) VALUES %s
                """,
                batch,
                page_size=BATCH_SIZE
            )

            print(
                f"  ⬆  Batch {batch_num}/{total_batches} — "
                f"{min(offset + BATCH_SIZE, len(rows)):,}/{len(rows):,} rows inserted"
            )

    conn.commit()
    print(f"\n🎉 Committed {len(rows):,} rows to census_population")


# =========================================================
# MAIN
# =========================================================

def main():

    conn = None

    try:

        print("🚀 Starting pipeline")

        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ PostgreSQL connected")

        create_table(conn)

        data = fetch_data()
        print("✅ API data fetched")

        transform_and_load(conn, data)

        print("✅ Pipeline completed successfully")

    except Exception as e:
        print("❌ Pipeline failed:", e)

    finally:
        if conn:
            conn.close()
            print("✅ PostgreSQL connection closed")


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()