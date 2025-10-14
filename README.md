# VitaeRules

CrewAI-first personal assistant with memory, task management, and natural language interactions via Telegram.

## Features

- 🤖 **Multi-Agent Architecture**: Powered by CrewAI with specialized agents for capture, retrieval, and task management
- 🧠 **Smart Memory**: Short-term (conversation) and long-term (vector + SQL) memory for context-aware responses
- 🎙️ **Voice Support**: Spanish speech-to-text for voice messages
- ✅ **Task Management**: Dynamic lists, tasks, and reminders with natural language input
- 🔍 **Intelligent Retrieval**: Answer questions from your memory with source citations
- 🌐 **Bilingual**: Spanish primary with English support
- 🔒 **Approval Flow**: Human-in-the-loop for side-effecting operations

## Architecture

### Crews

- **Capture Crew**: Orchestrator → Planner → Clarifier → ToolCaller
  - Processes incoming messages (text/voice)
  - Plans actions, clarifies ambiguity, executes with approval

- **Retrieval Crew**: QueryPlanner → Retriever → Composer
  - Answers questions from long-term memory
  - Provides citations via `/sources` command

- **Tasks & Lists Crew**: TaskExtractor → ConfidenceGate → Scheduler
  - Manages tasks, lists, and reminders

### Memory

- **Short-term Memory (STM)**: Conversation context per chat/session
- **Long-term Memory (LTM)**: Vector embeddings (Chroma) + SQL metadata
- **Zero-evidence policy**: Only answer from verified memory items

## Setup

### Prerequisites

- Python 3.11 or higher
- [Ollama](https://ollama.ai/) (for local LLM) or OpenRouter API key
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- FFmpeg (for voice transcription, optional)

### Installation

1. **Clone the repository**:
```powershell
git clone https://github.com/JuanLuBcn/VitaeRules.git
cd VitaeRules
```

2. **Create virtual environment**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. **Install dependencies**:
```powershell
pip install -U pip
pip install poetry
poetry install
```

4. **Configure environment**:
```powershell
# Copy example environment file
Copy-Item .env.example .env

# Edit .env and set your values:
# - TELEGRAM_BOT_TOKEN (required)
# - OLLAMA_MODEL or OPENROUTER_API_KEY (required)
```

5. **Install Ollama (if using local LLM)**:
```powershell
# Download from https://ollama.ai/
# Pull a model:
ollama pull llama3.2:3b
```

### Running

Start the application:
```powershell
poetry run vitaerules
```

Or using Python directly:
```powershell
python -m app.main
```

## Configuration

All configuration is done via environment variables (see `.env.example`):

### Essential Settings

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `LLM_BACKEND`: `ollama` or `openrouter`
- `OLLAMA_MODEL`: Model name (e.g., `llama3.2:3b`)
- `OPENROUTER_API_KEY`: API key for OpenRouter (if using cloud models)

### Memory & Storage

- `VECTOR_STORE_PATH`: Path to Chroma vector store (default: `data/chroma`)
- `SQL_DB_PATH`: Path to SQLite database (default: `data/app.sqlite`)

### Application Behavior

- `APPROVAL_TIMEOUT_MINUTES`: How long to wait for user approval (default: 10)
- `MAX_CLARIFY_QUESTIONS`: Max clarification questions per interaction (default: 3)
- `RETRIEVAL_TOP_K`: Number of memory items to retrieve (default: 4)
- `DEFAULT_TIMEZONE`: Timezone for temporal operations (default: `Europe/Madrid`)

### Feature Flags

- `ENABLE_VOICE`: Enable voice message transcription (default: `true`)
- `ENABLE_DIARY`: Enable daily diary synthesis (default: `false`)

## Development

### Running Tests

```powershell
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/unit/test_config.py
```

### Code Quality

```powershell
# Format code
poetry run black src tests

# Lint
poetry run ruff check src tests

# Fix linting issues
poetry run ruff check --fix src tests
```

### Pre-commit Hooks

```powershell
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## Project Structure

```
VitaeRules/
├── src/app/                    # Main application code
│   ├── config.py              # Configuration loader
│   ├── tracing.py             # Structured logging/tracing
│   ├── main.py                # Entry point
│   ├── memory/                # Memory abstraction (STM + LTM)
│   ├── contracts/             # Pydantic schemas
│   ├── tools/                 # Tool registry and implementations
│   ├── crews/                 # CrewAI crews and agents
│   │   ├── capture/           # Capture crew
│   │   ├── retrieval/         # Retrieval crew
│   │   └── tasks/             # Tasks & Lists crew
│   ├── adapters/              # External interfaces
│   │   └── telegram.py        # Telegram bot
│   └── utils/                 # Utilities
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── golden/                # Golden test fixtures
├── docs/                      # Documentation
├── scripts/                   # Development scripts
├── data/                      # Runtime data (gitignored)
│   ├── chroma/               # Vector store
│   ├── app.sqlite            # SQL database
│   └── trace.jsonl           # Trace logs
├── pyproject.toml            # Project metadata & dependencies
└── .env                      # Environment variables (gitignored)
```

## Usage Examples

### Capture Notes

```
User: "Reunión con María mañana a las 10am sobre el proyecto"
Bot: ✅ ¿Confirmas?
     📝 Nota: Reunión con María
     📅 10:00 - Mañana
User: "Sí"
Bot: ✅ Guardado
```

### Voice Messages

Simply send a voice message in Spanish - it will be transcribed and processed automatically.

### Create Tasks

```
User: "Añade 'comprar leche' a mi lista de compras"
Bot: ✅ ¿Confirmas?
     ➕ Añadir "comprar leche" a lista "compras"
User: "Sí"
Bot: ✅ Añadido
```

### Ask Questions

```
User: "¿Qué hice el martes pasado?"
Bot: El martes pasado tuviste una reunión con María sobre el proyecto a las 10am.
     [/sources] Ver fuentes
```

## Roadmap

### Phase 1 ✅ (Current)
- [x] Project scaffold
- [x] Configuration & tracing
- [ ] Memory foundation (STM + LTM)
- [ ] Tool registry

### Phase 2
- [ ] Capture Crew (MVP)
- [ ] Retrieval Crew
- [ ] Telegram adapter

### Phase 3
- [ ] Tasks & Lists management
- [ ] Voice transcription
- [ ] Approval flow with timeouts

### Phase 4 (Future)
- [ ] Diary synthesis
- [ ] Google Calendar/Tasks integration
- [ ] LinkedIn news posting
- [ ] Multi-language support (English)

## Contributing

This is a personal project, but suggestions and feedback are welcome! Please open an issue to discuss any changes.

## License

[To be determined]

## Acknowledgments

- Built with [CrewAI](https://www.crewai.com/)
- Vector storage by [Chroma](https://www.trychroma.com/)
- Speech-to-text by [faster-whisper](https://github.com/guillaumekln/faster-whisper)
