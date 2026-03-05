# 🏅 Garmin Analytics Dashboard

A personal triathlon training analytics platform built with **Streamlit**, powered by **Google Cloud Platform** (GCS + BigQuery). Data is automatically extracted from Garmin Connect, preprocessed, and stored in the cloud — then served as a rich, interactive dashboard.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GARMIN CONNECT API                           │
│                    (garminconnect Python SDK)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │  extract_weekly_activities.py
                             │  (GPX · TCX · CSV · Metadata)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   GOOGLE CLOUD STORAGE (GCS)                        │
│                                                                     │
│  data/                                                              │
│  ├── raw/                                                           │
│  │   └── YYYY-MM/                                                   │
│  │       └── {activityId}/                                          │
│  │           ├── {activityId}.gpx        ← GPS track               │
│  │           ├── {activityId}.tcx        ← Telemetry (HR, cadence) │
│  │           ├── {activityId}.csv        ← Split data              │
│  │           └── {activityId}_information.csv  ← Summary metadata  │
│  └── processed/                                                     │
│      └── YYYY-MM/                                                   │
│          └── {date}_activities_processed_.csv                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │  preprocess_activities.py
                             │  • Clean & normalize fields
                             │  • Standardize activity types
                             │  • Assign training periods / race labels
                             │  • Compute Day / Week / Month columns
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GOOGLE BIGQUERY                                  │
│                                                                     │
│  Dataset: garmin_stats                                              │
│  ├── activities   ← All processed training activities               │
│  ├── races        ← Official race results                           │
│  └── logs         ← Upload processing audit log                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │  sql_queries.py  (query layer)
                             │  utils_gcp.py    (BigQuery client)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   STREAMLIT DASHBOARD  (app.py)                     │
│                                                                     │
│   Stats │ Overview │ Run │ Swim │ Bike │ Race │ Results             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Data Pipeline — Step by Step

### 1. Extraction — `utils/extract_weekly_activities.py`
- Connects to Garmin Connect via `garminconnect` SDK (cookie-based auth)
- For each activity in a given week range:
  - Downloads **GPX** (GPS track), **TCX** (telemetry), **CSV** (splits)
  - Uploads raw files to **GCS** under `data/raw/YYYY-MM/{activityId}/`
  - Skips activities already present in GCS (deduplication)
  - Logs every upload result to the BigQuery `logs` table

### 2. Preprocessing — `utils/preprocess_activities.py`
| Step | What it does |
|---|---|
| `load_and_clean_data` | Normalizes numeric types, computes Day/Week/Month columns |
| `split_biking_musculation_activities_2023` | Splits combined 2023 sessions into two separate rows |
| `harmonize_zwift_activities` | Fills missing HR from paired Cardio Zwift sessions |
| `standardize_activity_types` | Maps Garmin type keys → grouped types (cycling, running, swimming…) |
| `assign_periods` | Tags each activity with its associated race training period |
| `save_processed_data` | Uploads processed CSV to GCS + appends to BigQuery `activities` table (with deduplication) |

### 3. Dashboard querying — `utils/sql_queries.py`
All BigQuery queries are centralized here. The dashboard reads data live from BigQuery via `@st.cache_data` (1-hour TTL) to minimize API calls.

---

## 📊 Dashboard Tabs

| Tab | Description |
|---|---|
| **📊 Stats** | All-time personal records — longest day/week/month/year by sport, fastest speed, max elevation, best HR. Clickable rows show full activity telemetry. |
| **🏁 Overview** | Current-week snapshot across all sports. Includes a training volume chart (by week or month) and detailed sport breakdowns with delta vs. last period. |
| **🏃 Run** | Running-specific trends, recent activities table, and per-activity deep dive: GPS map, pace-per-split bar chart, and dual-axis TCX telemetry (HR, cadence, altitude, watts). |
| **🏊 Swim** | Swimming volume summary, weekly distance area chart, recent sessions, and per-session split details with pace bar chart. |
| **🚴 Bike** | Cycling volume summary, weekly distance trends, recent rides, and per-ride GPS map + dual-axis telemetry. |
| **🎯 Race** | Select a target race and review the full training block: preparation summary, weekly/monthly distance breakdown per sport, and total training load chart. |
| **🏅 Results** | Gallery of official race results (Triathlon & Running/Trail) with splits, transitions, rankings, and links to official results pages. |

