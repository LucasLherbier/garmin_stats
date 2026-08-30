import os
from dotenv import load_dotenv

load_dotenv()
DATASET = os.getenv('GCP_DATASET_ID', 'garmin_stats')
ACTIVITIES = f"`{DATASET}.activities`"
RACES = f"`{DATASET}.races`"
WORKOUT_SUMMARIES = f"`{DATASET}.workout_summaries`"
DAILY_WELLNESS = f"`{DATASET}.daily_wellness`"

def get_top_metrics_query(filter_condition):
    # Note: filter_condition must be BQ compatible (e.g. using DATE() for Day)
    return f"""
        SELECT
            SUM(duration) AS total_movingDuration,
            SUM(distance) AS total_distance
        FROM {ACTIVITIES}
        WHERE {filter_condition};
    """

def get_activity_metrics_query(filter_condition):
    return f"""
        SELECT
            activityTypeGrouped,
            SUM(distance) AS total_distance
        FROM {ACTIVITIES}
        WHERE {filter_condition}
        GROUP BY activityTypeGrouped;
    """

def get_custom_metrics_query(filter_condition, column, aggregate_function):
    return f"""
        SELECT
            activityTypeGrouped,
            {aggregate_function}({column}) AS metric_value
        FROM {ACTIVITIES}
        WHERE {filter_condition}
        GROUP BY activityTypeGrouped;
    """

def get_latest_activity_query(sport_type, limit=1):
    return f"""
        SELECT *
        FROM {ACTIVITIES}
        WHERE activityTypeGrouped = '{sport_type}'
        ORDER BY startTimeLocal DESC
        LIMIT {limit};
    """
    
def get_metrics_for_period_query(sport_type, period_column, period_value):
    return f"""
        SELECT
            SUM(duration) AS total_duration,
            SUM(distance) AS total_distance,
            AVG(averageHR) AS avg_hr,
            AVG(elevationGain) AS avg_elevation_gain,
            AVG(calories) AS total_calories,
            AVG(maxHR) AS avg_max_hr,
            AVG(minHR) AS avg_min_hr,
            AVG(averageRunCadence) AS avg_run_cadence,
            AVG(averageSpeed) AS avg_speed,
            AVG(maxSpeed) AS avg_max_speed,
            AVG(averageTemperature) AS avg_temp,
            AVG(maxTemperature) AS avg_max_temp,
            AVG(minTemperature) AS avg_min_temp,
            SUM(waterEstimated) AS total_water_estimated,
            SUM(vigorousIntensityMinutes) AS total_vigorous_intensity
        FROM {ACTIVITIES}
        WHERE activityTypeGrouped = '{sport_type}'
        AND {period_column} = '{period_value}';
    """

def get_weekly_metrics_with_delta_query_overview():
    return f"""
        WITH DistinctWeeks AS (
            SELECT
                Week,
                ROW_NUMBER() OVER (ORDER BY Week DESC) AS week_rank
            FROM (
                SELECT DISTINCT Week FROM {ACTIVITIES}
                WHERE DATE(Week) < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
            ) w
        ),
        WeeklyMetrics AS (
            SELECT
                a.activityTypeGrouped, 
                a.Week,
                COUNT(*) AS nb_trainings,
                SUM(a.duration) AS total_duration,
                SUM(a.distance) AS total_distance,
                AVG(a.averageHR) AS avg_hr,
                SUM(a.elevationGain) AS total_elevation_gain,
                AVG(a.elevationGain) AS avg_elevation_gain,
                SUM(a.calories) AS total_calories,
                AVG(a.calories) AS avg_calories,
                MAX(a.maxHR) AS max_hr,
                MIN(a.minHR) AS min_hr,
                AVG(a.averageSpeed) AS avg_speed,
                SUM(a.waterEstimated) AS total_water_estimated,
                AVG(a.waterEstimated) AS avg_water_estimated,
                SUM(a.vigorousIntensityMinutes) AS total_vigorous_intensity,
                AVG(a.vigorousIntensityMinutes) AS avg_vigorous_intensity
            FROM {ACTIVITIES} a
            WHERE DATE(a.startTimeLocal) < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
            GROUP BY a.activityTypeGrouped, a.Week
        ), 
        data_raw AS (
            SELECT
                w.*,
                dw.week_rank
            FROM WeeklyMetrics w
            JOIN DistinctWeeks dw 
                ON w.Week = dw.Week
                AND dw.week_rank IN (1, 2)
        )
        SELECT
            first.activityTypeGrouped AS activityTypeGrouped, 
            first.Week AS current_week,
            first.nb_trainings AS current_nb_trainings,
            first.total_duration AS current_duration,
            first.total_distance AS current_distance,
            first.avg_hr AS current_avg_hr,
            first.total_elevation_gain AS current_total_elevation_gain,
            first.avg_elevation_gain AS current_avg_elevation_gain,
            first.total_calories AS current_total_calories,
            first.avg_calories AS current_avg_calories,
            first.max_hr AS current_max_hr,
            first.min_hr AS current_min_hr,
            first.avg_speed * 3.6 AS current_avg_speed,
            first.total_water_estimated AS current_total_water_estimated,
            first.avg_water_estimated AS current_avg_water_estimated,
            first.total_vigorous_intensity AS current_total_vigorous_intensity,
            first.avg_vigorous_intensity AS current_avg_vigorous_intensity,
            second.nb_trainings AS second_nb_trainings,
            second.total_duration AS second_total_duration,
            (first.total_duration - COALESCE(second.total_duration, 0)) AS duration_delta,
            (first.total_distance - COALESCE(second.total_distance, 0)) AS distance_delta,
            (first.avg_hr - COALESCE(second.avg_hr, 0)) AS avg_hr_delta,
            (first.avg_speed - COALESCE(second.avg_speed, 0)) * 3.6 AS avg_speed_delta
        FROM data_raw first
        LEFT JOIN data_raw second 
            ON first.activityTypeGrouped = second.activityTypeGrouped
            AND second.week_rank = 2   
        WHERE first.week_rank = 1;
    """
    
