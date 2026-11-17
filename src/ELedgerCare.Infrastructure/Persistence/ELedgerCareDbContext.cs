using ELedgerCare.Domain.Archive;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Intake;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;
using Microsoft.EntityFrameworkCore;

namespace ELedgerCare.Infrastructure.Persistence;

public sealed class ELedgerCareDbContext(DbContextOptions<ELedgerCareDbContext> options) : DbContext(options)
{
    public const string Schema = "eledgercare";
    public const string IdempotencyKeyUniqueIndex = "ux_documents_idempotency_key";
    public const string DocumentsArchiveOrderIndex = "ix_documents_submitted_at_document_id_desc";
    public const string OneRunningAttemptIndex = "ux_execution_attempts_one_running_per_job";
    public const string AcceptedResultDocumentIndex = "ux_extraction_results_document_id";
    public const string ReviewRevisionIdempotencyKeyIndex = "ux_work_order_review_revisions_idempotency_key";
    public const string ReviewRevisionDocNumberIndex = "ux_work_order_review_revisions_document_revision";
    public const string ReviewRevisionResultNumberIndex = "ux_work_order_review_revisions_result_revision";
    public const string ReviewHeadResultIndex = "ux_work_order_review_heads_result_id";
    public const string ArchiveProjectionDocumentVersionIndex = "ux_archive_result_projections_document_version";
    public const string ArchiveProjectionUnitsDocumentIndex = "ix_archive_projection_units_document_version_ordinal";

    public DbSet<Document> Documents => Set<Document>();

    public DbSet<OriginalArtifact> OriginalArtifacts => Set<OriginalArtifact>();

    public DbSet<ProcessingJob> ProcessingJobs => Set<ProcessingJob>();

    public DbSet<ExecutionAttempt> ExecutionAttempts => Set<ExecutionAttempt>();

    public DbSet<ExtractionResult> ExtractionResults => Set<ExtractionResult>();

    public DbSet<WorkOrderReviewHead> WorkOrderReviewHeads => Set<WorkOrderReviewHead>();

    public DbSet<WorkOrderReviewRevision> WorkOrderReviewRevisions => Set<WorkOrderReviewRevision>();

    public DbSet<WorkOrderReviewField> WorkOrderReviewFields => Set<WorkOrderReviewField>();

    public DbSet<ArchiveResultProjection> ArchiveResultProjections => Set<ArchiveResultProjection>();

    public DbSet<ArchiveProjectionUnit> ArchiveProjectionUnits => Set<ArchiveProjectionUnit>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema(Schema);

        modelBuilder.HasSequence<long>("extraction_fencing_seq", Schema)
            .StartsAt(1)
            .IncrementsBy(1)
            .IsCyclic(false);

        modelBuilder.Entity<Document>(document =>
        {
            document.ToTable("documents");
            document.HasKey(d => d.DocumentId).HasName("pk_documents");
            document.Property(d => d.DocumentId).HasColumnName("document_id").ValueGeneratedNever();
            document.Property(d => d.IdempotencyKey).HasColumnName("idempotency_key").IsRequired();
            document.Property(d => d.SubmittedAtUtc).HasColumnName("submitted_at").HasColumnType("timestamptz").IsRequired();
            document.HasIndex(d => d.IdempotencyKey).IsUnique().HasDatabaseName(IdempotencyKeyUniqueIndex);
            document.HasIndex(d => new { d.SubmittedAtUtc, d.DocumentId })
                .IsDescending(true, true)
                .HasDatabaseName(DocumentsArchiveOrderIndex);

            document.HasOne(d => d.Original)
                .WithOne()
                .HasForeignKey<OriginalArtifact>(a => a.DocumentId)
                .HasConstraintName("fk_original_artifacts_documents")
                .OnDelete(DeleteBehavior.Restrict);

            document.HasOne(d => d.Job)
                .WithOne()
                .HasForeignKey<ProcessingJob>(j => j.DocumentId)
                .HasConstraintName("fk_processing_jobs_documents")
                .OnDelete(DeleteBehavior.Restrict);

            document.Navigation(d => d.Original).IsRequired();
            document.Navigation(d => d.Job).IsRequired();
        });

