"""
Database Migration: Add Enhanced Fields
========================================

Adds people, location, media, and tag support to lists and tasks.

Version: 2.0
Date: 2025-10-26
Author: Vitti Enhancement Team

Changes:
- list_items: Add people, location, latitude, longitude, place_id, tags, notes, media_path, metadata
- tasks: Add people, location, latitude, longitude, place_id, tags, media_path, reminder_distance, metadata

Usage:
    python scripts/migrate_enhanced_fields.py
"""

import sqlite3
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.config import get_settings
from app.tracing import get_tracer

logger = get_tracer()


def migrate_lists_db(db_path: Path) -> bool:
    """
    Add enhanced fields to list_items table.
    
    New fields:
    - people: JSON array of person names ["Juan", "María"]
    - location: Human-readable location string
    - latitude, longitude: GPS coordinates
    - place_id: Google Place ID for stable reference
    - tags: JSON array of tags ["urgente", "orgánico"]
    - notes: Additional notes/context
    - media_path: Path to photo/media file
    - metadata: JSON for additional data
    
    Returns:
        True if migration was performed, False if already migrated
    """
    if not db_path.exists():
        logger.warning(f"Database not found: {db_path}")
        return False
    
    with sqlite3.connect(db_path) as conn:
        # Check if migration already done
        cursor = conn.execute("PRAGMA table_info(list_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "people" in columns:
            logger.info("list_items already migrated, skipping")
            return False
        
        logger.info("Migrating list_items table...")
        
        # Add new columns
        conn.execute("ALTER TABLE list_items ADD COLUMN people TEXT")
        conn.execute("ALTER TABLE list_items ADD COLUMN location TEXT")
        conn.execute("ALTER TABLE list_items ADD COLUMN latitude REAL")
        conn.execute("ALTER TABLE list_items ADD COLUMN longitude REAL")
        conn.execute("ALTER TABLE list_items ADD COLUMN place_id TEXT")
        conn.execute("ALTER TABLE list_items ADD COLUMN tags TEXT")
        conn.execute("ALTER TABLE list_items ADD COLUMN notes TEXT")
        conn.execute("ALTER TABLE list_items ADD COLUMN media_path TEXT")
        conn.execute("ALTER TABLE list_items ADD COLUMN metadata TEXT")
        
        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_item_location ON list_items(latitude, longitude)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_item_place ON list_items(place_id)")
        
        conn.commit()
        logger.info("✅ list_items migration complete")
        
        # Show updated schema
        cursor = conn.execute("PRAGMA table_info(list_items)")
        logger.info("Updated schema:")
        for row in cursor.fetchall():
            logger.info(f"  - {row[1]} ({row[2]})")
        
        return True


def migrate_tasks_db(db_path: Path) -> bool:
    """
    Add enhanced fields to tasks table.
    
    New fields:
    - people: JSON array of person names
    - location: Human-readable location string
    - latitude, longitude: GPS coordinates
    - place_id: Google Place ID
    - tags: JSON array of tags
    - media_path: Path to photo/attachment
    - reminder_distance: Meters for location-based reminders
    - metadata: JSON for additional data
    
    Returns:
        True if migration was performed, False if already migrated
    """
    if not db_path.exists():
        logger.warning(f"Database not found: {db_path}")
        return False
    
    with sqlite3.connect(db_path) as conn:
        # Check if migration already done
        cursor = conn.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "people" in columns:
            logger.info("tasks already migrated, skipping")
            return False
        
        logger.info("Migrating tasks table...")
        
        # Add new columns
        conn.execute("ALTER TABLE tasks ADD COLUMN people TEXT")
        conn.execute("ALTER TABLE tasks ADD COLUMN location TEXT")
        conn.execute("ALTER TABLE tasks ADD COLUMN latitude REAL")
        conn.execute("ALTER TABLE tasks ADD COLUMN longitude REAL")
        conn.execute("ALTER TABLE tasks ADD COLUMN place_id TEXT")
        conn.execute("ALTER TABLE tasks ADD COLUMN tags TEXT")
        conn.execute("ALTER TABLE tasks ADD COLUMN media_path TEXT")
        conn.execute("ALTER TABLE tasks ADD COLUMN reminder_distance INTEGER")
        conn.execute("ALTER TABLE tasks ADD COLUMN metadata TEXT")
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_task_location ON tasks(latitude, longitude)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_task_place ON tasks(place_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_task_people ON tasks(people)")
        
        conn.commit()
        logger.info("✅ tasks migration complete")
        
        # Show updated schema
        cursor = conn.execute("PRAGMA table_info(tasks)")
        logger.info("Updated schema:")
        for row in cursor.fetchall():
            logger.info(f"  - {row[1]} ({row[2]})")
        
        return True


def verify_migration(db_path: Path, table_name: str, expected_fields: list[str]) -> bool:
    """Verify that migration was successful."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        
        missing = set(expected_fields) - columns
        if missing:
            logger.error(f"Migration verification failed for {table_name}")
            logger.error(f"Missing fields: {missing}")
            return False
        
        logger.info(f"✅ {table_name} verification passed")
        return True


def main():
    """Run all migrations."""
    logger.info("=" * 60)
    logger.info("Starting database migration to v2.0")
    logger.info("=" * 60)
    
    settings = get_settings()
    storage_path = settings.storage_path
    
    logger.info(f"Storage path: {storage_path}")
    
    # Ensure storage directory exists
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Define database paths
    lists_db = storage_path / "lists.sqlite"
    tasks_db = storage_path / "tasks.sqlite"
    
    migrations_performed = []
    
    # Migrate lists
    if lists_db.exists():
        logger.info("\n" + "=" * 60)
        logger.info("Migrating Lists Database")
        logger.info("=" * 60)
        if migrate_lists_db(lists_db):
            migrations_performed.append("lists")
            
            # Verify
            verify_migration(lists_db, "list_items", [
                "people", "location", "latitude", "longitude", 
                "place_id", "tags", "notes", "media_path", "metadata"
            ])
    else:
        logger.info(f"Lists database not found at {lists_db}")
        logger.info("It will be created with enhanced schema on first use")
    
    # Migrate tasks
    if tasks_db.exists():
        logger.info("\n" + "=" * 60)
        logger.info("Migrating Tasks Database")
        logger.info("=" * 60)
        if migrate_tasks_db(tasks_db):
            migrations_performed.append("tasks")
            
            # Verify
            verify_migration(tasks_db, "tasks", [
                "people", "location", "latitude", "longitude", 
                "place_id", "tags", "media_path", "reminder_distance", "metadata"
            ])
    else:
        logger.info(f"Tasks database not found at {tasks_db}")
        logger.info("It will be created with enhanced schema on first use")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    
    if migrations_performed:
        logger.info(f"✅ Migrated: {', '.join(migrations_performed)}")
    else:
        logger.info("ℹ️  No migrations needed (already up to date or no databases found)")
    
    logger.info("\n✅ Migration process complete!")
    logger.info("=" * 60)
    
    return 0 if len(migrations_performed) > 0 or not (lists_db.exists() or tasks_db.exists()) else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)
