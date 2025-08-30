# 6. Reference & Examples

This section provides concrete, LLM-friendly examples for common extension and integration tasks in the RAH Modular Framework. Use these as templates for your own modules or as a knowledge base for LLM-driven code generation.

## 6.1 Example: Minimal Extension Module

**Directory Structure:**
```
modules/extensions/minimal_module/
├── manifest.json
├── api.py
└── services.py
```

**manifest.json:**
```json
{
  "name": "minimal_module",
  "version": "1.0.0",
  "dependencies": []
}
```

**api.py:**
```python
from fastapi import APIRouter
from core.app_context import app_context
from .services import MinimalService

router = APIRouter()

@router.get("/hello")
async def hello():
    return {"message": "Hello from minimal module!"}

# Register service
app_context.register_service('minimal_service', MinimalService())
```

**services.py:**
```python
class MinimalService:
    def greet(self):
        return "Hello!"
```

---

## 6.2 Example: Custom Database Integration

**db_models.py:**
```python
from sqlalchemy import Column, Integer, String
from core.database import get_database_base

DATABASE_NAME = "custom_db_module"
ModuleBase = get_database_base(DATABASE_NAME)

class CustomRecord(ModuleBase):
    __tablename__ = "custom_records"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

**database.py:**
```python
from sqlalchemy.orm import Session
from .db_models import CustomRecord

def add_record(session: Session, name: str):
    record = CustomRecord(name=name)
    session.add(record)
    session.commit()
    return record
```

---

## 6.3 Example: Advanced Error Handling

**services.py:**
```python
from core.error_handler import Result, Error

def risky_operation():
    try:
        # Some operation that may fail
        ...
        return Result.success(data="All good!")
    except Exception as e:
        return Result.failure(Error(code="RISKY_FAIL", message=str(e)))
```

---

## 6.4 Example: LLM Task Orchestration

**services.py:**
```python
from core.scheduler import register_task

async def llm_task():
    # LLM-driven background job
    ...

register_task('llm_task', llm_task, schedule='@daily')
```

---

> Use these examples as starting points for your own modules or as templates for LLM-driven code generation and reasoning.

Continue to [7. Best Practices & Gotchas](07-best-practices.md)
