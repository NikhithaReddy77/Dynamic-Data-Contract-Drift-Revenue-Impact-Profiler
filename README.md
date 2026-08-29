# Dynamic-Data-Contract-Drift-Revenue-Impact-Profiler
Detects schema drift, quantifies revenue impact, and proposes fixes — tested against a live Snowflake connection.
# Data-Contract Drift Guard

Autonomous schema drift detection + real-time revenue impact quantification + self-healing adapter suggestions.

## What this does

Companies lose money silently when upstream engineers rename or change database columns
(e.g. `user_id` → `customer_id`), breaking downstream dashboards and ML models without
anyone noticing until revenue numbers look wrong. This project detects that drift,
estimates the live dollar cost of it, and proposes a fix — without ever auto-applying
changes to production.

**Pipeline:** Schema snapshot → diff engine (infers renames, not just add/remove) →
lineage graph (traces which dashboards/models are affected) → revenue impact calculator
(live $/hour exposure with a confidence range) → adapter generator (proposes a SQL fix,
requires human approval).

Tested end-to-end against a **live Snowflake connection**, not just mock data.

## Example output
DRIFT: column_renamed (C_NAME -> CUSTOMER_FULL_NAME) confidence=89%
Exposure: $5,164-$20,272/hr (point estimate $15,300/hr)
Affected assets: ['dash_customer_360']
Proposed adapter:
-- Auto-generated compatibility view. Review before applying.
CREATE OR REPLACE VIEW MY_TEST_DB.PUBLIC.CUSTOMER_COMPAT AS
SELECT *, CUSTOMER_FULL_NAME AS C_NAME
FROM MY_TEST_DB.PUBLIC.CUSTOMER;


## Why this is different from generic drift detection

Most data observability tools alert on schema changes with a qualitative severity label
("high/medium/low"). This project instead:
- **Infers renames** (name similarity + type match + sample-value overlap) instead of
  reporting an unrelated add + remove pair
- **Traces impact at the column level**, not table level — a change to `internal_notes`
  isn't treated the same as a change to `discount_pct`, even in the same table
- **Quantifies exposure as a live dollar range**, not a severity bucket
- **Proposes a fix but never auto-applies it** — every suggested SQL adapter requires
  human approval, since auto-patching production pipelines can turn an outage into a
  data-corruption incident

## Tech stack

- **Python** — core engine (pydantic for data models, networkx for the lineage graph)
- **Snowflake** — live schema introspection via `snowflake-connector-python`
- **Plotly** — revenue exposure charts and criticality heatmaps
- **Google Colab** — development and demo environment (see notebook)

## Run it yourself

Open `DataContractGuard_Colab.ipynb` in Google Colab and run the cells top to bottom.
Cells 1-11 run entirely on mock data, no credentials needed. Cells 12+ connect to a real
Snowflake account — add your credentials as Colab secrets (`SNOWFLAKE_ACCOUNT`,
`SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_ROLE`) to try it
against a live warehouse.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/data-contract-drift-guard/blob/main/DataContractGuard_Colab.ipynb)

## Roadmap

- [ ] Wrap engine in a FastAPI service
- [ ] Postgres persistence for drift history and adapter approvals
- [ ] Next.js dashboard (multi-user, replacing notebook charts)
- [ ] Auth + per-company workspace isolation for real pilot use
