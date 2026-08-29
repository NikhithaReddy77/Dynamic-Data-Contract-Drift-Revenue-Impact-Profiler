from difflib import SequenceMatcher
from .models import ColumnSchema, DriftEvent, DriftType, TableSchema

RENAME_CONFIDENCE_THRESHOLD = 0.45


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _sample_overlap(a: ColumnSchema, b: ColumnSchema) -> float:
    if not a.sample_values or not b.sample_values:
        return 0.0
    set_a, set_b = set(a.sample_values), set(b.sample_values)
    return len(set_a & set_b) / max(len(set_a | set_b), 1)


def _rename_score(removed: ColumnSchema, added: ColumnSchema) -> float:
    name_sim = _name_similarity(removed.name, added.name)
    type_match = 1.0 if removed.data_type == added.data_type else 0.0
    value_overlap = _sample_overlap(removed, added)
    return (0.5 * name_sim) + (0.25 * type_match) + (0.25 * value_overlap)


def diff_schemas(old: TableSchema, new: TableSchema) -> list[DriftEvent]:
    if old.fqn != new.fqn:
        raise ValueError(f"Cannot diff schemas for different tables: {old.fqn} vs {new.fqn}")

    old_cols = {c.name: c for c in old.columns}
    new_cols = {c.name: c for c in new.columns}

    removed_names = set(old_cols) - set(new_cols)
    added_names = set(new_cols) - set(old_cols)
    common_names = set(old_cols) & set(new_cols)

    events: list[DriftEvent] = []

    for name in common_names:
        old_c, new_c = old_cols[name], new_cols[name]
        if old_c.data_type != new_c.data_type:
            events.append(DriftEvent(
                table_fqn=new.fqn, drift_type=DriftType.TYPE_CHANGED,
                old_column=name, new_column=name,
                old_type=old_c.data_type, new_type=new_c.data_type, confidence=1.0,
            ))
        if old_c.nullable != new_c.nullable:
            events.append(DriftEvent(
                table_fqn=new.fqn, drift_type=DriftType.NULLABILITY_CHANGED,
                old_column=name, new_column=name, confidence=1.0,
            ))

    unmatched_removed = set(removed_names)
    unmatched_added = set(added_names)

    candidates = []
    for r_name in removed_names:
        for a_name in added_names:
            score = _rename_score(old_cols[r_name], new_cols[a_name])
            if score >= RENAME_CONFIDENCE_THRESHOLD:
                candidates.append((score, r_name, a_name))
    candidates.sort(reverse=True, key=lambda x: x[0])

    for score, r_name, a_name in candidates:
        if r_name in unmatched_removed and a_name in unmatched_added:
            events.append(DriftEvent(
                table_fqn=new.fqn, drift_type=DriftType.COLUMN_RENAMED,
                old_column=r_name, new_column=a_name,
                old_type=old_cols[r_name].data_type, new_type=new_cols[a_name].data_type,
                confidence=round(score, 2),
            ))
            unmatched_removed.discard(r_name)
            unmatched_added.discard(a_name)

    for name in unmatched_removed:
        events.append(DriftEvent(table_fqn=new.fqn, drift_type=DriftType.COLUMN_REMOVED,
                                  old_column=name, confidence=1.0))
    for name in unmatched_added:
        events.append(DriftEvent(table_fqn=new.fqn, drift_type=DriftType.COLUMN_ADDED,
                                  new_column=name, confidence=1.0))

    return events
