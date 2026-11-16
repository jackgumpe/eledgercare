using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ELedgerCare.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddWorkOrderReview : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "work_order_review_revisions",
                schema: "eledgercare",
                columns: table => new
                {
                    revision_id = table.Column<Guid>(type: "uuid", nullable: false),
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    result_id = table.Column<Guid>(type: "uuid", nullable: false),
                    revision_number = table.Column<int>(type: "integer", nullable: false),
                    previous_revision_number = table.Column<int>(type: "integer", nullable: true),
                    status = table.Column<string>(type: "text", nullable: false),
                    idempotency_key = table.Column<Guid>(type: "uuid", nullable: false),
                    request_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    input_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    raw_output_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    profile_id = table.Column<string>(type: "text", nullable: false),
                    field_schema_version = table.Column<string>(type: "text", nullable: false),
                    suggestion_policy_version = table.Column<string>(type: "text", nullable: false),
                    operator_display_label = table.Column<string>(type: "text", nullable: true),
                    accepted_field_count = table.Column<int>(type: "integer", nullable: false),
                    edited_field_count = table.Column<int>(type: "integer", nullable: false),
                    unknown_field_count = table.Column<int>(type: "integer", nullable: false),
                    unreviewed_field_count = table.Column<int>(type: "integer", nullable: false),
                    saved_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_work_order_review_revisions", x => x.revision_id);
                    table.CheckConstraint("ck_work_order_review_revisions_bounds", "revision_number BETWEEN 1 AND 128 AND ((revision_number = 1 AND previous_revision_number IS NULL) OR (revision_number > 1 AND previous_revision_number = revision_number - 1))");
                    table.CheckConstraint("ck_work_order_review_revisions_digests", "octet_length(request_sha256) = 32 AND octet_length(input_sha256) = 32 AND octet_length(raw_output_sha256) = 32");
                    table.CheckConstraint("ck_work_order_review_revisions_field_counts", "accepted_field_count >= 0 AND edited_field_count >= 0 AND unknown_field_count >= 0 AND unreviewed_field_count >= 0 AND accepted_field_count + edited_field_count + unknown_field_count + unreviewed_field_count = 5 AND (status = 'draft' OR unreviewed_field_count = 0)");
                    table.CheckConstraint("ck_work_order_review_revisions_operator_label", "operator_display_label IS NULL OR (char_length(btrim(operator_display_label)) >= 1 AND char_length(operator_display_label) <= 80)");
                    table.CheckConstraint("ck_work_order_review_revisions_profile", "profile_id = 'maintenance-work-order/1' AND field_schema_version = 'maintenance-work-order-fields/1' AND suggestion_policy_version = 'work-order-suggestions/1'");
                    table.CheckConstraint("ck_work_order_review_revisions_status", "status IN ('draft', 'reviewed')");
                    table.ForeignKey(
                        name: "fk_work_order_review_revisions_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_work_order_review_revisions_extraction_results",
                        column: x => x.result_id,
                        principalSchema: "eledgercare",
                        principalTable: "extraction_results",
                        principalColumn: "result_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "work_order_review_fields",
                schema: "eledgercare",
                columns: table => new
                {
                    revision_id = table.Column<Guid>(type: "uuid", nullable: false),
                    field_ordinal = table.Column<int>(type: "integer", nullable: false),
                    field_key = table.Column<string>(type: "text", nullable: false),
                    decision = table.Column<string>(type: "text", nullable: false),
                    human_value = table.Column<string>(type: "text", nullable: true),
                    unknown_reason = table.Column<string>(type: "text", nullable: true),
                    consulted_page_number = table.Column<int>(type: "integer", nullable: true),
                    consulted_block_ordinal = table.Column<int>(type: "integer", nullable: true),
                    consulted_table_row = table.Column<int>(type: "integer", nullable: true),
                    consulted_table_column = table.Column<int>(type: "integer", nullable: true),
                    consulted_quote = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_work_order_review_fields", x => new { x.revision_id, x.field_ordinal });
                    table.CheckConstraint("ck_work_order_review_fields_decision", "decision IN ('unreviewed', 'accepted', 'edited', 'unknown')");
                    table.CheckConstraint("ck_work_order_review_fields_key_ordinal", "(field_ordinal = 0 AND field_key = 'work_order_id') OR (field_ordinal = 1 AND field_key = 'property_name') OR (field_ordinal = 2 AND field_key = 'building_unit') OR (field_ordinal = 3 AND field_key = 'requested_date') OR (field_ordinal = 4 AND field_key = 'issue_and_resolution')");
                    table.CheckConstraint("ck_work_order_review_fields_source_coords", "(consulted_page_number IS NULL AND consulted_block_ordinal IS NULL AND consulted_table_row IS NULL AND consulted_table_column IS NULL AND consulted_quote IS NULL) OR (consulted_page_number BETWEEN 1 AND 3 AND consulted_block_ordinal >= 0 AND consulted_quote IS NOT NULL AND ((consulted_table_row IS NULL AND consulted_table_column IS NULL) OR (consulted_table_row >= 0 AND consulted_table_column >= 0)))");
                    table.CheckConstraint("ck_work_order_review_fields_unknown_reason", "(decision = 'unknown' AND (unknown_reason IS NULL OR (char_length(btrim(unknown_reason)) >= 1 AND char_length(unknown_reason) <= 500))) OR (decision <> 'unknown' AND unknown_reason IS NULL)");
                    table.CheckConstraint("ck_work_order_review_fields_value_consistency", "(decision IN ('accepted', 'edited') AND human_value IS NOT NULL AND char_length(btrim(human_value)) >= 1) OR (decision = 'unknown' AND human_value IS NULL) OR (decision = 'unreviewed' AND (human_value IS NULL OR char_length(btrim(human_value)) >= 1))");
                    table.CheckConstraint("ck_work_order_review_fields_value_lengths", "human_value IS NULL OR ((field_key = 'work_order_id' AND char_length(human_value) <= 64) OR (field_key = 'property_name' AND char_length(human_value) <= 200) OR (field_key = 'building_unit' AND char_length(human_value) <= 120) OR (field_key = 'requested_date' AND char_length(human_value) <= 64) OR (field_key = 'issue_and_resolution' AND char_length(human_value) <= 4000))");
                    table.ForeignKey(
                        name: "fk_work_order_review_fields_revisions",
                        column: x => x.revision_id,
                        principalSchema: "eledgercare",
                        principalTable: "work_order_review_revisions",
                        principalColumn: "revision_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "work_order_review_heads",
                schema: "eledgercare",
                columns: table => new
                {
                    document_id = table.Column<Guid>(type: "uuid", nullable: false),
                    result_id = table.Column<Guid>(type: "uuid", nullable: false),
                    input_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    raw_output_sha256 = table.Column<byte[]>(type: "bytea", nullable: false),
                    profile_id = table.Column<string>(type: "text", nullable: false),
                    field_schema_version = table.Column<string>(type: "text", nullable: false),
                    suggestion_policy_version = table.Column<string>(type: "text", nullable: false),
                    machine_snapshot_json = table.Column<string>(type: "jsonb", nullable: false),
                    current_revision_number = table.Column<int>(type: "integer", nullable: false),
                    current_revision_id = table.Column<Guid>(type: "uuid", nullable: false),
                    current_status = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_work_order_review_heads", x => x.document_id);
                    table.CheckConstraint("ck_work_order_review_heads_digests", "octet_length(input_sha256) = 32 AND octet_length(raw_output_sha256) = 32");
                    table.CheckConstraint("ck_work_order_review_heads_profile", "profile_id = 'maintenance-work-order/1' AND field_schema_version = 'maintenance-work-order-fields/1' AND suggestion_policy_version = 'work-order-suggestions/1'");
                    table.CheckConstraint("ck_work_order_review_heads_revision_bounds", "current_revision_number BETWEEN 1 AND 128");
                    table.CheckConstraint("ck_work_order_review_heads_status", "current_status IN ('draft', 'reviewed')");
                    table.ForeignKey(
                        name: "fk_work_order_review_heads_current_revision",
                        column: x => x.current_revision_id,
                        principalSchema: "eledgercare",
                        principalTable: "work_order_review_revisions",
                        principalColumn: "revision_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_work_order_review_heads_documents",
                        column: x => x.document_id,
                        principalSchema: "eledgercare",
                        principalTable: "documents",
                        principalColumn: "document_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_work_order_review_heads_extraction_results",
                        column: x => x.result_id,
                        principalSchema: "eledgercare",
                        principalTable: "extraction_results",
                        principalColumn: "result_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ux_work_order_review_fields_revision_key",
                schema: "eledgercare",
                table: "work_order_review_fields",
                columns: new[] { "revision_id", "field_key" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_work_order_review_heads_current_revision_id",
                schema: "eledgercare",
                table: "work_order_review_heads",
                column: "current_revision_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_work_order_review_heads_result_id",
                schema: "eledgercare",
                table: "work_order_review_heads",
                column: "result_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_work_order_review_revisions_document_revision",
                schema: "eledgercare",
                table: "work_order_review_revisions",
                columns: new[] { "document_id", "revision_number" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_work_order_review_revisions_idempotency_key",
                schema: "eledgercare",
                table: "work_order_review_revisions",
                column: "idempotency_key",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_work_order_review_revisions_result_revision",
                schema: "eledgercare",
                table: "work_order_review_revisions",
                columns: new[] { "result_id", "revision_number" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "work_order_review_fields",
                schema: "eledgercare");

            migrationBuilder.DropTable(
                name: "work_order_review_heads",
                schema: "eledgercare");

            migrationBuilder.DropTable(
                name: "work_order_review_revisions",
                schema: "eledgercare");
        }
    }
}
