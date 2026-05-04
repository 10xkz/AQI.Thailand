CREATE TABLE IF NOT EXISTS favorites (
      id SERIAL PRIMARY KEY,
      station_id TEXT,
      station_name TEXT NOT NULL,
      pm25_value NUMERIC,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

INSERT INTO favorites (station_id, station_name, pm25_value) VALUES ('bangkok_startup_station', 'Bangkok Startup Station', 25.5);
