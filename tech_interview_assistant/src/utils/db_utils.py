import sqlite3
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
# from langchain_community.tools.sql_database.tool import (
#     InfoSQLDatabaseTool,
#     ListSQLDatabaseTool,
#     QuerySQLCheckerTool,
#     QuerySQLDataBaseTool,
# )
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