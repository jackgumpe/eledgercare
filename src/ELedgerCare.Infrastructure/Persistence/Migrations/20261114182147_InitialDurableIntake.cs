using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ELedgerCare.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class InitialDurableIntake : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "eledgercare");

            migrationBuilder.CreateTable(
                name: "documents",
                schema: "eledgercare",
                columns: table => new
                {
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    idempotency_key = table.Column<Guid>(type: "uuid", nullable: false),
                    submitted_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_documents", x => x.document_id);
                });

            migrationBuilder.CreateTable(
                name: "original_artifacts",
                schema: "eledgercare",
                columns: table => new
                {
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    bytes = table.Column<byte[]>(type: "bytea", nullable: false),
                    sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    byte_length = table.Column<int>(type: "integer", nullable: false),
                    media_type = table.Column<string>(type: "text", nullable: false),
                    page_count = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_original_artifacts", x => x.document_id);
                    table.CheckConstraint("ck_original_artifacts_byte_length_matches", "byte_length = octet_length(bytes)");
                    table.CheckConstraint("ck_original_artifacts_byte_length_range", "byte_length BETWEEN 1 AND 10485760");
                    table.CheckConstraint("ck_original_artifacts_media_type", "media_type = 'application/pdf'");
                    table.CheckConstraint("ck_original_artifacts_page_count_range", "page_count BETWEEN 1 AND 50");
                    table.CheckConstraint("ck_original_artifacts_sha256_length", "octet_length(sha256) = 32");
                    table.ForeignKey(
                        name: "fk_original_artifacts_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "processing_jobs",
                schema: "eledgercare",
                columns: table => new
                {
                    job_id = table.Column<Guid>(type: "uuid", nullable: false),
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    status = table.Column<string>(type: "text", nullable: false),
                    requested_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_processing_jobs", x => x.job_id);
                    table.CheckConstraint("ck_processing_jobs_status", "status = 'awaiting_extraction'");
                    table.ForeignKey(
                        name: "fk_processing_jobs_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ux_documents_idempotency_key",
                schema: "eledgercare",
                table: "documents",
                column: "idempotency_key",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_processing_jobs_document_id",
                schema: "eledgercare",
                table: "processing_jobs",
                column: "document_id",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "original_artifacts",
                schema: "eledgercare");

            migrationBuilder.DropTable(
                name: "processing_jobs",
                schema: "eledgercare");

            migrationBuilder.DropTable(
                name: "documents",
                schema: "eledgercare");
        }
    }
}