        modelBuilder.Entity<OriginalArtifact>(artifact =>
        {
            artifact.ToTable("original_artifacts", table =>
            {
                table.HasCheckConstraint("ck_original_artifacts_sha256_length",
                    $"octet_length(sha256) = {OriginalArtifact.Sha256Length}");
                table.HasCheckConstraint("ck_original_artifacts_byte_length_range",
                    $"byte_length BETWEEN 1 AND {AdmissionCeilings.MaxDocumentBytes}");
                table.HasCheckConstraint("ck_original_artifacts_byte_length_matches",
                    "byte_length = octet_length(bytes)");
                table.HasCheckConstraint("ck_original_artifacts_media_type",
                    $"media_type = '{OriginalArtifact.PdfMediaType}'");
                table.HasCheckConstraint("ck_original_artifacts_page_count_range",
                    $"page_count BETWEEN 1 AND {AdmissionCeilings.MaxPages}");
            });
            artifact.HasKey(a => a.DocumentId).HasName("pk_original_artifacts");
            artifact.Property(a => a.DocumentId).HasColumnName("document_id").ValueGeneratedNever();
            artifact.Property(a => a.Bytes).HasColumnName("bytes").HasColumnType("bytea").IsRequired();
            artifact.Property(a => a.Sha256).HasColumnName("sha256").HasColumnType("bytea").IsRequired();
            artifact.Property(a => a.ByteLength).HasColumnName("byte_length").IsRequired();
            artifact.Property(a => a.MediaType).HasColumnName("media_type").HasColumnType("text").IsRequired();
            artifact.Property(a => a.PageCount).HasColumnName("page_count").IsRequired();
        });

        modelBuilder.Entity<ProcessingJob>(job =>
        {
            job.ToTable("processing_jobs", table =>
            {
                table.HasCheckConstraint("ck_processing_jobs_status",
                    "status IN ('awaiting_extraction', 'queued', 'running', 'completed', 'failed', 'interrupted')");
                table.HasCheckConstraint("ck_processing_jobs_state_invariants",
                    "(status = 'awaiting_extraction' AND queued_at IS NULL AND attempt_count = 0 AND latest_fencing_token = 0 AND retried_from_attempt_id IS NULL) OR " +
                    "(status = 'queued' AND queued_at IS NOT NULL AND attempt_count >= 0 AND latest_fencing_token >= 0) OR " +
                    "(status IN ('running', 'completed', 'failed', 'interrupted') AND attempt_count >= 1 AND latest_fencing_token >= 1)");
            });
            job.HasKey(j => j.JobId).HasName("pk_processing_jobs");
            job.Property(j => j.JobId).HasColumnName("job_id").ValueGeneratedNever();
            job.Property(j => j.DocumentId).HasColumnName("document_id").IsRequired();
            job.HasIndex(j => j.DocumentId).IsUnique().HasDatabaseName("ux_processing_jobs_document_id");
            job.Property(j => j.Status)
                .HasColumnName("status")
                .HasColumnType("text")
                .HasConversion(status => status.ToWire(), value => ProcessingStatusNames.FromWire(value))
                .IsRequired();
            job.Property(j => j.RequestedAtUtc).HasColumnName("requested_at").HasColumnType("timestamptz").IsRequired();
            job.Property(j => j.QueuedAtUtc).HasColumnName("queued_at").HasColumnType("timestamptz");
            job.Property(j => j.UpdatedAtUtc).HasColumnName("updated_at").HasColumnType("timestamptz").IsRequired();
            job.Property(j => j.AttemptCount).HasColumnName("attempt_count").HasDefaultValue(0).IsRequired();
            job.Property(j => j.LatestFencingToken).HasColumnName("latest_fencing_token").HasDefaultValue(0L).IsRequired();
            job.Property(j => j.RetriedFromAttemptId).HasColumnName("retried_from_attempt_id");

            job.HasOne<ExecutionAttempt>()
                .WithMany()
                .HasForeignKey(j => j.RetriedFromAttemptId)
                .HasConstraintName("fk_processing_jobs_retried_from_attempt")
                .OnDelete(DeleteBehavior.Restrict);
            job.HasIndex(j => j.RetriedFromAttemptId).HasDatabaseName("ix_processing_jobs_retried_from_attempt_id");
        });

