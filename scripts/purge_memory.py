"""
Memory cleanup utility to purge all stored data and start fresh.

This script will:
1. Clear all short-term memory (conversation history)
2. Clear all long-term memory (vector store with notes/tasks)
3. Reset any session data
4. Provide a clean slate for testing
"""

import shutil
import sqlite3
from pathlib import Path

from app.config import get_settings


def purge_memory():
    """Purge all memory stores and start fresh."""
    settings = get_settings()
    
    print("🧹 Starting memory cleanup...")
    print("=" * 80)
    
    # 1. Clean SQLite database (short-term memory)
    if settings.sql_db_path.exists():
        print(f"\n📊 Cleaning SQLite database: {settings.sql_db_path}")
        try:
            with sqlite3.connect(settings.sql_db_path) as conn:
                # Clear conversations table
                cursor = conn.execute("SELECT COUNT(*) FROM conversations")
                conv_count = cursor.fetchone()[0]
                conn.execute("DELETE FROM conversations")
                print(f"   ✓ Deleted {conv_count} conversation messages")
                
                # Clear any other tables if they exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    if table != 'conversations':
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        conn.execute(f"DELETE FROM {table}")
                        print(f"   ✓ Deleted {count} rows from {table}")
                
                conn.commit()
                print(f"   ✓ Database cleaned successfully")
        except sqlite3.Error as e:
            print(f"   ⚠️  Warning: {e}")
    else:
        print(f"\n📊 SQLite database not found: {settings.sql_db_path}")
        print("   → Nothing to clean")
    
    # 2. Clean vector store (long-term memory)
    if settings.vector_store_path.exists():
        print(f"\n🗄️  Removing vector store: {settings.vector_store_path}")
        try:
            # Count files before deletion
            file_count = sum(1 for _ in settings.vector_store_path.rglob('*') if _.is_file())
            
            # Remove entire directory
            shutil.rmtree(settings.vector_store_path)
            print(f"   ✓ Deleted {file_count} files")
            
            # Recreate empty directory
            settings.vector_store_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Created fresh vector store directory")
        except Exception as e:
            print(f"   ⚠️  Warning: {e}")
    else:
        print(f"\n🗄️  Vector store not found: {settings.vector_store_path}")
        print("   → Nothing to clean")
    
    # 3. Clean storage directory (if it contains any runtime data)
    if settings.storage_path.exists():
        print(f"\n📁 Checking storage directory: {settings.storage_path}")
        file_count = sum(1 for _ in settings.storage_path.rglob('*') if _.is_file())
        
        if file_count > 0:
            print(f"   Found {file_count} files")
            confirm = input("   ⚠️  Delete storage files? (yes/no): ")
            if confirm.lower() in ['yes', 'y', 'si', 's']:
                shutil.rmtree(settings.storage_path)
                settings.storage_path.mkdir(parents=True, exist_ok=True)
                print(f"   ✓ Deleted {file_count} files")
            else:
                print(f"   → Skipped storage cleanup")
        else:
            print("   → No files to clean")
    
    # 4. Summary
    print("\n" + "=" * 80)
    print("✅ Memory cleanup complete!")
    print("\n📋 Summary:")
    print("   • Short-term memory (conversations): Cleared")
    print("   • Long-term memory (vector store): Cleared")
    print("   • Session data: Will reset on next bot start")
    print("\n🚀 Ready to start fresh!")
    print("=" * 80)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  MEMORY PURGE UTILITY                        ║
║                                                              ║
║  This will DELETE ALL stored data:                          ║
║  • All conversation history                                 ║
║  • All notes and tasks                                      ║
║  • All memories                                             ║
║                                                              ║
║  This action CANNOT be undone!                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    confirm = input("Are you sure you want to purge all memory? (yes/no): ")
    
    if confirm.lower() in ['yes', 'y']:
        purge_memory()
    else:
        print("\n❌ Cleanup cancelled. No data was deleted.")