def get_weekly_metrics_with_delta_query(sport_type):
    return f"""
       WITH WeeklyMetrics AS (
            SELECT
                Week,
                SUM(duration) as total_duration,
                SUM(distance) as total_distance,
                AVG(averageHR) as avg_hr,
                SUM(elevationGain) as total_elevation_gain,
                AVG(elevationGain) as avg_elevation_gain,
                SUM(calories) as total_calories,
                AVG(calories) as avg_calories,
                MAX(maxHR) as max_hr,
                MIN(minHR) as min_hr,
                AVG(averageRunCadence) as avg_run_cadence,
                AVG(averageSpeed) as avg_speed,
                AVG(averageTemperature) as avg_temp,
                SUM(waterEstimated) as total_water_estimated,
                AVG(waterEstimated) as avg_water_estimated,
                SUM(vigorousIntensityMinutes) as total_vigorous_intensity,
                AVG(vigorousIntensityMinutes) as avg_vigorous_intensity
            FROM {ACTIVITIES}
            WHERE activityTypeGrouped = '{sport_type}'
            AND DATE(startTimeLocal) < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
            GROUP BY Week
            ORDER BY Week DESC
            LIMIT 2
        )
        SELECT
            first.Week as current_week,
            first.total_duration as current_duration,
            first.total_distance as current_distance,
            first.avg_hr as current_avg_hr,
            first.total_elevation_gain as current_total_elevation_gain,
            first.avg_elevation_gain as current_avg_elevation_gain,
            first.total_calories as current_total_calories,
            first.avg_calories as current_avg_calories,
            first.max_hr as current_max_hr,
            first.min_hr as current_min_hr,
            first.avg_run_cadence as current_avg_run_cadence,
            first.avg_speed * 3.6 as current_avg_speed,
            first.avg_temp as current_avg_temp,
            first.total_water_estimated as current_total_water_estimated,
            first.avg_water_estimated as current_avg_water_estimated,
            first.total_vigorous_intensity as current_total_vigorous_intensity,
            first.avg_vigorous_intensity as current_avg_vigorous_intensity,
            (first.total_duration - COALESCE(second.total_duration, 0)) as duration_delta,
            (first.total_distance - COALESCE(second.total_distance, 0)) as distance_delta,
            (first.avg_hr - COALESCE(second.avg_hr, 0)) as avg_hr_delta,
            (first.avg_run_cadence - COALESCE(second.avg_run_cadence, 0)) as avg_run_cadence_delta,
            (first.avg_speed - COALESCE(second.avg_speed, 0)) * 3.6 as avg_speed_delta,
            (first.avg_temp - COALESCE(second.avg_temp, 0)) as avg_temp_delta
        FROM (
            SELECT * FROM WeeklyMetrics LIMIT 1
        ) first
        LEFT JOIN (
            SELECT * FROM WeeklyMetrics LIMIT 1 OFFSET 1
        ) second ON 1=1;
    """

def get_recent_activities_query(sport_type, timerange):
    # Mapping old/new keys to a stable set
    if timerange == '8_weeks':
        timerange = '6_units'
    elif timerange == '6_months':
        timerange = '6_units'
        
    time_filters = {
        '4_units': {
            'start': 'DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 28 DAY), WEEK(MONDAY))',
            'end': 'DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))'
        },
        '6_units': {
            'start': 'DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 42 DAY), WEEK(MONDAY))',
            'end': 'DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))'
        },
        'ytd': {
            'start': 'DATE_TRUNC(DATE(EXTRACT(YEAR FROM CURRENT_DATE()), 1, 1), WEEK(MONDAY))',
            'end': 'DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))'
        },
        'all': {
            'start': f'(SELECT DATE_TRUNC(MIN(DATE(startTimeLocal)), WEEK(MONDAY)) FROM {ACTIVITIES})',
            'end': f'(SELECT DATE_TRUNC(MAX(DATE(startTimeLocal)), WEEK(MONDAY)) FROM {ACTIVITIES})'
        }
    }
    
    # Safety fallback
    if timerange not in time_filters:
        timerange = 'all'
        
    start_date = time_filters[timerange]['start']
    end_date = time_filters[timerange]['end']
    
    return f"""
        WITH date_series AS (
            SELECT Week FROM UNNEST(GENERATE_DATE_ARRAY({start_date}, {end_date}, INTERVAL 7 DAY)) AS Week
        )
        SELECT 
            act.Day,    
            act.activityTypeGrouped,
            act.activityId,
            ROUND(act.distance, 2) AS distance,
            FORMAT_TIMESTAMP('%H:%M:%S', TIMESTAMP_SECONDS(CAST(act.duration AS INT64))) AS duration, 
            act.calories, 
            act.averageHR,
            act.maxHR,
            act.minHR,
            act.totalNumberOfStrokes,
            act.averageStrokeDistance,
            act.averageSwimCadence,
            act.maxSwimCadence,
            ROUND(act.averageSpeed*3.6, 2) AS averageSpeed, 
            ROUND(act.maxSpeed*3.6, 2) AS maxSpeed, 
            act.averageSwolf,
            ROUND(act.trainingEffect,2) AS trainingEffect,  
            act.trainingEffectLabel, 
            act.moderateIntensityMinutes,
            act.vigorousIntensityMinutes,
            act.averageTemperature,
            act.maxTemperature,
            act.minTemperature,
            act.waterEstimated,
            act.elevationGain,
            act.elevationLoss,
            act.startTimeLocal,
            act.locationName,
            act.activityName
        FROM {ACTIVITIES} act
        JOIN date_series ds
            ON DATE(ds.Week) = DATE(act.Week)
        WHERE act.activityTypeGrouped = '{sport_type}'
        ORDER BY act.Day DESC;
    """

