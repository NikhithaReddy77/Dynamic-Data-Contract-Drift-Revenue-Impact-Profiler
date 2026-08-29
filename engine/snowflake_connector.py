"""
Snowflake connector wrapper for the Streamlit app.
Reads credentials from Streamlit secrets (st.secrets), never hardcoded.
"""
import streamlit as st
from .models import ColumnSchema, TableSchema


def fetch_table_schema(database: str, schema: str, table: str) -> TableSchema:
    import snowflake.connector

    conn = snowflake.connector.connect(
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
        role=st.secrets["SNOWFLAKE_ROLE"],
        database=database,
        schema=schema,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_catalog = %s AND table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (database, schema, table),
        )
        columns = [
            ColumnSchema(name=row[0], data_type=row[1], nullable=(row[2] == "YES"))
            for row in cursor.fetchall()
        ]
        if not columns:
            raise ValueError(f"No columns found for {database}.{schema}.{table}")
        return TableSchema(database=database, schema_name=schema, table=table, columns=columns)
    finally:
        conn.close()
