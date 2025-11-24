def get_top_metrics_query(filter_condition):
    return f"""
        SELECT
            SUM(duration) AS total_movingDuration,
            SUM(distance) AS total_distance
        FROM activities
        WHERE {filter_condition};
    """

def get_activity_metrics_query(filter_condition):
    return f"""
        SELECT
            activityTypeGrouped,
            SUM(distance) AS total_distance
        FROM activities
        WHERE {filter_condition}
        GROUP BY activityTypeGrouped;
    """

def get_custom_metrics_query(filter_condition, column, aggregate_function):
    return f"""
        SELECT
            activityTypeGrouped,
            {aggregate_function}({column}) AS metric_value
        FROM activities
        WHERE {filter_condition}
        GROUP BY activityTypeGrouped;
    """

def get_latest_activity_query(sport_type, limit=1):
    return f"""
        SELECT *
        FROM activities
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
        FROM activities
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
                SELECT DISTINCT Week FROM activities
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
            FROM activities a
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

            -- Current week values
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

            -- Previous week values
            second.nb_trainings AS second_nb_trainings,
            second.total_duration AS second_total_duration,

            -- Deltas
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
    FROM activities
    WHERE activityTypeGrouped = '{sport_type}'
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
    time_filters = {
        '8_weeks': {
            'start': 'date("now", "-84 days", "weekday 1")',  # Start on Monday of 8 weeks ago
            'end': 'date("now", "weekday 1")'  # End on Monday of current week
        },
        '6_months': {
            'start': 'date("now", "-6 months", "weekday 1")',  # Start on Monday of 6 months ago
            'end': 'date("now", "weekday 1")'  # End on Monday of current week
        },
        'ytd': {
            'start': 'date(strftime("%Y", "now") || "-01-01", "weekday 1")',  # Start on the first Monday of the year
            'end': 'date("now", "weekday 1")'  # End on Monday of current week
        },
        'all': {
            'start': '(SELECT date(min(Week), "weekday 1") FROM activities WHERE activityTypeGrouped = "running")',
            'end': '(SELECT date(max(Week), "weekday 1") FROM activities WHERE activityTypeGrouped = "running")'
        }
    }

    start_date = time_filters[timerange]['start']
    end_date = time_filters[timerange]['end']
    
    return f"""
        WITH RECURSIVE date_series AS (
            SELECT {start_date} AS Week
            UNION ALL
            SELECT date(Week, '+7 days')
            FROM date_series
            WHERE date(Week, '+7 days') < {end_date}
        )
        SELECT 
            act.Day,    
            ROUND(act.distance, 2) as distance,
            time(act.duration, 'unixepoch') as duration, 
            act.calories, 
            act.averageHR,
            act.elevationGain,
            act.averageSpeed*3.6 as averageSpeed, 
            act.averageRunCadence, 
            act.elevationLoss, 
            act.maxHR, 
            act.minHR, 
            act.startTimeLocal,
            act.locationName, 
            act.activityName,
            act.activityId, 
            Round(act.trainingEffect,2) as trainingEffect,  
            act.trainingEffectLabel, 
            act.maxSpeed*3.6 as maxSpeed, 
            act.averageTemperature, 
            act.waterEstimated
        FROM activities act
        JOIN date_series ds
            ON strftime('%Y-%m-%d', ds.Week) = act.Week
         WHERE act.activityTypeGrouped = '{sport_type}'
        ORDER BY act.Day desc;
      
    """


def get_weekly_sport_query(sport_type, timerange):
    time_filters = {
        '8_weeks': {
            'start': 'date("now", "-84 days", "weekday 1")',
            'end': 'date("now", "weekday 1")'
        },
        '6_months': {
            'start': 'date("now", "-6 months", "weekday 1")',
            'end': 'date("now", "weekday 1")'
        },
        'ytd': {
            'start': 'date(strftime("%Y", "now") || "-01-01", "weekday 1")',
            'end': 'date("now", "weekday 1")'
        },
        'all': {
            'start': f'(SELECT date(min(Week), "weekday 1") FROM activities)',
            'end': f'(SELECT date(max(Week), "weekday 1") FROM activities)'
        }
    }

    start_date = time_filters[timerange]['start']
    end_date = time_filters[timerange]['end']

    # ---------- COMMON DATE SERIES ----------
    date_cte = f"""
        WITH RECURSIVE date_series AS (
            SELECT {start_date} AS Week
            UNION ALL
            SELECT date(Week, '+7 days')
            FROM date_series
            WHERE date(Week, '+7 days') < {end_date}
        )
    """

    # ---------- CASE 1: duration → sum all sports ----------
    if sport_type == "duration":
        return f"""
            {date_cte}
            SELECT
                ds.Week,
                COALESCE(SUM(a.duration), 0) AS total_duration
            FROM date_series ds
            LEFT JOIN activities a
                ON strftime('%Y-%m-%d', ds.Week)
                   = strftime('%Y-%m-%d', date(a.Week, 'weekday 1'))
            GROUP BY ds.Week
            ORDER BY ds.Week;
        """

    # ---------- CASE 2: only physical_reinforcement → count(*) ----------
    if sport_type == "physical_reinforcement":
        return f"""
            {date_cte}
            SELECT
                ds.Week,
                COALESCE(COUNT(a.Week), 0) AS nb_trainings
            FROM date_series ds
            LEFT JOIN activities a
                ON strftime('%Y-%m-%d', ds.Week)
                   = strftime('%Y-%m-%d', date(a.Week, 'weekday 1'))
                AND a.activityTypeGrouped = 'physical_reinforcement'
            GROUP BY ds.Week
            ORDER BY ds.Week;
        """

    # ---------- CASE 3: any sport → sum(distance) ----------
    return f"""
        {date_cte}
        SELECT
            ds.Week,
            COALESCE(SUM(a.distance), 0) AS total_distance
        FROM date_series ds
        LEFT JOIN activities a
            ON strftime('%Y-%m-%d', ds.Week)
               = strftime('%Y-%m-%d', date(a.Week, 'weekday 1'))
            AND a.activityTypeGrouped = '{sport_type}'
        GROUP BY ds.Week
        ORDER BY ds.Week;
    """



def get_biking_distance_by_timerange_query(timerange):
    time_filters = {
        '8_weeks': {
            'start': 'date("now", "-84 days", "weekday 1")',  # Start on Monday of 8 weeks ago
            'end': 'date("now", "weekday 1")'  # End on Monday of current week
        },
        '6_months': {
            'start': 'date("now", "-6 months", "weekday 1")',  # Start on Monday of 6 months ago
            'end': 'date("now", "weekday 1")'  # End on Monday of current week
        },
        'ytd': {
            'start': 'date(strftime("%Y", "now") || "-01-01", "weekday 1")',  # Start on the first Monday of the year
            'end': 'date("now", "weekday 1")'  # End on Monday of current week
        },
        'all': {
            'start': '(SELECT date(min(Week), "weekday 1") FROM activities WHERE activityTypeGrouped = "cycling")',
            'end': '(SELECT date(max(Week), "weekday 1") FROM activities WHERE activityTypeGrouped = "cycling")'
        }
    }

    start_date = time_filters[timerange]['start']
    end_date = time_filters[timerange]['end']

    return f"""
    WITH RECURSIVE date_series AS (
        SELECT {start_date} AS Week
        UNION ALL
        SELECT date(Week, '+7 days')
        FROM date_series
        WHERE date(Week, '+7 days') <= {end_date}
    )
    SELECT
        ds.Week,
        COALESCE(SUM(a.distance), 0) as total_distance
    FROM date_series ds
    LEFT JOIN activities a ON strftime('%Y-%m-%d', ds.Week) = strftime('%Y-%m-%d', date(a.Week, 'weekday 1'))
                          AND a.activityTypeGrouped = 'cycling'
    GROUP BY ds.Week
    ORDER BY ds.Week;
    """


def get_volume_metrics_query_overview():
    """
    Get race metrics for a specific training period
    """
    return f"""
        -- 1. Generate all weeks in the year
        WITH RECURSIVE date_series AS (
    SELECT date(strftime('%Y', 'now') || '-01-01') AS week
    UNION ALL
    SELECT date(week, '+7 days')
    FROM date_series
    WHERE week <= date('now')
),