        modelBuilder.Entity<ExecutionAttempt>(attempt =>
        {
            attempt.ToTable("execution_attempts", table =>
            {
                table.HasCheckConstraint("ck_execution_attempts_status",
                    "status IN ('running', 'completed', 'failed', 'interrupted')");
                table.HasCheckConstraint("ck_execution_attempts_positive_ids",
                    "attempt_number >= 1 AND fencing_token >= 1 AND supervisor_pid > 0 AND supervisor_create_filetime > 0");
                table.HasCheckConstraint("ck_execution_attempts_ended_consistency",
                    "(status = 'running' AND ended_at IS NULL) OR (status <> 'running' AND ended_at IS NOT NULL)");
                table.HasCheckConstraint("ck_execution_attempts_failure_consistency",
                    "(status IN ('failed', 'interrupted') AND failure_code IS NOT NULL) OR (status IN ('running', 'completed') AND failure_code IS NULL)");
            });
            attempt.HasKey(a => a.AttemptId).HasName("pk_execution_attempts");
            attempt.Property(a => a.AttemptId).HasColumnName("attempt_id").ValueGeneratedNever();
            attempt.Property(a => a.JobId).HasColumnName("job_id").IsRequired();
            attempt.Property(a => a.DocumentId).HasColumnName("document_id").IsRequired();
            attempt.Property(a => a.AttemptNumber).HasColumnName("attempt_number").IsRequired();
            attempt.Property(a => a.FencingToken).HasColumnName("fencing_token").IsRequired();
            attempt.Property(a => a.RetriedFromAttemptId).HasColumnName("retried_from_attempt_id");
            attempt.Property(a => a.Status)
                .HasColumnName("status")
                .HasColumnType("text")
                .HasConversion(s => s.ToWire(), v => AttemptStatusNames.FromWire(v))
                .IsRequired();
            attempt.Property(a => a.Phase).HasColumnName("phase").HasColumnType("text").IsRequired();
            attempt.Property(a => a.RunDirectoryName).HasColumnName("run_directory_name").HasColumnType("text").IsRequired();
            attempt.Property(a => a.SupervisorInstanceId).HasColumnName("supervisor_instance_id").IsRequired();
            attempt.Property(a => a.SupervisorPid).HasColumnName("supervisor_pid").IsRequired();
            attempt.Property(a => a.SupervisorCreateFileTime).HasColumnName("supervisor_create_filetime").IsRequired();
            attempt.Property(a => a.LauncherPid).HasColumnName("launcher_pid");
            attempt.Property(a => a.LauncherCreateFileTime).HasColumnName("launcher_create_filetime");
            attempt.Property(a => a.WorkerPid).HasColumnName("worker_pid");
            attempt.Property(a => a.WorkerCreateFileTime).HasColumnName("worker_create_filetime");
            attempt.Property(a => a.StartedAtUtc).HasColumnName("started_at").HasColumnType("timestamptz").IsRequired();
            attempt.Property(a => a.LastHeartbeatAtUtc).HasColumnName("last_heartbeat_at").HasColumnType("timestamptz").IsRequired();
            attempt.Property(a => a.EndedAtUtc).HasColumnName("ended_at").HasColumnType("timestamptz");
            attempt.Property(a => a.ExitCode).HasColumnName("exit_code");
            attempt.Property(a => a.FailureCode).HasColumnName("failure_code").HasColumnType("text");
            attempt.Property(a => a.FailureDetail).HasColumnName("failure_detail").HasColumnType("text");
            attempt.Property(a => a.DiagnosticRawOutputUtf8).HasColumnName("diagnostic_raw_output_utf8").HasColumnType("text");
            attempt.Property(a => a.DiagnosticMetadataJson).HasColumnName("diagnostic_metadata_json").HasColumnType("jsonb");

            attempt.HasOne<ProcessingJob>()
                .WithMany()
                .HasForeignKey(a => a.JobId)
                .HasConstraintName("fk_execution_attempts_processing_jobs")
                .OnDelete(DeleteBehavior.Restrict);

            attempt.HasOne<Document>()
                .WithMany()
                .HasForeignKey(a => a.DocumentId)
                .HasConstraintName("fk_execution_attempts_documents")
                .OnDelete(DeleteBehavior.Restrict);

            attempt.HasOne<ExecutionAttempt>()
                .WithMany()
                .HasForeignKey(a => a.RetriedFromAttemptId)
                .HasConstraintName("fk_execution_attempts_retried_from")
                .OnDelete(DeleteBehavior.Restrict);

            attempt.HasIndex(a => new { a.JobId, a.AttemptNumber })
                .IsUnique()
                .HasDatabaseName("ux_execution_attempts_job_attempt_number");
            attempt.HasIndex(a => a.FencingToken)
                .IsUnique()
                .HasDatabaseName("ux_execution_attempts_fencing_token");
            attempt.HasIndex(a => a.JobId)
                .IsUnique()
                .HasFilter("status = 'running'")
                .HasDatabaseName(OneRunningAttemptIndex);
            attempt.HasIndex(a => a.DocumentId).HasDatabaseName("ix_execution_attempts_document_id");
            attempt.HasIndex(a => a.RetriedFromAttemptId).HasDatabaseName("ix_execution_attempts_retried_from_attempt_id");
        });

