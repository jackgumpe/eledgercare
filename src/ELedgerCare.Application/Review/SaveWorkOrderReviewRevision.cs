using ELedgerCare.Application.Extraction;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;

namespace ELedgerCare.Application.Review;

public sealed class SaveWorkOrderReviewRevision(
    IWorkOrderReviewStore reviewStore,
    TimeProvider timeProvider)
{
    public Task<SaveReviewRevisionOutcome> ExecuteAsync(
        SaveReviewRevisionCommand command,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(command);
        var nowUtc = ExtractionAttemptCoordinator.TruncateToMicroseconds(timeProvider.GetUtcNow());
        return reviewStore.SaveRevisionAsync(command, nowUtc, cancellationToken);
    }

    /// <summary>
    /// Validates profile, text safety, length caps, whitespace rules, and decision invariants that do not
    /// depend on database state (invoked after checking <c>Idempotency-Key</c> replay so any parameter mismatch
    /// on an existing key always returns <c>409 idempotency_key_conflict</c>).
    /// </summary>
    public static SaveReviewRevisionOutcome? ValidateContextFreeInvariants(SaveReviewRevisionCommand command)
    {
        if (!string.Equals(command.ProfileId, WorkOrderReviewSchema.ProfileId, StringComparison.Ordinal))
        {
            return new SaveReviewRevisionOutcome.ProfileUnsupported(
                $"Only profile '{WorkOrderReviewSchema.ProfileId}' is supported in this release.");
        }

        if (command.OperatorDisplayLabel is not null)
        {
            if (!ReviewTextValidator.ValidateNonEmptyText(
                    command.OperatorDisplayLabel,
                    WorkOrderReviewSchema.MaxOperatorDisplayLabelChars,
                    allowMultilineWhitespace: false,
                    out var labelRejection))
            {
                return new SaveReviewRevisionOutcome.ValidationRejected(
                    "invalid_operator_display_label",
                    ReviewTextValidator.DescribeRejection(
                        "operatorDisplayLabel",
                        WorkOrderReviewSchema.MaxOperatorDisplayLabelChars,
                        labelRejection!.Value));
            }
        }

        for (var i = 0; i < WorkOrderReviewSchema.FieldCount; i++)
        {
            var spec = WorkOrderReviewSchema.Fields[i];
            var field = command.OrderedFields[i];

            if (command.Status == ReviewRevisionStatus.Reviewed && field.Decision == ReviewFieldDecision.Unreviewed)
            {
                return new SaveReviewRevisionOutcome.ValidationRejected(
                    "unreviewed_fields_cannot_complete_review",
                    $"Field '{spec.FieldKey}' is still 'unreviewed'. All five fields must be accepted, edited, or unknown before saving as 'reviewed'.");
            }

            if (field.Decision != ReviewFieldDecision.Unknown && field.UnknownReason is not null)
            {
                return new SaveReviewRevisionOutcome.ValidationRejected(
                    "unexpected_unknown_reason",
                    $"Field '{spec.FieldKey}' can only include unknownReason when decision is 'unknown'.");
            }

            if (field.UnknownReason is not null &&
                !ReviewTextValidator.ValidateNonEmptyText(
                    field.UnknownReason,
                    WorkOrderReviewSchema.MaxUnknownReasonChars,
                    allowMultilineWhitespace: false,
                    out var reasonRejection))
            {
                return new SaveReviewRevisionOutcome.ValidationRejected(
                    "invalid_unknown_reason",
                    ReviewTextValidator.DescribeRejection(
                        $"{spec.FieldKey}.unknownReason",
                        WorkOrderReviewSchema.MaxUnknownReasonChars,
                        reasonRejection!.Value));
            }

            switch (field.Decision)
            {
                case ReviewFieldDecision.Unknown:
                    if (field.Value is not null)
                    {
                        return new SaveReviewRevisionOutcome.ValidationRejected(
                            "unknown_field_cannot_have_value",
                            $"Field '{spec.FieldKey}' has decision 'unknown' and must have a null value.");
                    }

                    break;

                case ReviewFieldDecision.Accepted or ReviewFieldDecision.Edited:
                    if (field.Value is null)
                    {
                        return new SaveReviewRevisionOutcome.ValidationRejected(
                            "missing_field_value",
                            $"Field '{spec.FieldKey}' has decision '{field.Decision.ToWire()}' and requires a non-empty value.");
                    }

                    if (!ReviewTextValidator.ValidateNonEmptyText(
                            field.Value,
                            spec.MaxChars,
                            allowMultilineWhitespace: spec.Multiline,
                            out var valRejection))
                    {
                        return new SaveReviewRevisionOutcome.ValidationRejected(
                            "invalid_field_value",
                            ReviewTextValidator.DescribeRejection(spec.FieldKey, spec.MaxChars, valRejection!.Value));
                    }

                    break;

                case ReviewFieldDecision.Unreviewed:
                    if (field.Value is not null &&
                        !ReviewTextValidator.ValidateNonEmptyText(
                            field.Value,
                            spec.MaxChars,
                            allowMultilineWhitespace: spec.Multiline,
                            out var draftRejection))
                    {
                        return new SaveReviewRevisionOutcome.ValidationRejected(
                            "invalid_field_value",
                            ReviewTextValidator.DescribeRejection(spec.FieldKey, spec.MaxChars, draftRejection!.Value));
                    }

                    break;
            }
        }

        return null;
    }

    /// <summary>
    /// Validates <c>accepted</c> exact equality against the immutable <see cref="WorkOrderMachineSnapshot"/>
    /// and resolves/verifies <c>consultedSource</c> coordinates against parsed <see cref="ExtractionResult"/> pages.
    /// </summary>
    public static (SaveReviewRevisionOutcome? Error, IReadOnlyList<WorkOrderReviewField>? BuiltFields) ValidateAndBuildFields(
        Guid revisionId,
        IReadOnlyList<CanonicalReviewFieldInput> orderedInputs,
        WorkOrderMachineSnapshot machineSnapshot,
        IReadOnlyList<ExtractedPageView> parsedPages)
    {
        var built = new WorkOrderReviewField[WorkOrderReviewSchema.FieldCount];

        for (var i = 0; i < WorkOrderReviewSchema.FieldCount; i++)
        {
            var spec = WorkOrderReviewSchema.Fields[i];
            var input = orderedInputs[i];
            var candidate = machineSnapshot.Fields[i];
            ReviewSourceReference? resolvedSource = null;

            if (input.Decision == ReviewFieldDecision.Accepted)
            {
                if (candidate.Status != MachineCandidateStatus.Suggested || candidate.Value is null)
                {
                    return (
                        new SaveReviewRevisionOutcome.ValidationRejected(
                            "accepted_without_machine_suggestion",
                            $"Field '{spec.FieldKey}' cannot be marked 'accepted' because machine candidate status is '{candidate.Status.ToWire()}'."),
                        null);
                }

                if (!string.Equals(input.Value, candidate.Value, StringComparison.Ordinal))
                {
                    return (
                        new SaveReviewRevisionOutcome.ValidationRejected(
                            "accepted_value_mismatch",
                            $"Field '{spec.FieldKey}' decision 'accepted' requires exact equality to the original machine suggestion."),
                        null);
                }

                if (input.CallerConsultedSource is { } callerCoord)
                {
                    if (candidate.Source is null || callerCoord != candidate.Source.ToCoordinate())
                    {
                        return (
                            new SaveReviewRevisionOutcome.ValidationRejected(
                                "invalid_source_reference",
                                $"Field '{spec.FieldKey}' decision 'accepted' cannot specify source coordinates different from the machine candidate."),
                            null);
                    }
                }

                resolvedSource = candidate.Source;
            }
            else if (input.CallerConsultedSource is { } coord)
            {
                if (!WorkOrderReviewSuggestions.TryResolveConsultedSource(parsedPages, coord, out var verifiedRef, out var srcError))
                {
                    return (
                        new SaveReviewRevisionOutcome.ValidationRejected("invalid_source_reference", srcError!),
                        null);
                }

                resolvedSource = verifiedRef;
            }

            built[i] = WorkOrderReviewField.Create(
                revisionId,
                spec,
                input.Decision,
                input.Value,
                input.UnknownReason,
                resolvedSource);
        }

        return (null, built);
    }
}
