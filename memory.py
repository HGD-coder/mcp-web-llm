import sqlite3
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_db_path() -> str:
    env_dir = os.getenv("MCP_WEB_LLM_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
    else:
        # Default to ~/.mcp-web-llm
        data_dir = Path.home() / ".mcp-web-llm"
    
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create data directory {data_dir}: {e}")
        # fallback to current directory
        data_dir = Path(".")
        
    return str(data_dir / "history.db")

def init_db():
    db_path = get_db_path()
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize database at {db_path}: {e}")

def save_message(session_id: str, model: str, role: str, content: str):
    if not content:
        return
    db_path = get_db_path()
    try:
        with sqlite3.connect(db_path, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (session_id, model, role, content) VALUES (?, ?, ?, ?)",
                (session_id, model, role, content)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save message to DB: {e}")

# Initialize db on module load
init_db()
