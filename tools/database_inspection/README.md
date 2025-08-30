# Database Inspection Tools

Standalone CLI tools for inspecting databases used by the Modular Framework without requiring the backend to be loaded.

## Tools Overview

### ChromaDB Inspection (`inspect_chromadb.py`)
**Target Module**: `standard.llm_memory_processing`, `standard.llm_memory_databases`

Inspects ChromaDB vector databases used for storing conversation chunks, summaries, and memory embeddings.

**Usage Examples**:
```bash
# Interactive mode (user-friendly exploration)
python tools/database_inspection/inspect_chromadb.py --interactive

# List all collections with statistics
python tools/database_inspection/inspect_chromadb.py --stats

# Inspect specific collection
python tools/database_inspection/inspect_chromadb.py --collection conversation_memories_raw_chunks --limit 5

# Search within a collection
python tools/database_inspection/inspect_chromadb.py --collection conversation_memories_raw_chunks --search "conversation about AI" --results 3

# JSON output for scripting
python tools/database_inspection/inspect_chromadb.py --list --json
```

**Default Database Path**: `data/llm_memory/chromadb`

### SQLite Inspection (`inspect_sqlite.py`)
**Target Modules**: `standard.llm_memory_processing`, `core.database`, `core.settings`

Inspects SQLite databases used for metadata storage, framework settings, and relational data.

**Usage Examples**:
```bash
# Interactive mode (user-friendly exploration)
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --interactive

# Database information
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --info

# List all tables
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --list

# Inspect specific table with schema
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --table memory_chunks --limit 5 --schema

# Search within a table
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --table entity_mappings --search "emotion" --limit 3

# Execute custom query
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --query "SELECT entity_type, COUNT(*) FROM entity_mappings GROUP BY entity_type"
```

**Available Databases**:
- `data/database/framework.db` - Core framework data (settings, scheduler, errors)
- `data/database/llm_memory.db` - Memory processing metadata (chunks, entities, relationships)

## Key Database Locations

### ChromaDB Collections
Located in: `data/llm_memory/chromadb/`
- `conversation_memories_raw_chunks` - Raw conversation chunks for processing
- `conversation_memories_memories` - Processed summaries and insights

### SQLite Tables
**Framework Database** (`data/database/framework.db`):
- `settings_events` - Settings change history
- `error_examples` - Error handling patterns
- `scheduler_events` - Scheduled task logs

**LLM Memory Database** (`data/database/llm_memory.db`):
- `memory_chunks` - Chunk metadata and ChromaDB references
- `entity_mappings` - Extracted entities with Neo4j references
- `relationship_mappings` - Entity relationships
- `memory_records` - Conversation processing summaries

## Module Integration

### Memory Processing Pipeline
These tools help debug and verify the `standard.llm_memory_processing` module:

1. **Chunking Stage**: Verify chunks in both ChromaDB and SQLite metadata
2. **Triplet Extraction**: Check entity extraction in SQLite and Neo4j references
3. **Summarization**: Confirm T5 summaries stored in ChromaDB with metadata
4. **Storage Stage**: Validate cross-database consistency

### Framework Core
Tools support debugging core framework modules:

- **Database Module**: Verify multi-database architecture working
- **Settings Module**: Check settings storage and change tracking
- **Error Handler**: Analyze error patterns and statistics
- **Scheduler**: Monitor background task execution

## Development Workflow

### Verify Pipeline Health
```bash
# Check if memory processing is storing data
python tools/database_inspection/inspect_chromadb.py --stats
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --list

# Verify data consistency (chunk counts should match)
python tools/database_inspection/inspect_chromadb.py --collection conversation_memories_raw_chunks | grep "Count:"
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --table memory_chunks | grep "Total Rows:"
```

### Debug Pipeline Issues
```bash
# Check for processing errors in entity extraction
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --table entity_mappings --search "error"

# Verify summary generation is working
python tools/database_inspection/inspect_chromadb.py --collection conversation_memories_memories --limit 1

# Check framework error patterns
python tools/database_inspection/inspect_sqlite.py --db-path data/database/framework.db --table error_examples --limit 5
```

### Validate New Features
```bash
# After implementing new pipeline stage, verify data storage
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --query "SELECT processing_status, COUNT(*) FROM memory_chunks GROUP BY processing_status"

# Check recent activity
python tools/database_inspection/inspect_sqlite.py --db-path data/database/llm_memory.db --query "SELECT * FROM memory_chunks WHERE created_at > datetime('now', '-1 hour')"
```

## Interactive Mode Features

Both tools now include an **interactive mode** (`--interactive` or `-i`) that provides:

### ChromaDB Interactive Mode
- **Collection Browser**: Navigate collections with numbered menus
- **Document Explorer**: Browse documents with pagination (n/p/f for next/previous/full content)
- **Search Interface**: Interactive semantic search with result ranking
- **Export Function**: Save sample data to JSON files
- **Content Toggle**: Switch between preview and full content display

### SQLite Interactive Mode  
- **Table Browser**: Navigate tables with numbered menus
- **Data Browser**: Browse table data with pagination and page jumping
- **Search Interface**: Search across text columns interactively
- **Schema Viewer**: View detailed table schemas with indexes
- **Query Console**: Execute custom SQL queries with guided examples
- **Export Function**: Export table data to JSON files

### Navigation
- **Arrow Keys/Numbers**: Navigate menus and options
- **Ctrl+C**: Exit gracefully at any time
- **0**: Go back to previous menu level
- **Pagination**: n/p for next/previous, j for jump to page

## Notes

- **No Framework Dependencies**: These tools connect directly to database files
- **Read-Only Operations**: Tools only inspect data, never modify
- **Standalone Execution**: Can run even when main application is down
- **Cross-Platform**: Work on any system with Python and database libraries
- **JSON Output**: Support scripting and automation with `--json` flag
- **Interactive + CLI**: Keep command-line arguments for automation, add interactive mode for human exploration

## Related Documentation

- **Memory Processing**: `docs/llm_memory_processing/`
- **Database Architecture**: `docs/database/multi-database-implementation-final.md`
- **Framework Core**: `docs/core-framework-guide.md`