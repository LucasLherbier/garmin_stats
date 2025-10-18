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
            SUM(duration) AS total_movingDuration,
            SUM(distance) AS total_distance
        FROM activities
        WHERE activityTypeGrouped = '{sport_type}'
        AND {period_column} = '{period_value}';
    """

def get_weekly_metrics_with_delta_query(sport_type):
    return """
        WITH WeeklyMetrics AS (
            SELECT 
                Week,
                SUM(duration) as total_duration,
                SUM(distance) as total_distance
            FROM activities 
            WHERE activityTypeGrouped = ? 
            GROUP BY Week
            ORDER BY Week DESC
            LIMIT 2
        )
        SELECT 
            first.total_duration as current_duration,
            first.total_distance as current_distance,
            (first.total_duration - second.total_duration) as duration_delta,
            (first.total_distance - second.total_distance) as distance_delta
        FROM (
            SELECT * FROM WeeklyMetrics LIMIT 1
        ) first
        LEFT JOIN (
            SELECT * FROM WeeklyMetrics LIMIT 1 OFFSET 1
        ) second;
    """

def get_recent_activities_query(sport_type, days=14):
    return f"""
        SELECT 
            startTimeLocal,
            activityName,
            distance,
            duration,
            averageHR,
            maxHR,
            trainingEffectLabel,
            locationName,
            differenceBodyBattery
        FROM activities
        WHERE activityTypeGrouped = '{sport_type}'
        AND startTimeLocal >= datetime('now', '-{days} days')
        ORDER BY startTimeLocal DESC;
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
