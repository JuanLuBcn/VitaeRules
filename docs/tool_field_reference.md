# Tool Field Reference

Comprehensive documentation of all available fields for each tool, indicating which are mandatory and optional.

---

## 📋 ListTool

### Operations
- `create_list`
- `delete_list`
- `add_item`
- `remove_item`
- `complete_item`
- `list_items`
- `get_lists`

### Fields

| Field | Type | Mandatory For | Optional For | Description |
|-------|------|---------------|--------------|-------------|
| `operation` | string | **ALL** | - | Operation to perform (see Operations above) |
| `list_name` | string | `create_list`, `add_item` | `delete_list`, `list_items` | Name of the list |
| `list_id` | string | - | `delete_list`, `add_item`, `list_items` | ID of the list (alternative to list_name) |
| `item_text` | string | `add_item` | - | Text content of the item to add |
| `item_id` | string | `remove_item`, `complete_item` | - | ID of the specific item |
| `user_id` | string | - | **ALL** | User identifier for filtering |
| `chat_id` | string | - | **ALL** | Chat identifier for filtering |

### Operation-Specific Requirements

#### `create_list`
- **Required**: `operation`, `list_name`
- **Optional**: `user_id`, `chat_id`
- **Returns**: `list_id`, `list_name`, `created_at`

#### `delete_list`
- **Required**: `operation`, (`list_name` OR `list_id`)
- **Optional**: `user_id`, `chat_id`
- **Returns**: `list_id`, `list_name`, `deleted`

#### `add_item`
- **Required**: `operation`, `list_name`, `item_text`
- **Optional**: `user_id`, `chat_id`, `list_id`
- **Returns**: `item_id`, `item_text`, `list_id`, `position`
- **Note**: Auto-creates list if it doesn't exist

#### `remove_item`
- **Required**: `operation`, `item_id`
- **Returns**: `item_id`, `item_text`, `removed`

#### `complete_item`
- **Required**: `operation`, `item_id`
- **Returns**: `item_id`, `item_text`, `completed`

#### `list_items`
- **Required**: `operation`, (`list_name` OR `list_id`)
- **Returns**: `list_id`, `list_name`, `items[]`, `count`

#### `get_lists`
- **Required**: `operation`
- **Optional**: `user_id`, `chat_id`
- **Returns**: `lists[]`, `count`

---

## ✅ TaskTool

### Operations
- `create_task`
- `complete_task`
- `list_tasks`
- `update_task`
- `delete_task`

### Fields

| Field | Type | Mandatory For | Optional For | Description |
|-------|------|---------------|--------------|-------------|
| `operation` | string | **ALL** | - | Operation to perform |
| `task_id` | string | `complete_task`, `update_task`, `delete_task` | - | ID of the task |
| `title` | string | `create_task` | `update_task` | Task title/description |
| `description` | string | - | `create_task`, `update_task` | Detailed task description |
| `due_at` | string (ISO) | - | `create_task`, `update_task` | Due date/time in ISO format |
| `priority` | integer (0-3) | - | `create_task`, `update_task` | Priority: 0=low, 1=medium, 2=high, 3=urgent |
| `completed` | boolean | - | `list_tasks` | Filter by completion status |
| `user_id` | string | - | **ALL** | User identifier |
| `chat_id` | string | - | **ALL** | Chat identifier |

### Operation-Specific Requirements

#### `create_task`
- **Required**: `operation`, `title`
- **Optional**: `description`, `due_at`, `priority`, `user_id`, `chat_id`
- **Default**: `priority=0` (low)
- **Returns**: `task_id`, `title`, `description`, `due_at`, `priority`, `created_at`

#### `complete_task`
- **Required**: `operation`, `task_id`
- **Returns**: `task_id`, `title`, `completed_at`

#### `list_tasks`
- **Required**: `operation`
- **Optional**: `user_id`, `chat_id`, `completed` (filter)
- **Returns**: `tasks[]`, `count`

#### `update_task`
- **Required**: `operation`, `task_id`
- **Optional**: `title`, `description`, `due_at`, `priority`
- **Returns**: `task_id`, updated fields, `updated_at`

#### `delete_task`
- **Required**: `operation`, `task_id`
- **Returns**: `task_id`, `title`, `deleted`

---

## 💾 MemoryItem (for NoteAgent)

### Core Fields

| Field | Type | Mandatory | Default | Description |
|-------|------|-----------|---------|-------------|
| `id` | UUID | No | auto-generated | Unique identifier |
| `source` | MemorySource | **Yes** | - | Where this memory came from (CAPTURE, DIARY, IMPORT, SYSTEM) |
| `title` | string | **Yes** | - | Short title/summary |
| `content` | string | **Yes** | - | Full content/description |
| `section` | MemorySection | No | NOTE | Memory category (EVENT, NOTE, DIARY, TASK, LIST, etc.) |
| `created_at` | datetime | No | auto-generated | Creation timestamp |
| `updated_at` | datetime | No | auto-generated | Last update timestamp |

