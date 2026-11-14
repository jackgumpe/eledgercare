-- Runtime role privileges for the three F1 tables. Applied by the schema owner (eledgercare_migrator)
-- after migrations. The runtime role gets no UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER or DDL.
GRANT USAGE ON SCHEMA eledgercare TO eledgercare_app;
GRANT SELECT, INSERT ON TABLE
    eledgercare.documents,
    eledgercare.original_artifacts,
    eledgercare.processing_jobs
TO eledgercare_app;