def get_all_races_query():
    return f"SELECT * FROM {RACES} ORDER BY date DESC"

def get_weekly_sport_query(sport_type, timerange, granularity='week'):
    # Backward compatibility for old time range keys
    if timerange == '8_weeks':
        timerange = '4_units' if granularity == 'month' else '6_units' # rough mapping
    elif timerange == '6_months':
        timerange = '6_units' if granularity == 'month' else 'all'
    
    time_trunc = "WEEK(MONDAY)" if granularity == 'week' else "MONTH"
    interval = "7 DAY" if granularity == 'week' else "1 MONTH"
    
    # Calculate intervals based on granularity
    if granularity == 'week':
        intervals = {
            '4_units': '28 DAY',
            '6_units': '42 DAY'
        }
    else:
        intervals = {
            '4_units': '4 MONTH',
            '6_units': '6 MONTH'
        }

    time_filters = {
        '4_units': {
            'start': f"DATE_SUB(CURRENT_DATE(), INTERVAL {intervals['4_units']})",
            'end': 'CURRENT_DATE()'
        },
        '6_units': {
            'start': f"DATE_SUB(CURRENT_DATE(), INTERVAL {intervals['6_units']})",
            'end': 'CURRENT_DATE()'
        },
        'ytd': {
            'start': 'DATE(EXTRACT(YEAR FROM CURRENT_DATE()), 1, 1)',
            'end': 'CURRENT_DATE()'
        },
        'all': {
            'start': f'(SELECT MIN(DATE(startTimeLocal)) FROM {ACTIVITIES})',
            'end': f'(SELECT MAX(DATE(startTimeLocal)) FROM {ACTIVITIES})'
        }
    }
    
    # Final safety check for missing keys if any other old key is used
    if timerange not in time_filters:
        timerange = 'all'
        
    start_date = time_filters[timerange]['start']
    end_date = time_filters[timerange]['end']

    date_series_sql = f"""
        UNNEST(GENERATE_DATE_ARRAY(
            DATE_TRUNC({start_date}, {time_trunc}), 
            DATE_TRUNC({end_date}, {time_trunc}), 
            INTERVAL {interval}
        ))
    """

    if sport_type == "duration":
        return f"""
            WITH date_series AS (SELECT period FROM {date_series_sql} AS period)
            SELECT
                ds.period AS Week,
                COALESCE(SUM(a.duration), 0) AS total_duration
            FROM date_series ds
            LEFT JOIN {ACTIVITIES} a ON DATE_TRUNC(DATE(a.startTimeLocal), {time_trunc}) = ds.period
            WHERE ds.period < DATE_TRUNC(CURRENT_DATE(), {time_trunc})
            GROUP BY ds.period
            ORDER BY ds.period;
        """
    
    return f"""
        WITH date_series AS (SELECT period FROM {date_series_sql} AS period)
        SELECT
            ds.period AS Week,
            COALESCE(SUM(a.distance), 0) AS total_distance
        FROM date_series ds
        LEFT JOIN {ACTIVITIES} a ON DATE_TRUNC(DATE(a.startTimeLocal), {time_trunc}) = ds.period
            AND a.activityTypeGrouped = '{sport_type}'
        WHERE ds.period < DATE_TRUNC(CURRENT_DATE(), {time_trunc})
        GROUP BY ds.period
        ORDER BY ds.period;
    """

