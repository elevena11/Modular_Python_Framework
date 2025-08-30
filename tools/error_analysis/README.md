# Error Analysis Tools

This directory contains tools for analyzing error patterns from the Modular Framework's error tracking system to identify potential compliance standards and system improvements.

## Overview

The Modular Framework automatically tracks all errors in the `error_codes` database table, including error frequency, affected modules, and occurrence timestamps. These tools leverage this data to provide insights for:

- **Data-driven compliance standard development**
- **System health monitoring**
- **Error pattern identification**
- **Proactive quality improvements**

## Tools

### `error_analysis.py` - Core Analysis Engine

**Purpose**: Comprehensive error pattern analysis and compliance standard generation

**Key Features**:
- Error frequency analysis by module and category
- Automatic compliance standard generation based on error patterns
- Pattern categorization (validation, connection, database, etc.)
- Export capabilities for further analysis

**Usage Examples**:
```bash
# Get error summary for last 7 days
python tools/error_analysis/error_analysis.py --summary --days 7

# Full pattern analysis
python tools/error_analysis/error_analysis.py --analyze --days 7

# Generate compliance standard for specific error pattern
python tools/error_analysis/error_analysis.py --generate-standard "UNKNOWN_TYPE"

# Show all analyses
python tools/error_analysis/error_analysis.py --all --days 30
```

**Output**: 
- Formatted console reports
- JSON files saved to `tools/compliance/drafts/`

---

### `error_query.py` - Interactive Query Tool

**Purpose**: Quick exploration and filtering of error data

**Key Features**:
- Filter errors by pattern, module, or timeframe
- Cross-module error pattern detection
- Module-specific error analysis
- Real-time data querying

**Usage Examples**:
```bash
# Query specific error patterns
python tools/error_analysis/error_query.py --pattern "SERVICE_INIT_FAILED" --days 7

# Show errors for specific module
python tools/error_analysis/error_query.py --module "veritas_knowledge_graph" --days 7

# Show modules with most errors
python tools/error_analysis/error_query.py --modules --days 7

# Show cross-module patterns
python tools/error_analysis/error_query.py --patterns --days 7

# Recent errors (default)
python tools/error_analysis/error_query.py --days 1 --limit 10
```

**Use Cases**:
- Debugging specific modules
- Investigating recurring patterns
- Quick health checks
- Targeted error investigation

---

### `compliance_insights.py` - Strategic Intelligence

**Purpose**: High-level compliance strategy and prioritization

**Key Features**:
- Prioritized compliance opportunities
- Impact assessment (error frequency × affected modules)
- Trending analysis and recommendations
- Weekly compliance reports

**Usage Examples**:
```bash
# Generate compliance opportunities report
python tools/error_analysis/compliance_insights.py --days 7

# Generate weekly executive report
python tools/error_analysis/compliance_insights.py --report

# Save insights to file
python tools/error_analysis/compliance_insights.py --report --save weekly_report.json
```

**Output Format**:
- High/medium/low priority opportunities
- Impact metrics (error reduction potential)
- Strategic recommendations
- Trending analysis

## Integration with Compliance System

These tools integrate seamlessly with the compliance validation system:

1. **Error Analysis** → Identifies recurring patterns
2. **Standard Generation** → Creates draft compliance standards 
3. **Implementation** → Manual refinement of generated standards
4. **Validation** → Compliance tool validates adherence
5. **Monitoring** → Error analysis tracks improvement

### Example Workflow

```bash
# 1. Weekly health check
python tools/error_analysis/compliance_insights.py --report

# 2. Investigate top issue
python tools/error_analysis/error_query.py --pattern "SERVICE_INIT_FAILED"

# 3. Generate compliance standard
python tools/error_analysis/error_analysis.py --generate-standard "SERVICE_INIT_FAILED"

# 4. Refine and implement standard (manual step)
# Edit generated draft in tools/compliance/drafts/

# 5. Validate compliance
python tools/compliance/compliance.py --validate-all

# 6. Monitor improvement over time
python tools/error_analysis/error_query.py --pattern "SERVICE_INIT_FAILED" --days 30
```

## Error Categories

The tools automatically categorize errors into these patterns:

| Category | Pattern | Examples |
|----------|---------|----------|
| **Validation** | `validation`, `unknown_type` | Type validation, schema errors |
| **Connection** | `connection`, `timeout` | Database connections, network issues |
| **Database** | `database`, `db` | SQL errors, migration issues |
| **Import** | `import`, `module` | Module loading, dependency issues |
| **Configuration** | `config`, `setting` | Settings validation, missing config |
| **API** | `api`, `schema` | API validation, request failures |
| **Other** | Miscellaneous | Service initialization, business logic |

## Requirements

- Access to Modular Framework database (`data/database/modular_ai.db`)
- Python 3.8+ with framework dependencies
- Error tracking module must be initialized

## Database Schema

The tools query the `error_codes` table with this structure:

```sql
CREATE TABLE error_codes (
    id INTEGER PRIMARY KEY,
    module_id TEXT NOT NULL,        -- Module that generated the error
    code TEXT NOT NULL,             -- Full error code
    first_seen DATETIME NOT NULL,   -- First occurrence
    last_seen DATETIME NOT NULL,    -- Most recent occurrence  
    count INTEGER DEFAULT 0,       -- Total occurrences
    locations TEXT                  -- JSON array of code locations
);
```

## Output Files

Generated files are organized as follows:

```
tools/
├── compliance/
│   └── drafts/                    # Generated compliance standards
│       ├── error_prevention_unknown_type.json
│       └── error_prevention_service_init_failed.json
└── error_analysis/
    ├── README.md                  # This file
    ├── error_analysis.py          # Core analysis tool
    ├── error_query.py             # Interactive queries
    └── compliance_insights.py     # Strategic insights
```

## Success Metrics

Track the effectiveness of error-driven compliance development:

1. **Error Reduction**: Monitor decrease in error frequency after standard implementation
2. **Pattern Prevention**: Fewer new modules exhibiting known error patterns  
3. **Cross-Module Consistency**: Reduced variation in error handling approaches
4. **Development Velocity**: Faster resolution of recurring issues

## Example Success Story

**Type Validation Standard Implementation**:
- **Before**: 2,581 `UNKNOWN_TYPE` errors from incorrect schema type names
- **Analysis**: Tools identified this as #2 priority compliance opportunity
- **Action**: Implemented automated type validation in compliance system
- **Result**: Zero type validation errors in subsequent application runs
- **Impact**: Prevented 2,581+ future error occurrences

This demonstrates the power of data-driven compliance development.

## Best Practices

### Regular Monitoring
- Run weekly compliance insights reports
- Monitor error trends after each deployment
- Track error reduction following standard implementation

### Standard Development
- Start with highest-impact error patterns (frequency × modules affected)
- Use generated drafts as starting points, not final implementations
- Validate that standards actually prevent the targeted errors

### Continuous Improvement
- Regularly review and update error categorization
- Refine standard generation logic based on implementation experience
- Share insights across development team for proactive error prevention

---

*These tools are part of the Modular Framework's commitment to data-driven quality improvement and AI-agent-ready development patterns.*