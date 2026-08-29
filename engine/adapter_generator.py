from .models import AdapterSuggestion, DriftEvent, DriftType


def generate_adapter(drift: DriftEvent) -> AdapterSuggestion | None:
    if drift.drift_type != DriftType.COLUMN_RENAMED:
        return None

    table = drift.table_fqn
    old_col, new_col = drift.old_column, drift.new_column

    sql = (
        f"-- Auto-generated compatibility view. Review before applying.\n"
        f"CREATE OR REPLACE VIEW {table}_COMPAT AS\n"
        f"SELECT *,\n"
        f"       {new_col} AS {old_col}  -- restores old column name for existing consumers\n"
        f"FROM {table};"
    )

    rationale = (
        f"Schema differ inferred `{old_col}` was renamed to `{new_col}` "
        f"(confidence {drift.confidence:.0%}, based on name similarity, "
        f"type match, and sample-value overlap). This view lets existing "
        f"queries/dashboards referencing `{old_col}` keep working while "
        f"downstream owners migrate to `{new_col}` on their own schedule."
    )

    return AdapterSuggestion(
        drift_event=drift, suggested_sql=sql, mapping_confidence=drift.confidence,
        rationale=rationale, requires_human_approval=True, approved=False,
    )