def get_biking_distance_by_timerange_query(timerange):
    time_filters = {
        '8_weeks': {'start': 'DATE_SUB(CURRENT_DATE(), INTERVAL 84 DAY)', 'end': 'CURRENT_DATE()'},
        '6_months': {'start': 'DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)', 'end': 'CURRENT_DATE()'},
        'ytd': {'start': 'DATE(EXTRACT(YEAR FROM CURRENT_DATE()), 1, 1)', 'end': 'CURRENT_DATE()'},
        'all': {
            'start': f'(SELECT MIN(DATE(Week)) FROM {ACTIVITIES} WHERE activityTypeGrouped = "cycling")',
            'end': f'(SELECT MAX(DATE(Week)) FROM {ACTIVITIES} WHERE activityTypeGrouped = "cycling")'
        }
    }
    start_date = time_filters[timerange]['start']
    end_date = time_filters[timerange]['end']

    return f"""
    WITH date_series AS (
        SELECT Week FROM UNNEST(GENERATE_DATE_ARRAY(DATE_TRUNC({start_date}, WEEK(MONDAY)), DATE_TRUNC({end_date}, WEEK(MONDAY)), INTERVAL 7 DAY)) AS Week
    )
    SELECT
        ds.Week,
        COALESCE(SUM(a.distance), 0) as total_distance
    FROM date_series ds
    LEFT JOIN {ACTIVITIES} a ON DATE_TRUNC(DATE(a.startTimeLocal), WEEK(MONDAY)) = ds.Week
                          AND a.activityTypeGrouped = 'cycling'
    WHERE ds.Week < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
    GROUP BY ds.Week
    ORDER BY ds.Week;
    """

def get_volume_metrics_query_overview(granularity='week'):
    time_trunc = "WEEK(MONDAY)" if granularity == 'week' else "MONTH"
    interval = "7 DAY" if granularity == 'week' else "1 MONTH"
    
    return f"""
        WITH time_series AS (
            SELECT period
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_TRUNC(DATE(EXTRACT(YEAR FROM CURRENT_DATE()), 1, 1), {time_trunc}),
                DATE_TRUNC(CURRENT_DATE(), {time_trunc}),
                INTERVAL {interval}
            )) AS period
            WHERE period < DATE_TRUNC(CURRENT_DATE(), {time_trunc})
        ),
        activity_periods AS (
            SELECT
                DATE_TRUNC(DATE(startTimeLocal), {time_trunc}) AS period,
                SUM(duration) AS duration,
                COUNT(*) AS nb_trainings,
                SUM(distance) AS distance,
                SUM(calories) AS calories,
                SUM(elevationGain) AS elevationGain,
                SUM(totalNumberOfStrokes) AS totalNumberOfStrokes,
                SUM(duration * averageHR) AS total_hr_duration
            FROM {ACTIVITIES}
            WHERE EXTRACT(YEAR FROM startTimeLocal) = EXTRACT(YEAR FROM CURRENT_DATE())
            AND DATE_TRUNC(DATE(startTimeLocal), {time_trunc}) < DATE_TRUNC(CURRENT_DATE(), {time_trunc})
            GROUP BY period
        ),
        full_periods AS (
            SELECT
                ts.period,
                COALESCE(ap.duration, 0) AS duration,
                COALESCE(ap.nb_trainings, 0) AS nb_trainings,
                COALESCE(ap.distance, 0) AS distance,
                COALESCE(ap.calories, 0) AS calories,
                COALESCE(ap.elevationGain, 0) AS elevationGain,
                COALESCE(ap.totalNumberOfStrokes, 0) AS totalNumberOfStrokes,
                COALESCE(ap.total_hr_duration, 0) AS total_hr_duration,
                RANK() OVER (ORDER BY ts.period DESC) AS rank_period
            FROM time_series ts
            LEFT JOIN activity_periods ap ON ts.period = ap.period
        ),
        counts AS (
            SELECT
                COUNTIF(rank_period <= 1) AS c1,
                COUNTIF(rank_period <= 4) AS c4,
                COUNTIF(rank_period <= 12) AS c12,
                COUNTIF(rank_period <= 18) AS c18,
                COUNT(*) AS call
            FROM full_periods
        )
        SELECT 'last_1' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c1 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c1 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR FROM full_periods WHERE rank_period <= 1
        UNION ALL
        SELECT 'last_4' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c4 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c4 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR FROM full_periods WHERE rank_period <= 4
        UNION ALL
        SELECT 'last_12' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c12 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c12 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR FROM full_periods WHERE rank_period <= 12
        UNION ALL
        SELECT 'last_18' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c18 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c18 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR FROM full_periods WHERE rank_period <= 18
        UNION ALL
        SELECT 'last_all' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT call FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT call FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR FROM full_periods;
    """
   

