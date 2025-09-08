from sqlalchemy import create_engine, text
import pandas as pd
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.pgvector import PgVector
import sys

# SQLAlchemy connection string (with psycopg2 driver)
DB_URL = "postgresql+psycopg2://ai:ai@localhost:5532/ai"

# Create SQLAlchemy engine
engine = create_engine(DB_URL)

def load_knowledge_base(table_name: str):
    knowledge_base = WebsiteKnowledgeBase(
        urls=["https://learnkube.com/troubleshooting-deployments"],
        # Number of links to follow from the seed URLs
        max_links=2,
        # Table name: ai.local_rag_documents
        vector_db=PgVector(
            table_name=table_name,
            db_url=DB_URL,
        ),
    )
    knowledge_base.load()


def view_table(table_name: str, limit: int = 10):
    """
    View rows from a given table (dynamic table name).
    """
    with engine.connect() as conn:
        if "." in table_name:
            schema, table = table_name.split(".")
            query = text(f'SELECT * FROM "{schema}"."{table}" LIMIT :limit')
        else:
            query = text(f'SELECT * FROM "{table_name}" LIMIT :limit')

        df = pd.read_sql(query, conn, params={"limit": limit})
    return df[['id','content']]


def list_pgvector_tables():
    """
    List all tables that contain pgvector (embedding) columns.
    """
    query = """
    SELECT n.nspname AS schema,
           c.relname AS table,
           a.attname AS column
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_attribute a ON a.attrelid = c.oid
    JOIN pg_type t ON a.atttypid = t.oid
    WHERE t.typname = 'vector' AND a.attnum > 0;
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df

def truncate_table(table_name: str):
    """
    Truncate a table safely (remove all rows) dynamically.
    """
    with engine.begin() as conn:  # begin() gives automatic commit
        if "." in table_name:
            schema, table = table_name.split(".")
            sql_stmt = text(f'TRUNCATE TABLE "{schema}"."{table}" RESTART IDENTITY CASCADE')
        else:
            sql_stmt = text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
        conn.execute(sql_stmt)
    print(f"Table '{table_name}' truncated successfully.")

def drop_table(table_name: str):
    """
    Drop a table dynamically (removes the table and all its data).
    """
    with engine.begin() as conn:  # begin() gives automatic commit
        sql_stmt = text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
        conn.execute(sql_stmt)
    print(f"Table '{table_name}' dropped successfully.")


if __name__ == "__main__":
    
    print("📌 Tables with pgvector columns:")
    print(list_pgvector_tables())
    
    if len(sys.argv) < 2:
        print("provide table name")
        exit()

    table_name = sys.argv[1]    
    # Example usage
    #load_knowledge_base("website_documents")
    #print("\n📌 Sample rows from table:")
    
    #print(view_table("website_documents", 5))
    #truncate_table(table_name)
    drop_table(table_name)

