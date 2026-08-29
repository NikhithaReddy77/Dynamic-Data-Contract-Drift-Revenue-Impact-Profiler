# Data-Contract Drift Guard — Live Dashboard

Browser-based dashboard for the Data-Contract Drift Guard project: detects schema drift,
quantifies live revenue exposure, and proposes (never auto-applies) a SQL fix.

Runs on mock data by default. Toggle "Connect to real Snowflake" in the sidebar to run
against a live warehouse (requires SNOWFLAKE_* secrets configured in Streamlit Cloud).

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
Push this folder to a GitHub repo, then deploy for free at share.streamlit.io — point it
at `app.py`.