        modelBuilder.Entity<ExtractionResult>(result =>
        {
            result.ToTable("extraction_results", table =>
            {
                table.HasCheckConstraint("ck_extraction_results_schema",
                    $"schema_version = '{ExtractionCeilings.EnvelopeSchema}'");
                table.HasCheckConstraint("ck_extraction_results_digests",
                    "octet_length(input_sha256) = 32 AND octet_length(raw_output_sha256) = 32 AND " +
                    "octet_length(model_manifest_sha256) = 32 AND octet_length(dependency_lock_sha256) = 32 AND " +
                    "octet_length(worker_source_digest) = 32 AND octet_length(worker_config_digest) = 32");
                table.HasCheckConstraint("ck_extraction_results_raw_length_matches",
                    $"raw_output_byte_length BETWEEN 1 AND {ExtractionCeilings.MaxRawOutputBytes} AND raw_output_byte_length = octet_length(raw_output_bytes)");
                table.HasCheckConstraint("ck_extraction_results_page_bounds",
                    $"page_count BETWEEN 1 AND {ExtractionCeilings.MaxExtractionPages} AND output_page_count = page_count");
                table.HasCheckConstraint("ck_extraction_results_finish_reason",
                    $"finish_reason = '{ExtractionCeilings.StopFinishReason}'");
                table.HasCheckConstraint("ck_extraction_results_durations",
                    "load_duration_ms >= 0 AND render_duration_ms >= 0 AND infer_duration_ms >= 0 AND total_duration_ms >= 0");
            });
            result.HasKey(r => r.ResultId).HasName("pk_extraction_results");
            result.Property(r => r.ResultId).HasColumnName("result_id").ValueGeneratedNever();
            result.Property(r => r.DocumentId).HasColumnName("document_id").IsRequired();
            result.Property(r => r.JobId).HasColumnName("job_id").IsRequired();
            result.Property(r => r.AttemptId).HasColumnName("attempt_id").IsRequired();
            result.Property(r => r.FencingToken).HasColumnName("fencing_token").IsRequired();
            result.Property(r => r.SchemaVersion).HasColumnName("schema_version").HasColumnType("text").IsRequired();
            result.Property(r => r.InputSha256).HasColumnName("input_sha256").HasColumnType("bytea").IsRequired();
            result.Property(r => r.InputByteLength).HasColumnName("input_byte_length").IsRequired();
            result.Property(r => r.PageCount).HasColumnName("page_count").IsRequired();
            result.Property(r => r.RawOutputBytes).HasColumnName("raw_output_bytes").HasColumnType("bytea").IsRequired();
            result.Property(r => r.RawOutputByteLength).HasColumnName("raw_output_byte_length").IsRequired();
            result.Property(r => r.RawOutputSha256).HasColumnName("raw_output_sha256").HasColumnType("bytea").IsRequired();
            result.Property(r => r.ModelRepoId).HasColumnName("model_repo_id").HasColumnType("text").IsRequired();
            result.Property(r => r.ModelRevision).HasColumnName("model_revision").HasColumnType("text").IsRequired();
            result.Property(r => r.ModelManifestSha256).HasColumnName("model_manifest_sha256").HasColumnType("bytea").IsRequired();
            result.Property(r => r.DependencyLockSha256).HasColumnName("dependency_lock_sha256").HasColumnType("bytea").IsRequired();
            result.Property(r => r.WorkerSourceDigest).HasColumnName("worker_source_digest").HasColumnType("bytea").IsRequired();
            result.Property(r => r.WorkerConfigDigest).HasColumnName("worker_config_digest").HasColumnType("bytea").IsRequired();
            result.Property(r => r.RendererIdentity).HasColumnName("renderer_identity").HasColumnType("text").IsRequired();
            result.Property(r => r.GenerationSettingsJson).HasColumnName("generation_settings_json").HasColumnType("jsonb").IsRequired();
            result.Property(r => r.FinishReason).HasColumnName("finish_reason").HasColumnType("text").IsRequired();
            result.Property(r => r.OutputPageCount).HasColumnName("output_page_count").IsRequired();
            result.Property(r => r.StartedAtUtc).HasColumnName("started_at").HasColumnType("timestamptz").IsRequired();
            result.Property(r => r.CompletedAtUtc).HasColumnName("completed_at").HasColumnType("timestamptz").IsRequired();
            result.Property(r => r.LoadDurationMs).HasColumnName("load_duration_ms").IsRequired();
            result.Property(r => r.RenderDurationMs).HasColumnName("render_duration_ms").IsRequired();
            result.Property(r => r.InferDurationMs).HasColumnName("infer_duration_ms").IsRequired();
            result.Property(r => r.TotalDurationMs).HasColumnName("total_duration_ms").IsRequired();
            result.Property(r => r.DiagnosticMetadataJson).HasColumnName("diagnostic_metadata_json").HasColumnType("jsonb").IsRequired();

            result.HasOne<Document>()
                .WithOne()
                .HasForeignKey<ExtractionResult>(r => r.DocumentId)
                .HasConstraintName("fk_extraction_results_documents")
                .OnDelete(DeleteBehavior.Restrict);

            result.HasOne<ProcessingJob>()
                .WithOne()
                .HasForeignKey<ExtractionResult>(r => r.JobId)
                .HasConstraintName("fk_extraction_results_processing_jobs")
                .OnDelete(DeleteBehavior.Restrict);

            result.HasOne<ExecutionAttempt>()
                .WithOne()
                .HasForeignKey<ExtractionResult>(r => r.AttemptId)
                .HasConstraintName("fk_extraction_results_execution_attempts")
                .OnDelete(DeleteBehavior.Restrict);

            result.HasIndex(r => r.DocumentId).IsUnique().HasDatabaseName(AcceptedResultDocumentIndex);
            result.HasIndex(r => r.JobId).IsUnique().HasDatabaseName("ux_extraction_results_job_id");
            result.HasIndex(r => r.AttemptId).IsUnique().HasDatabaseName("ux_extraction_results_attempt_id");
            result.HasIndex(r => r.FencingToken).IsUnique().HasDatabaseName("ux_extraction_results_fencing_token");
        });