### Optional Fields

#### Classification & Tags
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tags` | list[string] | `[]` | User-defined tags |
| `status` | MemoryStatus | ACTIVE | Item status (ACTIVE, ARCHIVED, DELETED) |

#### People & Social
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `people` | list[string] | `[]` | People mentioned (@name) |
| `attendees` | list[string] | `[]` | Event attendees |

#### Temporal
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `event_start_at` | datetime | `null` | Event start time |
| `event_end_at` | datetime | `null` | Event end time |
| `timezone` | string | `null` | Timezone for temporal fields |
| `date_bucket` | string | `null` | Date bucket for retrieval (YYYY-MM-DD) |
| `due_at` | datetime | `null` | Due date for tasks |
| `completed_at` | datetime | `null` | Completion timestamp |

#### Location
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `location` | string | `null` | Location/place name |
| `coordinates` | tuple(float, float) | `null` | (latitude, longitude) |

#### Media & Attachments
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `media_type` | string | `null` | MIME type of media |
| `media_path` | string | `null` | Path to media file |
| `attachments` | list[string] | `[]` | Attachment file paths |

#### External References
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `external_id` | string | `null` | External system ID (Google Calendar, etc.) |
| `external_url` | string | `null` | External URL reference |

#### Task/List Specific
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `list_name` | string | `null` | List this item belongs to |

#### User Context
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `chat_id` | string | `null` | Chat/conversation ID |
| `user_id` | string | `null` | User ID who created this |

#### Metadata
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `metadata` | dict | `{}` | Additional metadata as key-value pairs |

---

## 🎯 Quick Reference by Agent

### ListAgent → ListTool
Most common operations:
```python
# Add item (auto-creates list if needed)
{
    "operation": "add_item",
    "list_name": "lista de la compra",
    "item_text": "leche",
    "user_id": "user123",
    "chat_id": "chat456"
}

# Query list
{
    "operation": "list_items",
    "list_name": "lista de la compra"
}

# Get all lists
{
    "operation": "get_lists",
    "user_id": "user123",
    "chat_id": "chat456"
}
```

### TaskAgent → TaskTool
Most common operations:
```python
# Create task
{
    "operation": "create_task",
    "title": "Llamar a Juan",
    "due_at": "2025-10-27T10:00:00Z",
    "priority": 1,
    "user_id": "user123",
    "chat_id": "chat456"
}

# List tasks
{
    "operation": "list_tasks",
    "user_id": "user123",
    "chat_id": "chat456",
    "completed": false  # only pending tasks
}

# Complete task
{
    "operation": "complete_task",
    "task_id": "task-uuid-here"
}
```

### NoteAgent → MemoryService
Most common pattern:
```python
from app.memory import MemoryItem, MemorySource, MemorySection

memory_item = MemoryItem(
    source=MemorySource.CAPTURE,
    section=MemorySection.NOTE,
    title="Nota sobre Juan",
    content="A Juan le gusta el café",
    people=["Juan"],
    tags=["preferencia"],
    chat_id="chat456",
    user_id="user123",
    metadata={"agent": "note_agent"}
)

memory_service.save_memory(memory_item)
```

---

## 📊 Field Priority Levels

### Critical (Always Required)
- `operation` - For all tools
- `title` - For TaskTool.create_task and MemoryItem
- `content` - For MemoryItem
- `source` - For MemoryItem
- `list_name` - For ListTool.create_list, add_item
- `item_text` - For ListTool.add_item
- `item_id` - For ListTool.remove_item, complete_item
- `task_id` - For TaskTool operations except create

### Important (Recommended)
- `user_id` - For filtering and context
- `chat_id` - For filtering and context
- `priority` - For tasks (defaults to 0)
- `section` - For MemoryItem (defaults to NOTE)

### Nice to Have (Enhanced Features)
- `description` - For tasks
- `due_at` - For tasks and events
- `tags` - For memories
- `people` - For memories
- `location` - For events
- `event_start_at`, `event_end_at` - For events

### Advanced (Future Features)
- `coordinates` - For location-based features
- `media_type`, `media_path`, `attachments` - For multimedia
- `external_id`, `external_url` - For integrations
- `timezone` - For multi-timezone support
- `metadata` - For custom extensions

---

## 🔄 Field Evolution Roadmap

### Current Implementation (v1.0)
- ✅ Basic list operations
- ✅ Basic task operations  
- ✅ Basic note storage
- ✅ User/chat context

### Planned Enhancements (v1.1)
- ⏳ Task priority display and sorting
- ⏳ Task due date reminders
- ⏳ List item completion tracking
- ⏳ People mention detection and linking

### Future Features (v2.0)
- 📅 Calendar integration (event_start_at, event_end_at)
- 📍 Location tracking (coordinates, location)
- 🎨 Media attachments (media_type, media_path)
- 🔗 External integrations (external_id, external_url)
- 🌍 Timezone support
- 🏷️ Advanced tag management