def get_volume_metrics_query(sport, granularity='week'):
    time_trunc = "WEEK(MONDAY)" if granularity == 'week' else "MONTH"
    interval = "7 DAY" if granularity == 'week' else "1 MONTH"
    extra_metrics = """,
                CAST(SUM(total_swolf_duration) / NULLIF(SUM(swolf_duration), 0) AS INT64) AS averageSwolf,
                CAST(SUM(total_np_duration) / NULLIF(SUM(np_duration), 0) AS INT64) AS avgNpW"""
    
    return f"""
        WITH time_series AS (
            SELECT period
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_TRUNC(DATE(EXTRACT(YEAR FROM CURRENT_DATE()), 1, 1), {time_trunc}),
                DATE_TRUNC(CURRENT_DATE(), {time_trunc}),
                INTERVAL {interval}
            )) AS period
            WHERE period < DATE_TRUNC(CURRENT_DATE(), {time_trunc})
        ),
        activity_np AS (
            SELECT
                ws.activityId,
                AVG(SAFE_CAST(JSON_VALUE(lap, '$.normalized_power_w') AS FLOAT64)) AS avg_np_w
            FROM {WORKOUT_SUMMARIES} ws,
            UNNEST(JSON_QUERY_ARRAY(ws.laps)) AS lap
            WHERE ws.parse_status = 'ok'
              AND JSON_VALUE(lap, '$.normalized_power_w') IS NOT NULL
            GROUP BY ws.activityId
        ),
        activity_periods AS (
            SELECT
                DATE_TRUNC(DATE(a.startTimeLocal), {time_trunc}) AS period,
                SUM(a.duration) AS duration,
                COUNT(*) AS nb_trainings,
                SUM(a.distance) AS distance,
                SUM(a.calories) AS calories,
                SUM(a.elevationGain) AS elevationGain,
                SUM(a.totalNumberOfStrokes) AS totalNumberOfStrokes,
                SUM(a.duration * a.averageHR) AS total_hr_duration,
                SUM(CASE WHEN a.averageSwolf > 0 THEN a.duration * a.averageSwolf ELSE 0 END) AS total_swolf_duration,
                SUM(CASE WHEN a.averageSwolf > 0 THEN a.duration ELSE 0 END) AS swolf_duration,
                SUM(CASE WHEN np.avg_np_w > 0 THEN a.duration * np.avg_np_w ELSE 0 END) AS total_np_duration,
                SUM(CASE WHEN np.avg_np_w > 0 THEN a.duration ELSE 0 END) AS np_duration
            FROM {ACTIVITIES} a
            LEFT JOIN activity_np np ON a.activityId = np.activityId
            WHERE a.activityTypeGrouped = '{sport}'
            AND EXTRACT(YEAR FROM a.startTimeLocal) = EXTRACT(YEAR FROM CURRENT_DATE())
            AND DATE_TRUNC(DATE(a.startTimeLocal), {time_trunc}) < DATE_TRUNC(CURRENT_DATE(), {time_trunc})
            GROUP BY period
        ),
        full_periods AS (
            SELECT
                ts.period,
                COALESCE(ap.duration, 0) AS duration,
                COALESCE(ap.nb_trainings, 0) AS nb_trainings,
                COALESCE(ap.distance, 0) AS distance,
                COALESCE(ap.calories, 0) AS calories,
                COALESCE(ap.elevationGain, 0) AS elevationGain,
                COALESCE(ap.totalNumberOfStrokes, 0) AS totalNumberOfStrokes,
                COALESCE(ap.total_hr_duration, 0) AS total_hr_duration,
                COALESCE(ap.total_swolf_duration, 0) AS total_swolf_duration,
                COALESCE(ap.swolf_duration, 0) AS swolf_duration,
                COALESCE(ap.total_np_duration, 0) AS total_np_duration,
                COALESCE(ap.np_duration, 0) AS np_duration,
                RANK() OVER (ORDER BY ts.period DESC) AS rank_period
            FROM time_series ts
            LEFT JOIN activity_periods ap ON ts.period = ap.period
        ),
        counts AS (
            SELECT
                COUNTIF(rank_period <= 1) AS c1,
                COUNTIF(rank_period <= 4) AS c4,
                COUNTIF(rank_period <= 12) AS c12,
                COUNTIF(rank_period <= 18) AS c18,
                COUNT(*) AS call
            FROM full_periods
        )
        SELECT 'last_1' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c1 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c1 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR{extra_metrics} FROM full_periods WHERE rank_period <= 1
        UNION ALL
        SELECT 'last_4' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c4 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c4 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR{extra_metrics} FROM full_periods WHERE rank_period <= 4
        UNION ALL
        SELECT 'last_12' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c12 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c12 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR{extra_metrics} FROM full_periods WHERE rank_period <= 12
        UNION ALL
        SELECT 'last_18' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT c18 FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT c18 FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR{extra_metrics} FROM full_periods WHERE rank_period <= 18
        UNION ALL
        SELECT 'last_all' AS name, SUM(duration) AS duration_total, SUM(duration)/NULLIF((SELECT call FROM counts), 0) AS duration_avg, SUM(nb_trainings) AS nb_trainings, SUM(distance) AS distance_total, SUM(distance)/NULLIF((SELECT call FROM counts), 0) AS distance_avg, SUM(calories) AS calories, SUM(elevationGain) AS elevationGain, SUM(totalNumberOfStrokes) AS totalNumberOfStrokes, CAST(SUM(total_hr_duration) / NULLIF(SUM(duration),0) AS INT64) AS averageHR{extra_metrics} FROM full_periods;
    """

