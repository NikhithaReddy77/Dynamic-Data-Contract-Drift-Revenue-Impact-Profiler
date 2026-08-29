"""
Data-Contract Drift Guard — Streamlit dashboard.

A browser-viewable version of the notebook demo. Runs entirely on mock
data by default (works with zero setup); optionally connects to a real
Snowflake account if credentials are provided via Streamlit secrets.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from engine import calculate_impact, diff_schemas, generate_adapter
from engine.mock_data import get_lineage_graph, get_schema_after, get_schema_before

st.set_page_config(page_title="Data-Contract Drift Guard", page_icon="🛡️", layout="wide")

st.title("🛡️ Data-Contract Drift Guard")
st.caption(
    "Detects schema drift, quantifies the live revenue impact, and proposes a fix — "
    "without ever auto-applying changes to production."
)

# ---------------------------------------------------------------------------
# Sidebar: data source
# ---------------------------------------------------------------------------
st.sidebar.header("Data source")
use_real_snowflake = st.sidebar.toggle(
    "Connect to real Snowflake",
    value=False,
    help="Requires SNOWFLAKE_* secrets configured in Streamlit Cloud settings.",
)

if use_real_snowflake:
    try:
        from engine.snowflake_connector import fetch_table_schema
        database = st.sidebar.text_input("Database", "MY_TEST_DB")
        schema_name = st.sidebar.text_input("Schema", "PUBLIC")
        table = st.sidebar.text_input("Table", "CUSTOMER")
        st.sidebar.info("Live schema fetch runs when you click 'Detect drift' below.")
    except Exception as e:
        st.sidebar.error(f"Snowflake connector unavailable: {e}")
        use_real_snowflake = False

st.sidebar.divider()
st.sidebar.markdown(
    "**How to read this:**\n\n"
    "- 🟢 Confidence = how sure the diff engine is this drift is real\n"
    "- 💵 Exposure = estimated revenue at risk per hour, as a range\n"
    "- 🛠️ Adapter = a proposed SQL fix, never auto-applied"
)

# ---------------------------------------------------------------------------
# Run detection
# ---------------------------------------------------------------------------
run = st.button("🔍 Detect drift", type="primary")

if run:
    with st.spinner("Diffing schemas..."):
        if use_real_snowflake:
            if "before_schema" not in st.session_state:
                st.warning(
                    "No baseline snapshot saved yet for this table. Click 'Save current "
                    "schema as baseline' first, make a change in Snowflake, then click "
                    "'Detect drift' again."
                )
                st.stop()
            before = st.session_state["before_schema"]
            after = fetch_table_schema(database, schema_name, table)
            lineage = get_lineage_graph()  # lineage is still mock unless you wire in real assets
        else:
            before = get_schema_before()
            after = get_schema_after()
            lineage = get_lineage_graph()

        events = diff_schemas(before, after)

    if not events:
        st.success("No drift detected. Schema is stable.")
    else:
        results = [(e, calculate_impact(e, lineage)) for e in events]

        # --- Summary metrics row ---
        total_exposure = sum(i.estimated_dollars_per_hour for _, i in results)
        col1, col2, col3 = st.columns(3)
        col1.metric("Drift events detected", len(events))
        col2.metric("Total estimated exposure", f"${total_exposure:,.0f}/hr")
        col3.metric(
            "Highest-confidence event",
            f"{max(e.confidence for e, _ in results):.0%}",
        )

        st.divider()

        # --- Per-event detail cards ---
        for event, impact in results:
            with st.container(border=True):
                label = (
                    f"{event.old_column} → {event.new_column}"
                    if event.old_column and event.new_column
                    else (event.new_column or event.old_column)
                )
                st.subheader(f"{event.drift_type.value.replace('_', ' ').title()}: `{label}`")
                st.write(f"Confidence: **{event.confidence:.0%}**")

                m1, m2 = st.columns(2)
                m1.metric(
                    "Estimated exposure",
                    f"${impact.estimated_dollars_per_hour:,.0f}/hr",
                    help=f"Range: ${impact.confidence_low:,.0f}–${impact.confidence_high:,.0f}/hr",
                )
                m2.metric("Exposed so far", f"${impact.estimated_dollars_exposed_so_far:,.2f}")

                if impact.affected_assets:
                    st.write(f"**Affected assets:** {', '.join(impact.affected_assets)}")

                adapter = generate_adapter(event)
                if adapter:
                    with st.expander("🛠️ Proposed adapter (requires approval)"):
                        st.code(adapter.suggested_sql, language="sql")
                        st.caption(adapter.rationale)
                        approve_col, _ = st.columns([1, 3])
                        approve_col.button(
                            "✅ Approve & copy SQL", key=f"approve_{event.table_fqn}_{label}"
                        )

        st.divider()

        # --- Charts ---
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            labels = [
                f"{e.old_column} → {e.new_column}" if e.old_column and e.new_column
                else (e.new_column or e.old_column)
                for e, _ in results
            ]
            point = [i.estimated_dollars_per_hour for _, i in results]
            low = [i.confidence_low for _, i in results]
            high = [i.confidence_high for _, i in results]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=labels, y=point,
                error_y=dict(type="data", symmetric=False,
                              array=[h - p for h, p in zip(high, point)],
                              arrayminus=[p - l for p, l in zip(point, low)]),
                marker_color="#1D9E75",
            ))
            fig.update_layout(title="Revenue exposure by drift event", yaxis_title="$ / hour",
                               template="plotly_white", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with chart_col2:
            asset_nodes = [n for n, d in lineage.graph.nodes(data=True) if "asset" in d]
            rows = []
            for node_id in asset_nodes:
                asset = lineage.graph.nodes[node_id]["asset"]
                for col, crit in asset.column_criticality.items():
                    rows.append({"asset": asset.name, "column": col, "criticality": crit})
            if rows:
                df = pd.DataFrame(rows)
                pivot = df.pivot(index="asset", columns="column", values="criticality")
                fig2 = px.imshow(pivot, text_auto=".0%", color_continuous_scale="Oranges",
                                  title="Column criticality by downstream asset")
                st.plotly_chart(fig2, use_container_width=True)

if use_real_snowflake and not run:
    if st.sidebar.button("📸 Save current schema as baseline"):
        try:
            from engine.snowflake_connector import fetch_table_schema
            schema_snapshot = fetch_table_schema(database, schema_name, table)
            st.session_state["before_schema"] = schema_snapshot
            st.sidebar.success(f"Baseline saved: {len(schema_snapshot.columns)} columns.")
        except Exception as e:
            st.sidebar.error(f"Could not fetch schema: {e}")

if not run:
    st.info("👆 Click **Detect drift** to run the engine on mock data (default) or a live "
            "Snowflake table (toggle in the sidebar).")
