CREATE TABLE IF NOT EXISTS anomalies (
    id BIGSERIAL PRIMARY KEY,
    ip TEXT NOT NULL,
    time_window BIGINT NOT NULL,
    requests_per_window INTEGER NOT NULL,
    failed_logins INTEGER NOT NULL,
    model_name TEXT NOT NULL DEFAULT 'isolation_forest',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE anomalies
ADD COLUMN IF NOT EXISTS model_name TEXT NOT NULL DEFAULT 'isolation_forest';

CREATE INDEX IF NOT EXISTS idx_anomalies_ip ON anomalies (ip);
CREATE INDEX IF NOT EXISTS idx_anomalies_time_window ON anomalies (time_window);
