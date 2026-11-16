using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Intake;
using ELedgerCare.Domain.Processing;
using Microsoft.EntityFrameworkCore;

namespace ELedgerCare.Infrastructure.Persistence;

public sealed class ELedgerCareDbContext(DbContextOptions<ELedgerCareDbContext> options) : DbContext(options)
{
    public const string Schema = "eledgercare";
    public const string IdempotencyKeyUniqueIndex = "ux_documents_idempotency_key";
    public const string OneRunningAttemptIndex = "ux_execution_attempts_one_running_per_job";
    public const string AcceptedResultDocumentIndex = "ux_extraction_results_document_id";

    public DbSet<Document> Documents => Set<Document>();

    public DbSet<OriginalArtifact> OriginalArtifacts => Set<OriginalArtifact>();

    public DbSet<ProcessingJob> ProcessingJobs => Set<ProcessingJob>();

    public DbSet<ExecutionAttempt> ExecutionAttempts => Set<ExecutionAttempt>();

    public DbSet<ExtractionResult> ExtractionResults => Set<ExtractionResult>();

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
    }
}