def get_race_metrics_query(start_date, end_date):
    return f"""
        WITH race_activities AS (
            SELECT * FROM {ACTIVITIES} WHERE DATE(startTimeLocal) >= '{start_date}' AND DATE(startTimeLocal) < '{end_date}'
        ),
        weekly_stats AS (
            SELECT Week,
                SUM(CASE WHEN activityTypeGrouped = 'swimming' THEN distance ELSE 0 END) AS week_swim_distance,
                SUM(CASE WHEN activityTypeGrouped = 'cycling' THEN distance ELSE 0 END) AS week_bike_distance,
                SUM(CASE WHEN activityTypeGrouped = 'running' THEN distance ELSE 0 END) AS week_run_distance,
                SUM(duration) AS week_duration,
                COUNT(*) AS week_sessions,
                SUM(elevationGain) AS week_elevation
            FROM race_activities
            GROUP BY Week
        ),
        monthly_stats AS (
            SELECT SUM(CASE WHEN activityTypeGrouped = 'swimming' THEN distance ELSE 0 END)/30.44 AS month_swim_distance, SUM(CASE WHEN activityTypeGrouped = 'cycling' THEN distance ELSE 0 END)/30.44 AS month_bike_distance, SUM(CASE WHEN activityTypeGrouped = 'running' THEN distance ELSE 0 END)/30.44 AS month_run_distance FROM race_activities
        ),
        last_8_weeks AS (
            SELECT
                AVG(week_duration) AS avg_duration_8w,
                AVG(week_swim_distance) AS avg_8w_swim,
                AVG(week_bike_distance) AS avg_8w_bike,
                AVG(week_run_distance) AS avg_8w_run,
                AVG(week_sessions) AS avg_8w_sessions,
                AVG(week_elevation) AS avg_8w_elevation
            FROM (
                SELECT week_duration, week_swim_distance, week_bike_distance, week_run_distance, week_sessions, week_elevation
                FROM weekly_stats
                ORDER BY Week DESC
                LIMIT 8 OFFSET 1
            )
        )
        SELECT
            COALESCE((SELECT SUM(duration) FROM race_activities), 0) AS total_duration,
            COALESCE((SELECT COUNT(*) FROM race_activities), 0) AS total_sessions,
            COALESCE((SELECT SUM(elevationGain) FROM race_activities), 0) AS total_elevation,
            COALESCE((SELECT SUM(distance) FROM race_activities WHERE activityTypeGrouped = 'swimming'), 0) AS total_distance_swim,
            COALESCE((SELECT SUM(distance) FROM race_activities WHERE activityTypeGrouped = 'cycling'), 0) AS total_distance_bike,
            COALESCE((SELECT SUM(distance) FROM race_activities WHERE activityTypeGrouped = 'running'), 0) AS total_distance_run,
            COALESCE((SELECT AVG(week_swim_distance) FROM weekly_stats), 0) AS average_week_distance_swim,
            COALESCE((SELECT AVG(week_bike_distance) FROM weekly_stats), 0) AS average_week_distance_bike,
            COALESCE((SELECT AVG(week_run_distance) FROM weekly_stats), 0) AS average_week_distance_run,
            COALESCE((SELECT AVG(week_sessions) FROM weekly_stats), 0) AS average_week_sessions,
            COALESCE((SELECT AVG(week_elevation) FROM weekly_stats), 0) AS average_week_elevation,
            COALESCE((SELECT avg_8w_swim FROM last_8_weeks), 0) AS average_8week_distance_swim,
            COALESCE((SELECT avg_8w_bike FROM last_8_weeks), 0) AS average_8week_distance_bike,
            COALESCE((SELECT avg_8w_run FROM last_8_weeks), 0) AS average_8week_distance_run,
            COALESCE((SELECT avg_8w_sessions FROM last_8_weeks), 0) AS average_8week_sessions,
            COALESCE((SELECT avg_8w_elevation FROM last_8_weeks), 0) AS average_8week_elevation,
            COALESCE((SELECT AVG(month_swim_distance) FROM monthly_stats), 0) AS average_month_distance_swim,
            COALESCE((SELECT AVG(month_bike_distance) FROM monthly_stats), 0) AS average_month_distance_bike,
            COALESCE((SELECT AVG(month_run_distance) FROM monthly_stats), 0) AS average_month_distance_run,
            COALESCE((SELECT AVG(week_duration) FROM weekly_stats), 0) AS average_duration_per_week,
            COALESCE((SELECT avg_duration_8w FROM last_8_weeks), 0) AS average_duration_last_8_weeks;
    """

def get_race_distance_by_timerange_query(start_date, end_date, granularity, sport_type):
    if granularity.lower() == 'week':
        return f"""
        WITH date_series AS (
            SELECT Week FROM UNNEST(GENERATE_DATE_ARRAY(DATE_TRUNC(DATE('{start_date}'), WEEK(MONDAY)), DATE_TRUNC(DATE('{end_date}'), WEEK(MONDAY)), INTERVAL 7 DAY)) AS Week
        )
        SELECT ds.Week AS time_period, COALESCE(SUM(a.distance), 0) AS total_distance
        FROM date_series ds
        LEFT JOIN {ACTIVITIES} a ON DATE_TRUNC(DATE(a.startTimeLocal), WEEK(MONDAY)) = ds.Week
                               AND DATE(a.startTimeLocal) >= '{start_date}' AND DATE(a.startTimeLocal) < '{end_date}'
                               AND a.activityTypeGrouped = '{sport_type}'
        WHERE ds.Week < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
        GROUP BY ds.Week ORDER BY ds.Week;
        """
    else:  # month
        return f"""
        WITH date_series AS (
            SELECT Month FROM UNNEST(GENERATE_DATE_ARRAY(DATE_TRUNC(DATE('{start_date}'), MONTH), DATE_TRUNC(DATE('{end_date}'), MONTH), INTERVAL 1 MONTH)) AS Month
        )
        SELECT ds.Month AS time_period, COALESCE(SUM(a.distance), 0) AS total_distance
        FROM date_series ds
        LEFT JOIN {ACTIVITIES} a ON DATE_TRUNC(DATE(a.startTimeLocal), MONTH) = ds.Month
                               AND DATE(a.startTimeLocal) >= '{start_date}' AND DATE(a.startTimeLocal) < '{end_date}'
                               AND a.activityTypeGrouped = '{sport_type}'
        WHERE ds.Month < DATE_TRUNC(CURRENT_DATE(), MONTH)
        GROUP BY ds.Month ORDER BY ds.Month;
        """

