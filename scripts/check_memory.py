"""Check memory status after cleanup."""

import sqlite3
from pathlib import Path
from app.config import get_settings


def check_memory_status():
    """Check current memory status."""
    settings = get_settings()
    
    print("\n" + "=" * 80)
    print("📊 MEMORY STATUS REPORT")
    print("=" * 80)
    
    # 1. SQLite database
    print("\n🗄️  Short-Term Memory (SQLite)")
    if settings.sql_db_path.exists():
        with sqlite3.connect(settings.sql_db_path) as conn:
            # List tables
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"   Database: {settings.sql_db_path}")
            print(f"   Tables: {len(tables)}")
            
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   • {table}: {count} rows")
    else:
        print(f"   ❌ Database not found: {settings.sql_db_path}")
    
    # 2. Vector store
    print("\n📚 Long-Term Memory (Vector Store)")
    if settings.vector_store_path.exists():
        file_count = sum(1 for _ in settings.vector_store_path.rglob('*') if _.is_file())
        dir_count = sum(1 for _ in settings.vector_store_path.rglob('*') if _.is_dir())
        
        print(f"   Directory: {settings.vector_store_path}")
        print(f"   Files: {file_count}")
        print(f"   Directories: {dir_count}")
        
        if file_count == 0:
            print(f"   ✅ Vector store is empty (clean)")
        else:
            print(f"   📦 Vector store contains data")
    else:
        print(f"   ❌ Vector store not found: {settings.vector_store_path}")
    
    # 3. Storage
    print("\n💾 Storage Directory")
    if settings.storage_path.exists():
        file_count = sum(1 for _ in settings.storage_path.rglob('*') if _.is_file())
        
        print(f"   Directory: {settings.storage_path}")
        print(f"   Files: {file_count}")
        
        if file_count == 0:
            print(f"   ✅ Storage is empty")
        else:
            print(f"   📁 Storage contains {file_count} files")
    else:
        print(f"   ❌ Storage not found: {settings.storage_path}")
    
    print("\n" + "=" * 80)
    print("✅ Status check complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    check_memory_status()
