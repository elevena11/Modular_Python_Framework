# Framework Documentation

This directory contains all documentation for the Modular Python Framework.

## Organization

### `docs/core/` - Core Framework Documentation
Official framework documentation maintained by the core team:

- **[Architecture](core/architecture.md)** - Framework architecture and design principles
- **[Module Development Guide](core/module-development-guide.md)** - Complete guide to creating modules
- **[Decorators](core/decorators.md)** - Decorator patterns and service registration
- **[Error Handling](core/error-handling.md)** - Result pattern and structured error logging
- **[Database](core/database.md)** - Database architecture and integration patterns
- **[Settings](core/settings.md)** - Pydantic settings system and configuration
- **[Core Components](core/core-components.md)** - Framework core components overview
- **[Development Tools](core/development-tools.md)** - Scaffolding and development utilities

### `docs/` - Project Documentation
User and project-specific documentation:

- **[Framework Updates](core/framework-updates.md)** - Release notes and version history
- **[Streamlit UI](core/streamlit-ui.md)** - UI components and interfaces

## Quick Start

If you're new to the framework, start with:

1. **[Architecture](core/architecture.md)** - Understand the framework design
2. **[Module Development Guide](core/module-development-guide.md)** - Learn to create modules
3. **[Decorators](core/decorators.md)** - Master the decorator patterns

## Development Workflow

For framework development:

1. **[Development Tools](core/development-tools.md)** - Use scaffolding tools
2. **[Error Handling](core/error-handling.md)** - Implement proper error patterns
3. **[Database](core/database.md)** - Integrate with the database system

## Contributing Documentation

- **Core framework docs** (`docs/core/`): Maintained by core team, requires review
- **Project docs** (`docs/`): Add your own project-specific documentation here
- **Module docs**: Each module can include its own README in its directory

## Documentation Standards

- Use **Markdown** format
- Include **code examples** for all patterns
- Add **"Quick Reference"** sections for complex topics
- Keep examples **up-to-date** with current framework patterns
- Use **consistent terminology** throughout

---

## Semantic Documentation Search

Search documentation using semantic similarity instead of keyword matching.

### Quick Start

**Build search index** (one-time setup):
```bash
python tools/rebuild_index.py
```

**Daemon mode** (recommended - 111x faster):
```bash
python tools/search_docs.py --daemon                    # Start in background, returns to shell
python tools/search_docs.py "how to use model_manager"  # Fast search (~87ms)
python tools/search_docs.py "database session" --top 10
python tools/search_docs.py --status                    # Check daemon status
python tools/search_docs.py --stop                      # Stop daemon

# Watch daemon activity (optional)
tail -f docs/.doc_index/daemon_*.log

# Run in foreground with terminal output (for debugging)
python tools/search_docs.py --daemon --tail
```

**Direct mode** (loads model each time - ~9.7s):
```bash
python tools/search_docs.py "query" --direct
python tools/search_docs.py "pydantic settings" --preview --direct
```

### How It Works

- **Semantic understanding**: Finds conceptually similar content, not just keyword matches
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (lightweight, fast)
- **Storage**: ChromaDB index in `docs/.doc_index/` (gitignored, user-generated)

### Benefits

Query: "register model" finds:
- "model registration"
- "how to add models"
- "ModelRequirement schema"
- Related examples and patterns

Traditional keyword search would miss most of these!

### Commands

**rebuild_index.py** - Build/rebuild the search index
```bash
python tools/rebuild_index.py
```

**search_docs.py** - Search documentation semantically
```bash
# Daemon commands
python tools/search_docs.py --daemon     # Start daemon
python tools/search_docs.py --status     # Check daemon status
python tools/search_docs.py --stop       # Stop daemon

# Search commands
python tools/search_docs.py [QUERY] [OPTIONS]

Options:
  --daemon         Start daemon mode (keeps model loaded)
  --stop           Stop daemon
  --status         Check daemon status
  --direct         Use direct mode (bypass daemon)
  --top N, -t N    Number of results (default: 5)
  --preview, -p    Show content preview
```

### Requirements

- `sentence-transformers` - Embedding model (~80MB download)
- `chromadb` - Vector database

Already included in framework requirements.

### Performance

- **Daemon mode**: ~87ms per search (111x faster)
- **Direct mode**: ~9.7s per search (loads model each time)
- **Model size**: 80MB in VRAM when daemon running

### Tips

- **Use daemon mode**: Start daemon once, get instant searches
- **Multiple codebases**: Each codebase can run its own daemon simultaneously (unique socket per path)
- **Rebuild after changes**: Run `rebuild_index.py` after updating docs
- **Broader queries**: Try general terms if specific queries don't match

---

**Framework Version**: 1.0.3
**Documentation Last Updated**: September 2025