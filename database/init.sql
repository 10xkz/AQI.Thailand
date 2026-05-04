CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    station_name TEXT NOT NULL,
    pm25_value NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO favorites (station_name, pm25_value) VALUES ('Bangkok Startup Station', 25.5);
