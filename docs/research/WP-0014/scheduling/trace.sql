CREATE SCHEMA IF NOT EXISTS wp0014;
CREATE TABLE IF NOT EXISTS wp0014.events (
  document_id uuid, status text, queued int, active int, recorded timestamptz DEFAULT clock_timestamp()
);
CREATE OR REPLACE FUNCTION wp0014.trace_transition() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
  INSERT INTO wp0014.events(document_id,status,queued,active)
  SELECT NEW.document_id, NEW.status, count(*) FILTER (WHERE status='queued'),
         count(*) FILTER (WHERE status='running') FROM eledgercare.processing_jobs;
  RETURN NEW;
END $$;
CREATE OR REPLACE TRIGGER wp0014_timing AFTER UPDATE OF status ON eledgercare.processing_jobs
FOR EACH ROW WHEN (OLD.status IS DISTINCT FROM NEW.status) EXECUTE FUNCTION wp0014.trace_transition();
