# 🏅 Garmin Analytics Dashboard

A personal triathlon training analytics platform built with **Streamlit**, powered by **Google Cloud Platform** (GCS + BigQuery). Data is automatically extracted from Garmin Connect, preprocessed, and stored in the cloud — then served as a rich, interactive dashboard.

---

## 🏗️ Architecture Overview

The system is separated into two distinct parts: an automated **Data Extraction & ETL Pipeline** and the interactive **Streamlit Dashboard App**.

### 1️⃣ Part 1: Data Extraction & Pipeline (ETL)
Data is automatically fetched on a schedule via GitHub Actions, cleaned, and warehoused in Google Cloud.

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        GARMIN CONNECT API                           │
│                    (garminconnect Python SDK)                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │  extract_weekly_activities.py
                             │  (Run automatically by GitHub Actions)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   GOOGLE CLOUD STORAGE (GCS)                        │
│  (Stores raw GPX, TCX, CSV, and Activity Metadata)                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │  preprocess_activities.py (Python ETL)
                             │  • Clean & normalize fields
                             │  • Standardize activity types
                             │  • Compute analytical columns
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GOOGLE BIGQUERY                                  │
│  (Data Warehouse: activities, races, logs)                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 2️⃣ Part 2: Interactive Dashboard Application
The frontend application is built in Streamlit and deployed as a web service via a **Docker container** on Render, serving processed analytics directly from BigQuery.

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT: RENDER (Docker container)            │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                STREAMLIT DASHBOARD (app.py)                   │  │
│  │   Stats │ Overview │ Run │ Swim │ Bike │ Race │ Results       │  │
│  └────────┬──────────────────────────────────────────────┬───────┘  │
│           │ sql_queries.py / utils_gcp.py                │          │
│           ▼                                              ▼          │
│   GOOGLE BIGQUERY                            GOOGLE CLOUD STORAGE   │
│   (Core Analytics & Data)                    (Raw details like GPX) │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Data Pipeline — Step by Step

### 1. Extraction — `utils/pipeline/extract_weekly_activities.py`
- Connects to Garmin Connect via `garminconnect` SDK (cookie-based auth)
- For each activity in a given week range:
  - Downloads **GPX** (GPS track), **TCX** (telemetry), **CSV** (splits)
  - Uploads raw files to **GCS** under `data/raw/YYYY-MM/{activityId}/`
  - Skips activities already present in GCS (deduplication)
  - Logs every upload result to the BigQuery `logs` table

### 2. Preprocessing — `utils/pipeline/preprocess_activities.py`
| Step | What it does |
|---|---|
| `load_and_clean_data` | Normalizes numeric types, computes Day/Week/Month columns |
| `split_biking_musculation_activities_2023` | Splits combined 2023 sessions into two separate rows |
| `harmonize_zwift_activities` | Fills missing HR from paired Cardio Zwift sessions |
| `standardize_activity_types` | Maps Garmin type keys → grouped types (cycling, running, swimming…) |
| `assign_periods` | Tags each activity with its associated race training period |
| `save_processed_data` | Uploads processed CSV to GCS + appends to BigQuery `activities` table (with deduplication) |

### 3. Workout summaries — `utils/pipeline/workout_summaries/`
After each weekly extract + preprocess, lap CSVs are parsed into BigQuery **`workout_summaries`** (race-prep scope only). See **[docs/workout_summaries.md](docs/workout_summaries.md)** for CLI, schema, parser version, and coach context strategy.

### 4. Dashboard querying — `utils/sql_queries.py`
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
└── utils/                      # Backend clients & configurations
    ├── sql_queries.py           # All BigQuery SQL queries
    ├── utils_gcp.py             # GCS + BigQuery clients
    │
    └── pipeline/                # ETL Data pipeline 
        ├── extract_weekly_activities.py  # Garmin → GCS pipeline
        ├── preprocess_activities.py      # Clean + label + upload
        ├── connect_to_garmin.py     # Garmin auth helper
        ├── garmin_cookies.py        # Cookie-based login
        └── create_weekly_stats.py   # Local aggregation utility
```

---

## 🚀 Tech details

### Prerequisites
- Python 3.11+
- A GCP project with BigQuery and Cloud Storage enabled
- A GCP Service Account key (JSON) with `BigQuery Data Editor` + `Storage Object Admin` roles
- A Garmin Connect account
- **Race coach (optional):** `GEMINI_API_KEY` in `.env` or Streamlit secrets. Coach uses **`gemini-3.1-flash-lite`** (`GEMINI_MODEL` optional override).

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