        modelBuilder.Entity<WorkOrderReviewRevision>(revision =>
        {
            revision.ToTable("work_order_review_revisions", table =>
            {
                table.HasCheckConstraint("ck_work_order_review_revisions_bounds",
                    $"revision_number BETWEEN 1 AND {WorkOrderReviewSchema.MaxRevisionsPerResult} AND " +
                    "((revision_number = 1 AND previous_revision_number IS NULL) OR " +
                    "(revision_number > 1 AND previous_revision_number = revision_number - 1))");
                table.HasCheckConstraint("ck_work_order_review_revisions_status",
                    "status IN ('draft', 'reviewed')");
                table.HasCheckConstraint("ck_work_order_review_revisions_digests",
                    "octet_length(request_sha256) = 32 AND octet_length(input_sha256) = 32 AND octet_length(raw_output_sha256) = 32");
                table.HasCheckConstraint("ck_work_order_review_revisions_profile",
                    $"profile_id = '{WorkOrderReviewSchema.ProfileId}' AND " +
                    $"field_schema_version = '{WorkOrderReviewSchema.FieldSchemaVersion}' AND " +
                    $"suggestion_policy_version = '{WorkOrderReviewSchema.SuggestionPolicyVersion}'");
                table.HasCheckConstraint("ck_work_order_review_revisions_operator_label",
                    $"operator_display_label IS NULL OR (char_length(btrim(operator_display_label)) >= 1 AND char_length(operator_display_label) <= {WorkOrderReviewSchema.MaxOperatorDisplayLabelChars})");
                table.HasCheckConstraint("ck_work_order_review_revisions_field_counts",
                    "accepted_field_count >= 0 AND edited_field_count >= 0 AND unknown_field_count >= 0 AND unreviewed_field_count >= 0 AND " +
                    $"accepted_field_count + edited_field_count + unknown_field_count + unreviewed_field_count = {WorkOrderReviewSchema.FieldCount} AND " +
                    "(status = 'draft' OR unreviewed_field_count = 0)");
            });
            revision.HasKey(r => r.RevisionId).HasName("pk_work_order_review_revisions");
            revision.Property(r => r.RevisionId).HasColumnName("revision_id").ValueGeneratedNever();
            revision.Property(r => r.DocumentId).HasColumnName("document_id").IsRequired();
            revision.Property(r => r.ResultId).HasColumnName("result_id").IsRequired();
            revision.Property(r => r.RevisionNumber).HasColumnName("revision_number").IsRequired();
            revision.Property(r => r.PreviousRevisionNumber).HasColumnName("previous_revision_number");
            revision.Property(r => r.Status)
                .HasColumnName("status")
                .HasColumnType("text")
                .HasConversion(s => s.ToWire(), v => ReviewRevisionStatusNames.FromWire(v))
                .IsRequired();
            revision.Property(r => r.IdempotencyKey).HasColumnName("idempotency_key").IsRequired();
            revision.Property(r => r.RequestSha256).HasColumnName("request_sha256").HasColumnType("bytea").IsRequired();
            revision.Property(r => r.InputSha256).HasColumnName("input_sha256").HasColumnType("bytea").IsRequired();
            revision.Property(r => r.RawOutputSha256).HasColumnName("raw_output_sha256").HasColumnType("bytea").IsRequired();
            revision.Property(r => r.ProfileId).HasColumnName("profile_id").HasColumnType("text").IsRequired();
            revision.Property(r => r.FieldSchemaVersion).HasColumnName("field_schema_version").HasColumnType("text").IsRequired();
            revision.Property(r => r.SuggestionPolicyVersion).HasColumnName("suggestion_policy_version").HasColumnType("text").IsRequired();
            revision.Property(r => r.OperatorDisplayLabel).HasColumnName("operator_display_label").HasColumnType("text");
            revision.Property(r => r.AcceptedFieldCount).HasColumnName("accepted_field_count").IsRequired();
            revision.Property(r => r.EditedFieldCount).HasColumnName("edited_field_count").IsRequired();
            revision.Property(r => r.UnknownFieldCount).HasColumnName("unknown_field_count").IsRequired();
            revision.Property(r => r.UnreviewedFieldCount).HasColumnName("unreviewed_field_count").IsRequired();
            revision.Property(r => r.SavedAtUtc).HasColumnName("saved_at").HasColumnType("timestamptz").IsRequired();

            revision.HasOne<Document>()
                .WithMany()
                .HasForeignKey(r => r.DocumentId)
                .HasConstraintName("fk_work_order_review_revisions_documents")
                .OnDelete(DeleteBehavior.Restrict);

            revision.HasOne<ExtractionResult>()
                .WithMany()
                .HasForeignKey(r => r.ResultId)
                .HasConstraintName("fk_work_order_review_revisions_extraction_results")
                .OnDelete(DeleteBehavior.Restrict);

            revision.HasMany(r => r.Fields)
                .WithOne()
                .HasForeignKey(f => f.RevisionId)
                .HasConstraintName("fk_work_order_review_fields_revisions")
                .OnDelete(DeleteBehavior.Restrict);
            revision.Navigation(r => r.Fields).UsePropertyAccessMode(PropertyAccessMode.Field);

            revision.HasIndex(r => r.IdempotencyKey).IsUnique().HasDatabaseName(ReviewRevisionIdempotencyKeyIndex);
            revision.HasIndex(r => new { r.DocumentId, r.RevisionNumber }).IsUnique().HasDatabaseName(ReviewRevisionDocNumberIndex);
            revision.HasIndex(r => new { r.ResultId, r.RevisionNumber }).IsUnique().HasDatabaseName(ReviewRevisionResultNumberIndex);
        });

