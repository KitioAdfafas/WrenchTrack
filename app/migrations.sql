UPDATE jobs SET status_changed_at = date_received || ' 00:00:00'
WHERE status_changed_at IS NULL;

INSERT INTO status_history (job_id, from_status, to_status, changed_at)
SELECT id, NULL, status, status_changed_at FROM jobs
WHERE id NOT IN (SELECT job_id FROM status_history);