week_data_raw AS (
    SELECT
        date(startTimeLocal, 'weekday 1', '-6 days') AS week,  -- aligns start of week to Monday
        SUM(duration) AS duration,
        COUNT(*) AS nb_trainings,
        SUM(distance) AS distance,
        SUM(calories) AS calories,
        SUM(elevationGain) AS elevationGain,
        CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
    FROM activities
    WHERE date(startTimeLocal) >= date(strftime('%Y', 'now') || '-01-01')
    GROUP BY week
),

week_data AS (
    SELECT
        ds.week,
        COALESCE(wd.duration, 0) AS duration,
        COALESCE(wd.nb_trainings, 0) AS nb_trainings,
        COALESCE(wd.distance, 0) AS distance,
        COALESCE(wd.calories, 0) AS calories,
        COALESCE(wd.elevationGain, 0) AS elevationGain,
        COALESCE(wd.averageHR, 0) AS averageHR,
        RANK() OVER (ORDER BY ds.week DESC) AS rank_week
    FROM date_series ds
    LEFT JOIN week_data_raw wd
        ON ds.week = wd.week
)

        -- 4. Aggregate last 1, 4, 12, 18, all weeks
        SELECT
            'last_1' AS name,
            SUM(duration) AS duration_total,
            SUM(duration) AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / NULLIF(SUM(duration),0) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week = 1

        UNION ALL

        SELECT
            'last_4' AS name,
            SUM(duration) AS duration_total,
            SUM(duration)/4 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance)/4 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / NULLIF(SUM(duration),0) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week <= 4


        UNION ALL

        SELECT
            "last_12" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) / 12 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) / 12 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week <= 12
        

        UNION ALL

        SELECT
            "last_18" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) / 18 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) / 18 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week <= 18  

        UNION ALL

        SELECT
            "last_all" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) / 18 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) / 18 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data 
    """   
    
def get_volume_metrics_query(sport):
    """
    Get race metrics for a specific training period
    """
    return f"""
        WITH week_data AS (
            SELECT
                week,
                SUM(duration) AS duration,
                COUNT(*) AS nb_trainings,
                SUM(distance) AS distance,
                SUM(calories) AS calories,
                SUM(elevationGain) AS elevationGain,
                CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR,
                RANK() OVER (ORDER BY week DESC) AS rank_week
            FROM activities
            WHERE activityTypeGrouped = '{sport}'
                AND date(startTimeLocal) >=   date(strftime('%Y', 'now') || '-01-01')
            GROUP BY week
        )
        SELECT
            "last_1" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week = 1

        UNION ALL

        SELECT
            "last_4" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) / 4 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) / 4 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week <= 4


        UNION ALL

        SELECT
            "last_12" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) / 12 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) / 12 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week <= 12
        

        UNION ALL

        SELECT
            "last_18" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) / 18 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) / 18 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data
        WHERE rank_week <= 18  

        UNION ALL

        SELECT
            "last_all" as name, 
            SUM(duration) AS duration_total,
            SUM(duration) / 18 AS duration_avg,
            SUM(nb_trainings) AS nb_trainings,
            SUM(distance) AS distance_total,
            SUM(distance) / 18 AS distance_avg,
            SUM(calories) AS calories,
            SUM(elevationGain) AS elevationGain,
            CAST(SUM(duration * averageHR) / SUM(duration) AS INTEGER) AS averageHR
        FROM week_data 
    """   
    
def get_race_metrics_query(start_date, end_date):
    """
    Get race metrics for a specific training period
    """
    return f"""
        WITH race_activities AS (
            SELECT *
            FROM activities
            WHERE date(startTimeLocal) BETWEEN '{start_date}' AND '{end_date}'
        ),
        weekly_stats AS (
            SELECT 
                Week,
                SUM(CASE WHEN activityTypeGrouped = 'swimming' THEN distance ELSE 0 END) AS week_swim_distance,
                SUM(CASE WHEN activityTypeGrouped = 'cycling' THEN distance ELSE 0 END) AS week_bike_distance,
                SUM(CASE WHEN activityTypeGrouped = 'running' THEN distance ELSE 0 END) AS week_run_distance,
                SUM(duration) AS week_duration
            FROM race_activities
            GROUP BY Week
        ),
        monthly_stats AS (
            SELECT 
                strftime('%Y-%m', startTimeLocal) AS month,
                SUM(CASE WHEN activityTypeGrouped = 'swimming' THEN distance ELSE 0 END) AS month_swim_distance,
                SUM(CASE WHEN activityTypeGrouped = 'cycling' THEN distance ELSE 0 END) AS month_bike_distance,
                SUM(CASE WHEN activityTypeGrouped = 'running' THEN distance ELSE 0 END) AS month_run_distance
            FROM race_activities
            GROUP BY strftime('%Y-%m', startTimeLocal)
        ),
        last_8_weeks AS (
            SELECT 
                AVG(week_duration) AS avg_duration_8w,
                AVG(week_swim_distance) AS avg_8w_swim,
                AVG(week_bike_distance) AS avg_8w_bike,
                AVG(week_run_distance) AS avg_8w_run
            FROM (
                SELECT week_duration, week_swim_distance, week_bike_distance, week_run_distance
                FROM weekly_stats
                ORDER BY Week DESC
                LIMIT 9 OFFSET 1  -- Skip the most recent week and take the next 8 weeks
            )
        )
                SELECT
            -- Total distances
            COALESCE((SELECT SUM(distance) FROM race_activities WHERE activityTypeGrouped = 'swimming'), 0) AS total_distance_swim,
            COALESCE((SELECT SUM(distance) FROM race_activities WHERE activityTypeGrouped = 'cycling'), 0) AS total_distance_bike,
            COALESCE((SELECT SUM(distance) FROM race_activities WHERE activityTypeGrouped = 'running'), 0) AS total_distance_run,
            -- Average weekly distances
            COALESCE((SELECT AVG(week_swim_distance) FROM weekly_stats), 0) AS average_week_distance_swim,
            COALESCE((SELECT AVG(week_bike_distance) FROM weekly_stats), 0) AS average_week_distance_bike,
            COALESCE((SELECT AVG(week_run_distance) FROM weekly_stats), 0) AS average_week_distance_run,
            -- Average last 8 weeks distances
            COALESCE((SELECT avg_8w_swim FROM last_8_weeks), 0) AS average_8week_distance_swim,
            COALESCE((SELECT avg_8w_bike FROM last_8_weeks), 0) AS average_8week_distance_bike,
            COALESCE((SELECT avg_8w_run FROM last_8_weeks), 0) AS average_8week_distance_run,
            -- Average monthly distances
            COALESCE((SELECT AVG(month_swim_distance) FROM monthly_stats), 0) AS average_month_distance_swim,
            COALESCE((SELECT AVG(month_bike_distance) FROM monthly_stats), 0) AS average_month_distance_bike,
            COALESCE((SELECT AVG(month_run_distance) FROM monthly_stats), 0) AS average_month_distance_run,
            -- Average durations
            COALESCE((SELECT AVG(week_duration) FROM weekly_stats), 0) AS average_duration_per_week,
            COALESCE((SELECT avg_duration_8w FROM last_8_weeks), 0) AS average_duration_last_8_weeks;
    """

def get_race_distance_by_timerange_query(start_date, end_date, granularity, sport_type):
    """
    Get distance data for graphs by sport and granularity, filling missing periods with 0
    """
    if granularity.lower() == 'week':
        return f"""
        WITH RECURSIVE date_series AS (
            SELECT date('{start_date}', 'weekday 0', '-6 days') AS week_start  -- Align start_date to the previous Monday
            UNION ALL
            SELECT date(week_start, '+7 days')
            FROM date_series
            WHERE date(week_start, '+7 days') <= date('{end_date}')
        )
        SELECT
            ds.week_start AS time_period,
            COALESCE(SUM(a.distance), 0) AS total_distance
        FROM date_series ds
        LEFT JOIN activities a ON date(a.startTimeLocal, 'weekday 0', '-6 days') = ds.week_start
                              AND date(a.startTimeLocal) BETWEEN '{start_date}' AND '{end_date}'
                              AND a.activityTypeGrouped = '{sport_type}'
        GROUP BY ds.week_start
        ORDER BY ds.week_start;
        """
    else:  # month
        return f"""
        WITH RECURSIVE date_series AS (
            SELECT date('{start_date}', 'start of month') AS month_start
            UNION ALL
            SELECT date(month_start, '+1 month')
            FROM date_series
            WHERE date(month_start, '+1 month') <= date('{end_date}', 'start of month')
        )
        SELECT
            ds.month_start AS time_period,
            COALESCE(SUM(a.distance), 0) AS total_distance
        FROM date_series ds
        LEFT JOIN activities a ON date(a.startTimeLocal, 'start of month') = ds.month_start
                              AND date(a.startTimeLocal) BETWEEN '{start_date}' AND '{end_date}'
                              AND a.activityTypeGrouped = '{sport_type}'
        GROUP BY ds.month_start
        ORDER BY ds.month_start;
        """


def get_activity_duration_by_granularity_query(start_date, end_date, granularity):
    if granularity == "week":
        # Calculate the first day of the week (Monday) for each record
        time_group = "date(startTimeLocal, 'weekday 0', '-6 days')"
    elif granularity == "month":
        time_group = "strftime('%Y-%m-01', startTimeLocal)"
    
    query = f"""
    SELECT 
        {time_group} AS TimePeriod,
        activityTypeGrouped,
        SUM(duration) AS Duration
    FROM activities
    WHERE date(startTimeLocal) BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY TimePeriod, activityTypeGrouped
    ORDER BY TimePeriod
    """
    return query

def activities_stats():
    """
    Load activity data from SQLite.
    If activity_type is provided → filter by activityTypeGrouped.
    """

    return f"""
        SELECT 
            activityId,
            activityName,
            locationName, 
            trainingRace,
            startTimeLocal,
            DATE(startTimeLocal) AS Day,
            Week,
            DATE(Month) AS Month,
            STRFTIME('%Y', startTimeLocal) AS Year,
            distance,
            duration,
            averageHR,
            averageSpeed*3.6 as averageSpeed,
            elevationGain,
            calories,
            averageTemperature,
            waterEstimated,
            activityTypeGrouped
        FROM activities
     """