def get_race_wellness_by_granularity_query(start_date, end_date, granularity):
    if granularity == "week":
        time_trunc = "WEEK(MONDAY)"
        interval = "7 DAY"
        period_alias = "Week"
    else:
        time_trunc = "MONTH"
        interval = "1 MONTH"
        period_alias = "Month"

    return f"""
    WITH date_series AS (
        SELECT period AS {period_alias}
        FROM UNNEST(GENERATE_DATE_ARRAY(
            DATE_TRUNC(DATE('{start_date}'), {time_trunc}),
            DATE_TRUNC(DATE('{end_date}'), {time_trunc}),
            INTERVAL {interval}
        )) AS period
    ),
    wellness_daily AS (
        SELECT *
        FROM {DAILY_WELLNESS}
        WHERE day >= DATE('{start_date}')
          AND day <= DATE('{end_date}')
          AND extract_status IN ('ok', 'partial')
    ),
    wellness_periods AS (
        SELECT
            DATE_TRUNC(day, {time_trunc}) AS time_period,
            AVG(sleep_score) AS avg_sleep_score,
            AVG(hrv_last_night_avg) AS avg_hrv,
            AVG(resting_hr) AS avg_resting_hr,
            AVG(body_battery_high) AS avg_body_battery_high,
            AVG(body_battery_low) AS avg_body_battery_low,
            AVG(avg_stress) AS avg_stress,
            AVG(sleep_duration_sec) AS avg_sleep_duration_sec,
            COUNT(*) AS day_count
        FROM wellness_daily
        GROUP BY time_period
    )
    SELECT
        ds.{period_alias} AS time_period,
        wp.avg_sleep_score,
        wp.avg_hrv,
        wp.avg_resting_hr,
        wp.avg_body_battery_high,
        wp.avg_body_battery_low,
        wp.avg_stress,
        wp.avg_sleep_duration_sec,
        COALESCE(wp.day_count, 0) AS day_count
    FROM date_series ds
    LEFT JOIN wellness_periods wp ON ds.{period_alias} = wp.time_period
    WHERE ds.{period_alias} < DATE_TRUNC(CURRENT_DATE(), {time_trunc})
    ORDER BY ds.{period_alias};
    """


def get_race_wellness_daily_query(start_date, end_date):
    return f"""
    SELECT
        day AS time_period,
        sleep_score AS avg_sleep_score,
        hrv_last_night_avg AS avg_hrv,
        resting_hr AS avg_resting_hr,
        body_battery_high AS avg_body_battery_high,
        body_battery_low AS avg_body_battery_low,
        avg_stress AS avg_stress,
        sleep_duration_sec AS avg_sleep_duration_sec,
        1 AS day_count
    FROM {DAILY_WELLNESS}
    WHERE day >= DATE('{start_date}')
      AND day <= DATE('{end_date}')
      AND extract_status IN ('ok', 'partial')
    ORDER BY day;
    """


def get_race_activities_query(start_date, end_date, sport_types):
    if len(sport_types) == 1:
        sport_filter = f"act.activityTypeGrouped = '{sport_types[0]}'"
    else:
        joined = "', '".join(sport_types)
        sport_filter = f"act.activityTypeGrouped IN ('{joined}')"

    return f"""
        SELECT
            DATE(act.startTimeLocal) AS Day,
            act.activityTypeGrouped,
            act.activityId,
            ROUND(act.distance, 2) AS distance,
            act.duration,
            act.calories,
            act.averageHR,
            act.maxHR,
            ROUND(act.averageSpeed * 3.6, 2) AS averageSpeed,
            act.elevationGain,
            act.trainingEffectLabel,
            act.startTimeLocal,
            act.locationName,
            act.activityName
        FROM {ACTIVITIES} act
        WHERE DATE(act.startTimeLocal) >= '{start_date}'
          AND DATE(act.startTimeLocal) < '{end_date}'
          AND {sport_filter}
        ORDER BY act.startTimeLocal DESC;
    """


