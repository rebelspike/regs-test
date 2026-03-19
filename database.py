import sqlite3
from flask import g
import os

DATABASE = 'regs.db'

def get_db():
    """Get database connection from Flask's application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database from schema.sql file."""
    from app import app
    
    schema_file = 'schema.sql'
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file '{schema_file}' not found. Please ensure schema.sql exists in the project directory.")
    
    with app.app_context():
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        
        # Read and execute the SQL schema file
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        db.executescript(schema_sql)
        db.close()
        print(f"✅ Database initialized from {schema_file}")