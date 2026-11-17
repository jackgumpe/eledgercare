using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ELedgerCare.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddSourceLinkedArchive : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "archive_result_projections",
                schema: "eledgercare",
                columns: table => new
                {
                    result_id = table.Column<Guid>(type: "uuid", nullable: false),
                    projection_version = table.Column<string>(type: "text", nullable: false),
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    raw_output_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    projection_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    unit_count = table.Column<int>(type: "integer", nullable: false),
                    has_fallback = table.Column<bool>(type: "boolean", nullable: false),
                    projected_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_archive_result_projections", x => new { x.result_id, x.projection_version });
                    table.CheckConstraint("ck_archive_result_projections_digests", "octet_length(raw_output_sha256) = 32 AND octet_length(projection_sha256) = 32");
                    table.CheckConstraint("ck_archive_result_projections_unit_count", "unit_count >= 0");
                    table.CheckConstraint("ck_archive_result_projections_version", "projection_version = 'archive-machine-projection/1'");
                    table.ForeignKey(
                        name: "fk_archive_result_projections_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_archive_result_projections_extraction_results",
                        column: x => x.result_id,
                        principalSchema: "eledgercare",
                        principalTable: "extraction_results",
                        principalColumn: "result_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "archive_projection_units",
                schema: "eledgercare",
                columns: table => new
                {
                    result_id = table.Column<Guid>(type: "uuid", nullable: false),
                    projection_version = table.Column<string>(type: "text", nullable: false),
                    unit_ordinal = table.Column<int>(type: "integer", nullable: false),
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    page_number = table.Column<int>(type: "integer", nullable: true),
                    unit_kind = table.Column<string>(type: "text", nullable: false),
                    is_fallback = table.Column<bool>(type: "boolean", nullable: false),
                    search_text = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_archive_projection_units", x => new { x.result_id, x.projection_version, x.unit_ordinal });
                    table.CheckConstraint("ck_archive_projection_units_coords", "((unit_kind = 'document_fallback' AND page_number IS NULL AND is_fallback = TRUE) OR (unit_kind = 'page_fallback' AND page_number BETWEEN 1 AND 3 AND is_fallback = TRUE) OR (unit_kind = 'page' AND page_number BETWEEN 1 AND 3))");
                    table.CheckConstraint("ck_archive_projection_units_kind", "unit_kind IN ('page', 'page_fallback', 'document_fallback')");
                    table.CheckConstraint("ck_archive_projection_units_ordinal", "unit_ordinal >= 0");
                    table.CheckConstraint("ck_archive_projection_units_text", "char_length(btrim(search_text)) >= 1");
                    table.CheckConstraint("ck_archive_projection_units_version", "projection_version = 'archive-machine-projection/1'");
                    table.ForeignKey(
                        name: "fk_archive_projection_units_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_archive_projection_units_projections",
                        columns: x => new { x.result_id, x.projection_version },
                        principalSchema: "eledgercare",
                        principalTable: "archive_result_projections",
                        principalColumns: new[] { "result_id", "projection_version" },
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_documents_submitted_at_document_id_desc",
                schema: "eledgercare",
                table: "documents",
                columns: new[] { "submitted_at", "document_id" },
                descending: new bool[0]);

            migrationBuilder.CreateIndex(
                name: "ix_archive_projection_units_document_version_ordinal",
                schema: "eledgercare",
                table: "archive_projection_units",
                columns: new[] { "document_id", "projection_version", "unit_ordinal" });

            migrationBuilder.CreateIndex(
                name: "ux_archive_result_projections_document_version",
                schema: "eledgercare",
                table: "archive_result_projections",
                columns: new[] { "document_id", "projection_version" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "archive_projection_units",
                schema: "eledgercare");

            migrationBuilder.DropTable(
                name: "archive_result_projections",
                schema: "eledgercare");

            migrationBuilder.DropIndex(
                name: "ix_documents_submitted_at_document_id_desc",
                schema: "eledgercare",
                table: "documents");
        }
    }
}
