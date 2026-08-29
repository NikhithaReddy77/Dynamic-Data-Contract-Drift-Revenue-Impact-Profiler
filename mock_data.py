from .lineage import LineageGraph
from .models import ColumnSchema, DownstreamAsset, TableSchema


def get_schema_before() -> TableSchema:
    return TableSchema(
        database="ANALYTICS", schema_name="PUBLIC", table="CHECKOUT_EVENTS",
        columns=[
            ColumnSchema(name="event_id", data_type="VARCHAR", nullable=False,
                         sample_values=["evt_001", "evt_002", "evt_003"]),
            ColumnSchema(name="user_id", data_type="VARCHAR", nullable=False,
                         sample_values=["usr_9f2", "usr_1a4", "usr_7c3"]),
            ColumnSchema(name="discount_pct", data_type="FLOAT", nullable=True,
                         sample_values=["0.10", "0.0", "0.25"]),
            ColumnSchema(name="order_total", data_type="FLOAT", nullable=False,
                         sample_values=["49.99", "120.00", "18.50"]),
            ColumnSchema(name="internal_notes", data_type="VARCHAR", nullable=True,
                         sample_values=["", "vip customer", ""]),
        ],
    )


def get_schema_after() -> TableSchema:
    return TableSchema(
        database="ANALYTICS", schema_name="PUBLIC", table="CHECKOUT_EVENTS",
        columns=[
            ColumnSchema(name="event_id", data_type="VARCHAR", nullable=False,
                         sample_values=["evt_001", "evt_002", "evt_003"]),
            ColumnSchema(name="customer_id", data_type="VARCHAR", nullable=False,
                         sample_values=["usr_9f2", "usr_1a4", "usr_7c3"]),
            ColumnSchema(name="discount_pct", data_type="FLOAT", nullable=True,
                         sample_values=["0.10", "0.0", "0.25"]),
            ColumnSchema(name="order_total", data_type="FLOAT", nullable=False,
                         sample_values=["49.99", "120.00", "18.50"]),
            ColumnSchema(name="internal_notes", data_type="VARCHAR", nullable=True,
                         sample_values=["", "vip customer", ""]),
        ],
    )


def get_lineage_graph() -> LineageGraph:
    lineage = LineageGraph()
    table = get_schema_before().fqn

    checkout_dashboard = DownstreamAsset(
        asset_id="dash_checkout_revenue", asset_type="dashboard",
        name="Checkout Revenue (Exec Dashboard)", revenue_per_hour=42_000.0,
        column_criticality={"user_id": 0.9, "discount_pct": 0.8, "order_total": 1.0, "internal_notes": 0.05},
    )
    fraud_model = DownstreamAsset(
        asset_id="ml_fraud_scoring", asset_type="ml_model",
        name="Real-time Fraud Scoring Model", revenue_per_hour=15_500.0,
        column_criticality={"user_id": 0.95, "discount_pct": 0.2, "order_total": 0.6, "internal_notes": 0.0},
    )

    lineage.add_asset(checkout_dashboard)
    lineage.add_asset(fraud_model)
    lineage.link(table, checkout_dashboard.asset_id,
                 columns_used=["user_id", "discount_pct", "order_total", "internal_notes"])
    lineage.link(table, fraud_model.asset_id, columns_used=["user_id", "discount_pct", "order_total"])

    return lineage
