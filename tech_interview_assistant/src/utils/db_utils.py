import json
import sqlite3
from typing import List
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langchain_community.utilities.sql_database import SQLDatabase


def initialize_db_connection(db_name):
    db = SQLDatabase.from_uri(F"sqlite:///{db_name}")
    conn = sqlite3.connect(db_name)
    return db, conn


def build_sql_agent(db, llm, system_message):
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    print(toolkit.get_tools())
    agent_executor = create_react_agent(
        llm, toolkit.get_tools(), state_modifier=system_message
    )
    return agent_executor


def fetch_rows_from_sql(db_path: str, table_name: str) -> List[dict]:
    """
    Connect to a local SQL db, retrieve 'description' and 'solution' columns.
    Return a list of dicts with those keys.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"SELECT description, solution FROM {table_name}"
    cursor.execute(query)
    
    rows = []
    for row in cursor.fetchall():
        desc, sol = row
        rows.append({
            "description": desc,
            "solution": json.load(sol)
        })
    
    conn.close()
    return rows