        modelBuilder.Entity<WorkOrderReviewField>(field =>
        {
            field.ToTable("work_order_review_fields", table =>
            {
                table.HasCheckConstraint("ck_work_order_review_fields_key_ordinal",
                    "(field_ordinal = 0 AND field_key = 'work_order_id') OR " +
                    "(field_ordinal = 1 AND field_key = 'property_name') OR " +
                    "(field_ordinal = 2 AND field_key = 'building_unit') OR " +
                    "(field_ordinal = 3 AND field_key = 'requested_date') OR " +
                    "(field_ordinal = 4 AND field_key = 'issue_and_resolution')");
                table.HasCheckConstraint("ck_work_order_review_fields_decision",
                    "decision IN ('unreviewed', 'accepted', 'edited', 'unknown')");
                table.HasCheckConstraint("ck_work_order_review_fields_value_consistency",
                    "(decision IN ('accepted', 'edited') AND human_value IS NOT NULL AND char_length(btrim(human_value)) >= 1) OR " +
                    "(decision = 'unknown' AND human_value IS NULL) OR " +
                    "(decision = 'unreviewed' AND (human_value IS NULL OR char_length(btrim(human_value)) >= 1))");
                table.HasCheckConstraint("ck_work_order_review_fields_value_lengths",
                    "human_value IS NULL OR (" +
                    "(field_key = 'work_order_id' AND char_length(human_value) <= 64) OR " +
                    "(field_key = 'property_name' AND char_length(human_value) <= 200) OR " +
                    "(field_key = 'building_unit' AND char_length(human_value) <= 120) OR " +
                    "(field_key = 'requested_date' AND char_length(human_value) <= 64) OR " +
                    "(field_key = 'issue_and_resolution' AND char_length(human_value) <= 4000))");
                table.HasCheckConstraint("ck_work_order_review_fields_unknown_reason",
                    "(decision = 'unknown' AND (unknown_reason IS NULL OR (char_length(btrim(unknown_reason)) >= 1 AND char_length(unknown_reason) <= 500))) OR " +
                    "(decision <> 'unknown' AND unknown_reason IS NULL)");
                table.HasCheckConstraint("ck_work_order_review_fields_source_coords",
                    "(consulted_page_number IS NULL AND consulted_block_ordinal IS NULL AND consulted_table_row IS NULL AND consulted_table_column IS NULL AND consulted_quote IS NULL) OR " +
                    "(consulted_page_number BETWEEN 1 AND 3 AND consulted_block_ordinal >= 0 AND consulted_quote IS NOT NULL AND " +
                    "((consulted_table_row IS NULL AND consulted_table_column IS NULL) OR (consulted_table_row >= 0 AND consulted_table_column >= 0)))");
            });
            field.HasKey(f => new { f.RevisionId, f.FieldOrdinal }).HasName("pk_work_order_review_fields");
            field.Property(f => f.RevisionId).HasColumnName("revision_id").ValueGeneratedNever();
            field.Property(f => f.FieldOrdinal).HasColumnName("field_ordinal").ValueGeneratedNever();
            field.Property(f => f.FieldKey).HasColumnName("field_key").HasColumnType("text").IsRequired();
            field.Property(f => f.Decision)
                .HasColumnName("decision")
                .HasColumnType("text")
                .HasConversion(d => d.ToWire(), v => ReviewFieldDecisionNames.FromWire(v))
                .IsRequired();
            field.Property(f => f.HumanValue).HasColumnName("human_value").HasColumnType("text");
            field.Property(f => f.UnknownReason).HasColumnName("unknown_reason").HasColumnType("text");
            field.Property(f => f.ConsultedPageNumber).HasColumnName("consulted_page_number");
            field.Property(f => f.ConsultedBlockOrdinal).HasColumnName("consulted_block_ordinal");
            field.Property(f => f.ConsultedTableRow).HasColumnName("consulted_table_row");
            field.Property(f => f.ConsultedTableColumn).HasColumnName("consulted_table_column");
            field.Property(f => f.ConsultedQuote).HasColumnName("consulted_quote").HasColumnType("text");

            field.HasIndex(f => new { f.RevisionId, f.FieldKey })
                .IsUnique()
                .HasDatabaseName("ux_work_order_review_fields_revision_key");
        });

