import sqlite3

conn = sqlite3.connect('data/app.sqlite')
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cursor.fetchall())

# Check memories
try:
    cursor.execute("SELECT COUNT(*) FROM memories")
    count = cursor.fetchone()[0]
    print(f"\nTotal memories: {count}")
    
    if count > 0:
        cursor.execute("SELECT id, content, created_at FROM memories LIMIT 10")
        print("\nSample memories:")
        for row in cursor.fetchall():
            print(f"  ID {row[0]}: {row[1][:100]}... (created: {row[2]})")
except Exception as e:
    print(f"Error checking memories: {e}")

# Check lists
try:
    cursor.execute("SELECT COUNT(*) FROM lists")
    count = cursor.fetchone()[0]
    print(f"\nTotal lists: {count}")
    
    if count > 0:
        cursor.execute("SELECT id, name, created_at FROM lists LIMIT 10")
        print("\nSample lists:")
        for row in cursor.fetchall():
            print(f"  ID {row[0]}: {row[1]} (created: {row[2]})")
except Exception as e:
    print(f"Error checking lists: {e}")

# Check tasks
try:
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    print(f"\nTotal tasks: {count}")
    
    if count > 0:
        cursor.execute("SELECT id, description, completed, created_at FROM tasks LIMIT 10")
        print("\nSample tasks:")
        for row in cursor.fetchall():
            status = "✓" if row[2] else "○"
            print(f"  {status} ID {row[0]}: {row[1][:80]}... (created: {row[3]})")
except Exception as e:
    print(f"Error checking tasks: {e}")

conn.close()
