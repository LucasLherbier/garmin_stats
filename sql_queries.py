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
            act.activityId, 
                        act.trainingEffect,  
            act.trainingEffectLabel
       
        FROM activities act
        JOIN date_series ds
            ON strftime('%Y-%m-%d', ds.Week) = act.Week
         WHERE act.activityTypeGrouped = '{sport_type}'
        ORDER BY act.Day desc;
      
    """


def get_running_distance_by_timerange_query(timerange):
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
        ds.Week,
        COALESCE(SUM(a.distance), 0) as total_distance
    FROM date_series ds
    LEFT JOIN activities a ON strftime('%Y-%m-%d', ds.Week) = strftime('%Y-%m-%d', date(a.Week, 'weekday 1'))
                          AND a.activityTypeGrouped = 'running'
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
    else:  # Month
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
    if granularity == "Week":
        # Calculate the first day of the week (Monday) for each record
        time_group = "date(startTimeLocal, 'weekday 0', '-6 days')"
    elif granularity == "Month":
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
