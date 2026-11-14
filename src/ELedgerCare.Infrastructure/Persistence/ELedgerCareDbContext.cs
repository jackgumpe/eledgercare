using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Intake;
using ELedgerCare.Domain.Processing;
using Microsoft.EntityFrameworkCore;

namespace ELedgerCare.Infrastructure.Persistence;

public sealed class ELedgerCareDbContext(DbContextOptions<ELedgerCareDbContext> options) : DbContext(options)
{
    public const string Schema = "eledgercare";
    public const string IdempotencyKeyUniqueIndex = "ux_documents_idempotency_key";

    public DbSet<Document> Documents => Set<Document>();

    public DbSet<OriginalArtifact> OriginalArtifacts => Set<OriginalArtifact>();

    public DbSet<ProcessingJob> ProcessingJobs => Set<ProcessingJob>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema(Schema);

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
                table.HasCheckConstraint("ck_processing_jobs_status",
                    $"status = '{ProcessingStatusNames.AwaitingExtraction}'"));
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
        });
    }
}
