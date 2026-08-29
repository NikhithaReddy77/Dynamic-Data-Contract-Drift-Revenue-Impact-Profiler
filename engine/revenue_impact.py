from datetime import datetime, timezone
from .lineage import LineageGraph
from .models import DriftEvent, RevenueImpact

BASE_UNCERTAINTY_PCT = 0.15


def calculate_impact(drift: DriftEvent, lineage: LineageGraph, now: datetime | None = None) -> RevenueImpact:
    now = now or datetime.now(timezone.utc)

    candidate_columns = [c for c in (drift.old_column, drift.new_column) if c]
    seen_asset_ids: set[str] = set()
    matched_assets = []
    for col in candidate_columns:
        for asset in lineage.downstream_assets_for_column(drift.table_fqn, col):
            if asset.asset_id not in seen_asset_ids:
                seen_asset_ids.add(asset.asset_id)
                matched_assets.append((asset, col))

    point_estimate = 0.0
    for asset, matched_column in matched_assets:
        criticality = asset.column_criticality.get(matched_column, 0.5)
        point_estimate += asset.revenue_per_hour * criticality

    assets = [a for a, _ in matched_assets]

    uncertainty_pct = BASE_UNCERTAINTY_PCT + (1 - drift.confidence) * 0.35
    low = point_estimate * (1 - uncertainty_pct) * drift.confidence
    high = point_estimate * (1 + uncertainty_pct)

    detected = drift.detected_at
    if detected.tzinfo is None:
        detected = detected.replace(tzinfo=timezone.utc)
    minutes_elapsed = max((now - detected).total_seconds() / 60, 0)
    dollars_exposed_so_far = point_estimate * (minutes_elapsed / 60)

    return RevenueImpact(
        drift_event=drift,
        affected_assets=[a.asset_id for a in assets],
        estimated_dollars_per_hour=round(point_estimate, 2),
        confidence_low=round(max(low, 0), 2),
        confidence_high=round(high, 2),
        minutes_since_detected=round(minutes_elapsed, 1),
        estimated_dollars_exposed_so_far=round(dollars_exposed_so_far, 2),
    )
