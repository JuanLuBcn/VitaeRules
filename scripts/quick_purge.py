"""
Quick memory cleanup - no confirmations, just clean everything.
Use this for rapid testing iterations.
"""

import shutil
import sqlite3
from pathlib import Path

from app.config import get_settings


def quick_purge():
    """Instantly purge all memory without confirmations."""
    settings = get_settings()
    
    stats = {
        'conversations': 0,
        'vector_files': 0,
        'storage_files': 0
    }
    
    # 1. SQLite database
    if settings.sql_db_path.exists():
        with sqlite3.connect(settings.sql_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM conversations")
            stats['conversations'] = cursor.fetchone()[0]
            conn.execute("DELETE FROM conversations")
            conn.commit()
    
    # 2. Vector store
    if settings.vector_store_path.exists():
        stats['vector_files'] = sum(1 for _ in settings.vector_store_path.rglob('*') if _.is_file())
        shutil.rmtree(settings.vector_store_path)
        settings.vector_store_path.mkdir(parents=True, exist_ok=True)
    
    # 3. Storage (skip - usually has persistent data)
    
    return stats


if __name__ == "__main__":
    stats = quick_purge()
    print(f"✅ Purged: {stats['conversations']} conversations, {stats['vector_files']} vector files")
