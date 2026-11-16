using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ELedgerCare.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddLocalExtraction : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_processing_jobs_status",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.CreateSequence(
                name: "extraction_fencing_seq",
                schema: "eledgercare");

            migrationBuilder.AddColumn<int>(
                name: "attempt_count",
                schema: "eledgercare",
                table: "processing_jobs",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.AddColumn<long>(
                name: "latest_fencing_token",
                schema: "eledgercare",
                table: "processing_jobs",
                type: "bigint",
                nullable: false,
                defaultValue: 0L);

            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "queued_at",
                schema: "eledgercare",
                table: "processing_jobs",
                type: "timestamptz",
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "retried_from_attempt_id",
                schema: "eledgercare",
                table: "processing_jobs",
                type: "uuid",
                nullable: true);

            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "updated_at",
                schema: "eledgercare",
                table: "processing_jobs",
                type: "timestamptz",
                nullable: true);

            migrationBuilder.Sql(
                "UPDATE eledgercare.processing_jobs SET updated_at = requested_at WHERE updated_at IS NULL;");

            migrationBuilder.AlterColumn<DateTimeOffset>(
                name: "updated_at",
                schema: "eledgercare",
                table: "processing_jobs",
                type: "timestamptz",
                nullable: false,
                oldClrType: typeof(DateTimeOffset),
                oldType: "timestamptz",
                oldNullable: true);

            migrationBuilder.CreateTable(
                name: "execution_attempts",
                schema: "eledgercare",
                columns: table => new
                {
                    attempt_id = table.Column<Guid>(type: "uuid", nullable: false),
                    job_id = table.Column<Guid>(type: "uuid", nullable: false),
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    attempt_number = table.Column<int>(type: "integer", nullable: false),
                    fencing_token = table.Column<long>(type: "bigint", nullable: false),
                    retried_from_attempt_id = table.Column<Guid>(type: "uuid", nullable: true),
                    status = table.Column<string>(type: "text", nullable: false),
                    phase = table.Column<string>(type: "text", nullable: false),
                    run_directory_name = table.Column<string>(type: "text", nullable: false),
                    supervisor_instance_id = table.Column<Guid>(type: "uuid", nullable: false),
                    supervisor_pid = table.Column<int>(type: "integer", nullable: false),
                    supervisor_create_filetime = table.Column<long>(type: "bigint", nullable: false),
                    launcher_pid = table.Column<int>(type: "integer", nullable: true),
                    launcher_create_filetime = table.Column<long>(type: "bigint", nullable: true),
                    worker_pid = table.Column<int>(type: "integer", nullable: true),
                    worker_create_filetime = table.Column<long>(type: "bigint", nullable: true),
                    started_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                    last_heartbeat_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                    ended_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                    exit_code = table.Column<int>(type: "integer", nullable: true),
                    failure_code = table.Column<string>(type: "text", nullable: true),
                    failure_detail = table.Column<string>(type: "text", nullable: true),
                    diagnostic_raw_output_utf8 = table.Column<string>(type: "text", nullable: true),
                    diagnostic_metadata_json = table.Column<string>(type: "jsonb", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_execution_attempts", x => x.attempt_id);
                    table.CheckConstraint("ck_execution_attempts_ended_consistency", "(status = 'running' AND ended_at IS NULL) OR (status <> 'running' AND ended_at IS NOT NULL)");
                    table.CheckConstraint("ck_execution_attempts_failure_consistency", "(status IN ('failed', 'interrupted') AND failure_code IS NOT NULL) OR (status IN ('running', 'completed') AND failure_code IS NULL)");
                    table.CheckConstraint("ck_execution_attempts_positive_ids", "attempt_number >= 1 AND fencing_token >= 1 AND supervisor_pid > 0 AND supervisor_create_filetime > 0");
                    table.CheckConstraint("ck_execution_attempts_status", "status IN ('running', 'completed', 'failed', 'interrupted')");
                    table.ForeignKey(
                        name: "fk_execution_attempts_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_execution_attempts_processing_jobs",
                        column: x => x.job_id,
                        principalSchema: "eledgercare",
                        principalTable: "processing_jobs",
                        principalColumn: "job_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_execution_attempts_retried_from",
                        column: x => x.retried_from_attempt_id,
                        principalSchema: "eledgercare",
                        principalTable: "execution_attempts",
                        principalColumn: "attempt_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "extraction_results",
                schema: "eledgercare",
                columns: table => new
                {
                    result_id = table.Column<Guid>(type: "uuid", nullable: false),
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    job_id = table.Column<Guid>(type: "uuid", nullable: false),
                    attempt_id = table.Column<Guid>(type: "uuid", nullable: false),
                    fencing_token = table.Column<long>(type: "bigint", nullable: false),
                    schema_version = table.Column<string>(type: "text", nullable: false),
                    input_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    input_byte_length = table.Column<int>(type: "integer", nullable: false),
                    page_count = table.Column<int>(type: "integer", nullable: false),
                    raw_output_bytes = table.Column<byte[]>(type: "bytea", nullable: false),
                    raw_output_byte_length = table.Column<int>(type: "integer", nullable: false),
                    raw_output_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    model_repo_id = table.Column<string>(type: "text", nullable: false),
                    model_revision = table.Column<string>(type: "text", nullable: false),
                    model_manifest_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    dependency_lock_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    worker_source_digest = table.Column<byte[]>(type: "bytea", nullable: false),
                    worker_config_digest = table.Column<byte[]>(type: "bytea", nullable: false),
                    renderer_identity = table.Column<string>(type: "text", nullable: false),
                    generation_settings_json = table.Column<string>(type: "jsonb", nullable: false),
                    finish_reason = table.Column<string>(type: "text", nullable: false),
                    output_page_count = table.Column<int>(type: "integer", nullable: false),
                    started_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                    completed_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                    load_duration_ms = table.Column<long>(type: "bigint", nullable: false),
                    render_duration_ms = table.Column<long>(type: "bigint", nullable: false),
                    infer_duration_ms = table.Column<long>(type: "bigint", nullable: false),
                    total_duration_ms = table.Column<long>(type: "bigint", nullable: false),
                    diagnostic_metadata_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_extraction_results", x => x.result_id);
                    table.CheckConstraint("ck_extraction_results_digests", "octet_length(input_sha256) = 32 AND octet_length(raw_output_sha256) = 32 AND octet_length(model_manifest_sha256) = 32 AND octet_length(dependency_lock_sha256) = 32 AND octet_length(worker_source_digest) = 32 AND octet_length(worker_config_digest) = 32");
                    table.CheckConstraint("ck_extraction_results_durations", "load_duration_ms >= 0 AND render_duration_ms >= 0 AND infer_duration_ms >= 0 AND total_duration_ms >= 0");
                    table.CheckConstraint("ck_extraction_results_finish_reason", "finish_reason = 'stop'");
                    table.CheckConstraint("ck_extraction_results_page_bounds", "page_count BETWEEN 1 AND 3 AND output_page_count = page_count");
                    table.CheckConstraint("ck_extraction_results_raw_length_matches", "raw_output_byte_length BETWEEN 1 AND 16777216 AND raw_output_byte_length = octet_length(raw_output_bytes)");
                    table.CheckConstraint("ck_extraction_results_schema", "schema_version = 'eledgercare.local-extraction/1'");
                    table.ForeignKey(
                        name: "fk_extraction_results_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_extraction_results_execution_attempts",
                        column: x => x.attempt_id,
                        principalSchema: "eledgercare",
                        principalTable: "execution_attempts",
                        principalColumn: "attempt_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_extraction_results_processing_jobs",
                        column: x => x.job_id,
                        principalSchema: "eledgercare",
                        principalTable: "processing_jobs",
                        principalColumn: "job_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_processing_jobs_retried_from_attempt_id",
                schema: "eledgercare",
                table: "processing_jobs",
                column: "retried_from_attempt_id");

            migrationBuilder.AddCheckConstraint(
                name: "ck_processing_jobs_state_invariants",
                schema: "eledgercare",
                table: "processing_jobs",
                sql: "(status = 'awaiting_extraction' AND queued_at IS NULL AND attempt_count = 0 AND latest_fencing_token = 0 AND retried_from_attempt_id IS NULL) OR (status = 'queued' AND queued_at IS NOT NULL AND attempt_count >= 0 AND latest_fencing_token >= 0) OR (status IN ('running', 'completed', 'failed', 'interrupted') AND attempt_count >= 1 AND latest_fencing_token >= 1)");

            migrationBuilder.AddCheckConstraint(
                name: "ck_processing_jobs_status",
                schema: "eledgercare",
                table: "processing_jobs",
                sql: "status IN ('awaiting_extraction', 'queued', 'running', 'completed', 'failed', 'interrupted')");

            migrationBuilder.CreateIndex(
                name: "ix_execution_attempts_retried_from_attempt_id",
                schema: "eledgercare",
                table: "execution_attempts",
                column: "retried_from_attempt_id");

            migrationBuilder.CreateIndex(
                name: "ix_execution_attempts_document_id",
                schema: "eledgercare",
                table: "execution_attempts",
                column: "document_id");

            migrationBuilder.CreateIndex(
                name: "ux_execution_attempts_fencing_token",
                schema: "eledgercare",
                table: "execution_attempts",
                column: "fencing_token",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_execution_attempts_job_attempt_number",
                schema: "eledgercare",
                table: "execution_attempts",
                columns: new[] { "job_id", "attempt_number" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_execution_attempts_one_running_per_job",
                schema: "eledgercare",
                table: "execution_attempts",
                column: "job_id",
                unique: true,
                filter: "status = 'running'");

            migrationBuilder.CreateIndex(
                name: "ux_extraction_results_attempt_id",
                schema: "eledgercare",
                table: "extraction_results",
                column: "attempt_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_extraction_results_document_id",
                schema: "eledgercare",
                table: "extraction_results",
                column: "document_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_extraction_results_fencing_token",
                schema: "eledgercare",
                table: "extraction_results",
                column: "fencing_token",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_extraction_results_job_id",
                schema: "eledgercare",
                table: "extraction_results",
                column: "job_id",
                unique: true);

            migrationBuilder.AddForeignKey(
                name: "fk_processing_jobs_retried_from_attempt",
                schema: "eledgercare",
                table: "processing_jobs",
                column: "retried_from_attempt_id",
                principalSchema: "eledgercare",
                principalTable: "execution_attempts",
                principalColumn: "attempt_id",
                onDelete: ReferentialAction.Restrict);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "fk_processing_jobs_retried_from_attempt",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropTable(
                name: "extraction_results",
                schema: "eledgercare");

            migrationBuilder.DropTable(
                name: "execution_attempts",
                schema: "eledgercare");

            migrationBuilder.DropIndex(
                name: "ix_processing_jobs_retried_from_attempt_id",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropCheckConstraint(
                name: "ck_processing_jobs_state_invariants",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropCheckConstraint(
                name: "ck_processing_jobs_status",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropColumn(
                name: "attempt_count",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropColumn(
                name: "latest_fencing_token",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropColumn(
                name: "queued_at",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropColumn(
                name: "retried_from_attempt_id",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropColumn(
                name: "updated_at",
                schema: "eledgercare",
                table: "processing_jobs");

            migrationBuilder.DropSequence(
                name: "extraction_fencing_seq",
                schema: "eledgercare");

            migrationBuilder.AddCheckConstraint(
                name: "ck_processing_jobs_status",
                schema: "eledgercare",
                table: "processing_jobs",
                sql: "status = 'awaiting_extraction'");
        }
    }
}
