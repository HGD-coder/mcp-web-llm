import sqlite3
import os
from pathlib import Path
from datetime import datetime
import logging

def get_db_path() -> str:
    env_dir = os.getenv("MCP_WEB_LLM_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir / "history.db")

    try:
        # Default to ~/.mcp-web-llm
        data_dir = Path.home() / ".mcp-web-llm"
        data_dir.mkdir(parents=True, exist_ok=True)
        # Test if we have write permission (sandbox might block sqlite3 implicitly)
        test_file = data_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return str(data_dir / "history.db")
    except Exception as e:
        logging.warning(f"Cannot write to {Path.home() / '.mcp-web-llm'}, falling back to current directory: {e}")
        return str(Path(".") / "history.db")

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        cursor.execute('''
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        pass

    conn.commit()
    conn.close()

def save_message(model_name: str, role: str, content: str):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # To be safe against previous schema with session_id, we just insert specifying only the fields we have
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'session_id' in columns:
            cursor.execute(
                'INSERT INTO messages (session_id, model_name, role, content) VALUES (?, ?, ?, ?)',
                ("default", model_name, role, content)
            )
        else:
            cursor.execute(
                'INSERT INTO messages (model_name, role, content) VALUES (?, ?, ?)',
                (model_name, role, content)
            )
        
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to save message to history.db: {e}")

# Initialize DB on module load
try:
    init_db()
except Exception as e:
    import traceback
    logging.error(f"Failed to initialize history.db: {e}\n{traceback.format_exc()}")