def get_activity_heatmap_query(sport_filter_sql: str) -> str:
    """Activity counts for current week by weekday (Mon=0) and time slot (AM/PM/EV)."""
    return f"""
        SELECT
            MOD(EXTRACT(DAYOFWEEK FROM startTimeLocal) + 5, 7) AS dow,
            CASE
                WHEN EXTRACT(HOUR FROM startTimeLocal) < 12 THEN 'AM'
                WHEN EXTRACT(HOUR FROM startTimeLocal) < 18 THEN 'PM'
                ELSE 'EV'
            END AS slot,
            COUNT(*) AS activity_count
        FROM {ACTIVITIES}
        WHERE DATE_TRUNC(DATE(startTimeLocal), WEEK(MONDAY)) = DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
          AND DATE(startTimeLocal) <= CURRENT_DATE()
          AND ({sport_filter_sql})
        GROUP BY dow, slot
        ORDER BY dow, slot
    """


def get_activity_duration_by_granularity_query(start_date, end_date, granularity):
    if granularity == "week":
        time_group = "DATE_TRUNC(DATE(startTimeLocal), WEEK(MONDAY))"
        limit_date = "DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))"
    else: # month
        time_group = "DATE_TRUNC(DATE(startTimeLocal), MONTH)"
        limit_date = "DATE_TRUNC(CURRENT_DATE(), MONTH)"
    
    return f"""
    SELECT 
        {time_group} AS TimePeriod,
        activityTypeGrouped,
        SUM(duration) AS Duration
    FROM {ACTIVITIES}
    WHERE DATE(startTimeLocal) >= '{start_date}' AND DATE(startTimeLocal) < '{end_date}'
    AND {time_group} < {limit_date}
    GROUP BY TimePeriod, activityTypeGrouped
    ORDER BY TimePeriod
    """

def activities_stats():
    return f"""
        SELECT 
            activityId,
            activityName,
            locationName, 
            trainingRace,
            startTimeLocal,
            DATE(startTimeLocal) AS Day,
            Week,
            DATE_TRUNC(DATE(startTimeLocal), MONTH) AS Month,
            EXTRACT(YEAR FROM startTimeLocal) AS Year,
            distance,
            duration,
            averageHR,
            averageSpeed*3.6 as averageSpeed,
            elevationGain,
            calories,
            averageTemperature,
            waterEstimated,
            activityTypeGrouped
        FROM {ACTIVITIES}
    """

def get_workout_summaries_prep_index_query(start_date, end_date):
    """Lightweight prep catalog for coach context (all scoped summaries in race window)."""
    return f"""
        SELECT
            activityId,
            startTimeLocal,
            sport,
            activityName,
            duration,
            distance,
            averageHR,
            structure_summary,
            parse_status
        FROM {WORKOUT_SUMMARIES}
        WHERE DATE(startTimeLocal) >= '{start_date}'
          AND DATE(startTimeLocal) < '{end_date}'
        ORDER BY startTimeLocal ASC
    """

def get_workout_summaries_recent_query(start_date, end_date, lookback_days=7):
    """Recent workouts with segment detail for weekly coach pass."""
    return f"""
        SELECT
            activityId,
            startTimeLocal,
            sport,
            activityName,
            duration,
            distance,
            averageHR,
            structure_summary,
            summary_text,
            segments,
            lap_analysis,
            parse_status
        FROM {WORKOUT_SUMMARIES}
        WHERE parse_status = 'ok'
          AND DATE(startTimeLocal) >= GREATEST(DATE('{start_date}'), DATE_SUB(DATE('{end_date}'), INTERVAL {int(lookback_days)} DAY))
          AND DATE(startTimeLocal) < '{end_date}'
        ORDER BY startTimeLocal DESC
    """

def get_workout_summary_detail_query(activity_id):
    return f"""
        SELECT
            activityId,
            startTimeLocal,
            sport,
            activityName,
            structure_summary,
            summary_text,
            segments,
            lap_analysis,
            laps,
            parse_status
        FROM {WORKOUT_SUMMARIES}
        WHERE activityId = {int(activity_id)}
        LIMIT 1
    """

def get_activities_by_date_query(selected_date):
    return f"""
        SELECT
            a.activityId,
            a.activityName,
            a.activityTypeGrouped,
            a.startTimeLocal,
            a.duration,
            a.distance,
            a.calories,
            a.averageHR,
            a.maxHR,
            a.elevationGain,
            a.averageSpeed,
            ws.sport AS summary_sport,
            ws.parse_status,
            ws.summary_text
        FROM {ACTIVITIES} a
        LEFT JOIN {WORKOUT_SUMMARIES} ws ON a.activityId = ws.activityId
        WHERE DATE(a.startTimeLocal) = DATE('{selected_date}')
        ORDER BY a.startTimeLocal ASC
    """

def get_activity_report_query(activity_id):
    return f"""
        SELECT
            a.activityId,
            a.activityName,
            a.activityTypeGrouped,
            a.startTimeLocal,
            a.duration,
            a.distance,
            a.calories,
            a.averageHR,
            a.maxHR,
            a.minHR,
            a.elevationGain,
            a.averageSpeed,
            a.maxSpeed,
            a.averageRunCadence,
            a.averageSwolf,
            a.locationName,
            a.trainingEffectLabel,
            ws.sport,
            ws.structure_summary,
            ws.summary_text,
            ws.segments,
            ws.laps,
            ws.parse_status
        FROM {ACTIVITIES} a
        LEFT JOIN {WORKOUT_SUMMARIES} ws ON a.activityId = ws.activityId
        WHERE a.activityId = {int(activity_id)}
        LIMIT 1
    """