---

## 🗂️ Project Structure

```
garmin_stats/
├── app.py                      # Streamlit entry point & navigation
├── requirements.txt
├── Dockerfile
├── .env                        # Local secrets (never committed)
│
├── assets/
│   └── style.css               # Custom dark theme + glassmorphism
│
├── tabs/                       # One module per dashboard tab
│   ├── tab_overview.py
│   ├── tab_running.py
│   ├── tab_swimming.py
│   ├── tab_cycling.py
│   ├── tab_race.py
│   ├── tab_races_results.py
│   └── tab_stats.py
│
├── actions/                    # Reusable UI + parsing helpers
│   ├── utils.py                # Charts, formatting, pagination
│   ├── utils_ui.py             # Glassmorphism metric/card components
│   ├── display_map.py          # GPX map rendering (Folium)
│   ├── display_pace_bar_plot.py # Pace split bar charts
│   └── parse_tcx_csv.py        # TCX / swimming CSV parsers
│
└── utils/                      # Backend data pipeline
    ├── sql_queries.py           # All BigQuery SQL queries
    ├── utils_gcp.py             # GCS + BigQuery clients
    ├── extract_weekly_activities.py  # Garmin → GCS pipeline
    ├── preprocess_activities.py      # Clean + label + upload
    ├── connect_to_garmin.py     # Garmin auth helper
    ├── garmin_cookies.py        # Cookie-based login
    ├── create_weekly_stats.py   # Local aggregation utility
    └── list_bq_tables.py        # BQ table debug helper
```

---

## 🚀 Running Locally

### Prerequisites
- Python 3.11+
- A GCP project with BigQuery and Cloud Storage enabled
- A GCP Service Account key (JSON) with `BigQuery Data Editor` + `Storage Object Admin` roles
- A Garmin Connect account

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/garmin_stats.git
cd garmin_stats

# 2. Create and activate a virtual environment
python -m venv garmin_stats_venv
garmin_stats_venv\Scripts\activate   # Windows
# source garmin_stats_venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your values (see below)

# 5. Run the dashboard
streamlit run app.py
```

### `.env` file

```env
GCP_PROJECT_ID=your-gcp-project-id
GCP_DATASET_ID=garmin_stats
GCP_BUCKET_NAME=your-gcs-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=credentials.json   # local only
USER_EMAIL=your-garmin-email@example.com
USER_PASSWORD=your-garmin-password
```

---

## 🐳 Running with Docker

```bash
# Build the image
docker build -t garmin-analytics .

# Run locally (mount your credentials)
docker run -p 8501:8501 \
  --env-file .env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  -v $(pwd)/credentials.json:/app/credentials.json \
  garmin-analytics
```

Then open [http://localhost:8501](http://localhost:8501).

---

## ☁️ Deploying on Render

1. Push your repo to GitHub (**do not commit** `credentials.json` or `.env`)
2. Create a new **Web Service** on Render pointing to your repo
3. Set **Start command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Add the following **Environment Variables** in Render's dashboard:

| Variable | Value |
|---|---|
| `GCP_PROJECT_ID` | your GCP project ID |
| `GCP_DATASET_ID` | `garmin_stats` |
| `GCP_BUCKET_NAME` | your GCS bucket name |
| `GOOGLE_CREDENTIALS_JSON` | *(paste full contents of credentials.json)* |

> ⚠️ For GCP auth on Render, use the `GOOGLE_CREDENTIALS_JSON` env var approach (see `utils_gcp.py`) instead of a credentials file.

---

## 🔒 Security Notes

- `credentials.json` is listed in `.gitignore` (`*.json`) — **never commit it**
- `.env` is listed in `.gitignore` — **never commit it**
- Rotate your GCP service account key periodically
- Use the principle of least privilege: only grant the service account the permissions it needs

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Dashboard | Streamlit |
| Charts | Plotly Express / Graph Objects |
| Maps | Folium + streamlit-folium |
| Data | pandas, pyarrow |
| Cloud Storage | Google Cloud Storage |
| Database | Google BigQuery |
| Garmin API | garminconnect (Python SDK) |
| Styling | Custom CSS — Glassmorphism dark theme |
| Font | Outfit (Google Fonts) |