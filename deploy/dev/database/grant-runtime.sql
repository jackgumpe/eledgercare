-- Least-privilege runtime role grants for F1 + F2 + F3 + F4 tables in schema eledgercare.
-- Applied by the schema owner (eledgercare_migrator) after explicit EF Core migrations.
-- The runtime role (eledgercare_app) never receives DELETE, TRUNCATE, REFERENCES, TRIGGER, or DDL.
-- original_artifacts, accepted extraction_results, work_order_review_revisions, work_order_review_fields,
-- archive_result_projections, and archive_projection_units remain strictly append-only/immutable
-- (SELECT, INSERT only), and work_order_review_heads permits UPDATE exclusively on mutable head
-- pointer/status/timestamp columns (F3-BIC-02, F4-BIC-05).

GRANT USAGE ON SCHEMA eledgercare TO eledgercare_app;

GRANT USAGE, SELECT ON SEQUENCE eledgercare.extraction_fencing_seq TO eledgercare_app;

GRANT SELECT, INSERT ON TABLE
    eledgercare.documents,
    eledgercare.original_artifacts,
    eledgercare.processing_jobs,
    eledgercare.execution_attempts,
    eledgercare.extraction_results,
    eledgercare.work_order_review_revisions,
    eledgercare.work_order_review_fields,
    eledgercare.work_order_review_heads,
    eledgercare.archive_result_projections,
    eledgercare.archive_projection_units
TO eledgercare_app;

GRANT UPDATE (
    status,
    queued_at,
    updated_at,
    attempt_count,
    latest_fencing_token,
    retried_from_attempt_id
) ON TABLE eledgercare.processing_jobs TO eledgercare_app;

GRANT UPDATE (
    status,
    phase,
    launcher_pid,
    launcher_create_filetime,
    worker_pid,
    worker_create_filetime,
    last_heartbeat_at,
    ended_at,
    exit_code,
    failure_code,
    failure_detail,
    diagnostic_raw_output_utf8,
    diagnostic_metadata_json
) ON TABLE eledgercare.execution_attempts TO eledgercare_app;

GRANT UPDATE (
    current_revision_number,
    current_revision_id,
    current_status,
    updated_at
) ON TABLE eledgercare.work_order_review_heads TO eledgercare_app;