        modelBuilder.Entity<WorkOrderReviewHead>(head =>
        {
            head.ToTable("work_order_review_heads", table =>
            {
                table.HasCheckConstraint("ck_work_order_review_heads_revision_bounds",
                    $"current_revision_number BETWEEN 1 AND {WorkOrderReviewSchema.MaxRevisionsPerResult}");
                table.HasCheckConstraint("ck_work_order_review_heads_status",
                    "current_status IN ('draft', 'reviewed')");
                table.HasCheckConstraint("ck_work_order_review_heads_digests",
                    "octet_length(input_sha256) = 32 AND octet_length(raw_output_sha256) = 32");
                table.HasCheckConstraint("ck_work_order_review_heads_profile",
                    $"profile_id = '{WorkOrderReviewSchema.ProfileId}' AND " +
                    $"field_schema_version = '{WorkOrderReviewSchema.FieldSchemaVersion}' AND " +
                    $"suggestion_policy_version = '{WorkOrderReviewSchema.SuggestionPolicyVersion}'");
            });
            head.HasKey(h => h.DocumentId).HasName("pk_work_order_review_heads");
            head.Property(h => h.DocumentId).HasColumnName("document_id").ValueGeneratedNever();
            head.Property(h => h.ResultId).HasColumnName("result_id").IsRequired();
            head.Property(h => h.InputSha256).HasColumnName("input_sha256").HasColumnType("bytea").IsRequired();
            head.Property(h => h.RawOutputSha256).HasColumnName("raw_output_sha256").HasColumnType("bytea").IsRequired();
            head.Property(h => h.ProfileId).HasColumnName("profile_id").HasColumnType("text").IsRequired();
            head.Property(h => h.FieldSchemaVersion).HasColumnName("field_schema_version").HasColumnType("text").IsRequired();
            head.Property(h => h.SuggestionPolicyVersion).HasColumnName("suggestion_policy_version").HasColumnType("text").IsRequired();
            head.Property(h => h.MachineSnapshotJson).HasColumnName("machine_snapshot_json").HasColumnType("jsonb").IsRequired();
            head.Property(h => h.CurrentRevisionNumber).HasColumnName("current_revision_number").IsRequired();
            head.Property(h => h.CurrentRevisionId).HasColumnName("current_revision_id").IsRequired();
            head.Property(h => h.CurrentStatus)
                .HasColumnName("current_status")
                .HasColumnType("text")
                .HasConversion(s => s.ToWire(), v => ReviewRevisionStatusNames.FromWire(v))
                .IsRequired();
            head.Property(h => h.CreatedAtUtc).HasColumnName("created_at").HasColumnType("timestamptz").IsRequired();
            head.Property(h => h.UpdatedAtUtc).HasColumnName("updated_at").HasColumnType("timestamptz").IsRequired();

            head.HasOne<Document>()
                .WithOne()
                .HasForeignKey<WorkOrderReviewHead>(h => h.DocumentId)
                .HasConstraintName("fk_work_order_review_heads_documents")
                .OnDelete(DeleteBehavior.Restrict);

            head.HasOne<ExtractionResult>()
                .WithOne()
                .HasForeignKey<WorkOrderReviewHead>(h => h.ResultId)
                .HasConstraintName("fk_work_order_review_heads_extraction_results")
                .OnDelete(DeleteBehavior.Restrict);

            head.HasOne<WorkOrderReviewRevision>()
                .WithMany()
                .HasForeignKey(h => h.CurrentRevisionId)
                .HasConstraintName("fk_work_order_review_heads_current_revision")
                .OnDelete(DeleteBehavior.Restrict);

            head.HasIndex(h => h.ResultId).IsUnique().HasDatabaseName(ReviewHeadResultIndex);
            head.HasIndex(h => h.CurrentRevisionId).IsUnique().HasDatabaseName("ux_work_order_review_heads_current_revision_id");
        });

