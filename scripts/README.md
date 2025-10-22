# Utility Scripts

Collection of utility scripts for managing VitaeBot data and testing.

## 🧹 Memory Management

### `purge_memory.py`
Interactive memory cleanup with confirmations.
```bash
python scripts/purge_memory.py
```

### `quick_purge.py`
Fast cleanup without confirmations (for testing).
```bash
python scripts/quick_purge.py
```

### `check_memory.py`
Check memory status without making changes.
```bash
python scripts/check_memory.py
```

## 📖 Documentation

See [Memory Cleanup Guide](../docs/memory_cleanup_guide.md) for detailed information.

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Check status | `python scripts/check_memory.py` |
| Safe cleanup | `python scripts/purge_memory.py` |
| Quick cleanup | `python scripts/quick_purge.py` |
| Full workflow | `python scripts/check_memory.py && python scripts/quick_purge.py && python scripts/check_memory.py` |