        modelBuilder.Entity<ArchiveResultProjection>(projection =>
        {
            projection.ToTable("archive_result_projections", table =>
            {
                table.HasCheckConstraint("ck_archive_result_projections_version",
                    $"projection_version = '{ArchiveSchema.ProjectionVersion}'");
                table.HasCheckConstraint("ck_archive_result_projections_digests",
                    "octet_length(raw_output_sha256) = 32 AND octet_length(projection_sha256) = 32");
                table.HasCheckConstraint("ck_archive_result_projections_unit_count",
                    "unit_count >= 0");
            });
            projection.HasKey(p => new { p.ResultId, p.ProjectionVersion }).HasName("pk_archive_result_projections");
            projection.Property(p => p.ResultId).HasColumnName("result_id").ValueGeneratedNever();
            projection.Property(p => p.DocumentId).HasColumnName("document_id").IsRequired();
            projection.Property(p => p.ProjectionVersion).HasColumnName("projection_version").HasColumnType("text").ValueGeneratedNever();
            projection.Property(p => p.RawOutputSha256).HasColumnName("raw_output_sha256").HasColumnType("bytea").IsRequired();
            projection.Property(p => p.ProjectionSha256).HasColumnName("projection_sha256").HasColumnType("bytea").IsRequired();
            projection.Property(p => p.UnitCount).HasColumnName("unit_count").IsRequired();
            projection.Property(p => p.HasFallback).HasColumnName("has_fallback").IsRequired();
            projection.Property(p => p.ProjectedAtUtc).HasColumnName("projected_at").HasColumnType("timestamptz").IsRequired();

            projection.HasOne<Document>()
                .WithMany()
                .HasForeignKey(p => p.DocumentId)
                .HasConstraintName("fk_archive_result_projections_documents")
                .OnDelete(DeleteBehavior.Restrict);

            projection.HasOne<ExtractionResult>()
                .WithMany()
                .HasForeignKey(p => p.ResultId)
                .HasConstraintName("fk_archive_result_projections_extraction_results")
                .OnDelete(DeleteBehavior.Restrict);

            projection.HasMany(p => p.Units)
                .WithOne()
                .HasForeignKey(u => new { u.ResultId, u.ProjectionVersion })
                .HasConstraintName("fk_archive_projection_units_projections")
                .OnDelete(DeleteBehavior.Restrict);
            projection.Navigation(p => p.Units).UsePropertyAccessMode(PropertyAccessMode.Field);

            projection.HasIndex(p => new { p.DocumentId, p.ProjectionVersion })
                .IsUnique()
                .HasDatabaseName(ArchiveProjectionDocumentVersionIndex);
        });

        modelBuilder.Entity<ArchiveProjectionUnit>(unit =>
        {
            unit.ToTable("archive_projection_units", table =>
            {
                table.HasCheckConstraint("ck_archive_projection_units_version",
                    $"projection_version = '{ArchiveSchema.ProjectionVersion}'");
                table.HasCheckConstraint("ck_archive_projection_units_ordinal",
                    "unit_ordinal >= 0");
                table.HasCheckConstraint("ck_archive_projection_units_kind",
                    $"unit_kind IN ('{ArchiveSchema.UnitKindPage}', '{ArchiveSchema.UnitKindPageFallback}', '{ArchiveSchema.UnitKindDocumentFallback}')");
                table.HasCheckConstraint("ck_archive_projection_units_coords",
                    $"((unit_kind = '{ArchiveSchema.UnitKindDocumentFallback}' AND page_number IS NULL AND is_fallback = TRUE) OR " +
                    $"(unit_kind = '{ArchiveSchema.UnitKindPageFallback}' AND page_number BETWEEN 1 AND {ExtractionCeilings.MaxExtractionPages} AND is_fallback = TRUE) OR " +
                    $"(unit_kind = '{ArchiveSchema.UnitKindPage}' AND page_number BETWEEN 1 AND {ExtractionCeilings.MaxExtractionPages}))");
                table.HasCheckConstraint("ck_archive_projection_units_text",
                    "char_length(btrim(search_text)) >= 1");
            });
            unit.HasKey(u => new { u.ResultId, u.ProjectionVersion, u.UnitOrdinal }).HasName("pk_archive_projection_units");
            unit.Property(u => u.ResultId).HasColumnName("result_id").ValueGeneratedNever();
            unit.Property(u => u.ProjectionVersion).HasColumnName("projection_version").HasColumnType("text").ValueGeneratedNever();
            unit.Property(u => u.UnitOrdinal).HasColumnName("unit_ordinal").ValueGeneratedNever();
            unit.Property(u => u.DocumentId).HasColumnName("document_id").IsRequired();
            unit.Property(u => u.PageNumber).HasColumnName("page_number");
            unit.Property(u => u.UnitKind).HasColumnName("unit_kind").HasColumnType("text").IsRequired();
            unit.Property(u => u.IsFallback).HasColumnName("is_fallback").IsRequired();
            unit.Property(u => u.SearchText).HasColumnName("search_text").HasColumnType("text").IsRequired();

            unit.HasOne<Document>()
                .WithMany()
                .HasForeignKey(u => u.DocumentId)
                .HasConstraintName("fk_archive_projection_units_documents")
                .OnDelete(DeleteBehavior.Restrict);

            unit.HasIndex(u => new { u.DocumentId, u.ProjectionVersion, u.UnitOrdinal })
                .HasDatabaseName(ArchiveProjectionUnitsDocumentIndex);
        });
    }
}
