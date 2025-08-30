# STANDARD.API_SCHEMA_VALIDATION [ID:STD-API-001]
VERSION: 1.0.1
UPDATED: 2025-03-20
OWNER: core.framework

# HUMAN: This document defines the API Schema Validation standard in AI-optimized format with maximum information density.

## STANDARD_DEFINITION [ID:STD-API-DEF-001]
NAME: API Schema Validation
PURPOSE: Ensure consistent API request and response validation using Pydantic V2 models
SCOPE: All API endpoints in the system

## TECHNICAL_REQUIREMENTS [ID:STD-API-REQ-001]
REQUIREMENT.PYDANTIC_V2_SYNTAX: Use Pydantic V2 compatible syntax (populate_by_name, json_schema_extra)
REQUIREMENT.SCHEMA_FILE_SEPARATION: API schemas must be defined in api_schemas.py, separate from database models in db_models.py
REQUIREMENT.VALIDATION_ENFORCEMENT: API endpoints must use Pydantic models for request/response validation
REQUIREMENT.APPROPRIATE_TYPES: Schemas must use appropriate field types and constraints
REQUIREMENT.FIELD_DOCUMENTATION: Schemas must include descriptive field docstrings
REQUIREMENT.NAMING_CONVENTION: Schemas must follow consistent naming conventions
REQUIREMENT.EXPLICIT_RESPONSE_MODELS: Response models must be explicitly defined in API endpoints
REQUIREMENT.AVOID_ATTRIBUTE_SHADOWING: Avoid field names that shadow BaseModel attributes

## FILE_ORGANIZATION [ID:STD-API-ORG-001]
STRUCTURE:
```
modules/your_module/
  ├── api.py              # API endpoints using schemas
  ├── db_models.py        # Database models (SQLAlchemy)
  ├── api_schemas.py      # API schemas (Pydantic)
  └── service.py          # Business logic
```

## SCHEMA_CONVENTIONS [ID:STD-API-CONV-001]
CONVENTION.BASE_CLASS: Schema classes should extend Pydantic's BaseModel
CONVENTION.NAMING_PATTERN: Schema names should be descriptive and follow PascalCase
CONVENTION.REQUEST_SUFFIX: Request models should end with `Request` (e.g., `CreateUserRequest`)
CONVENTION.RESPONSE_SUFFIX: Response models should end with `Response` (e.g., `UserResponse`)
CONVENTION.GENERAL_MODEL: General data models can use a descriptive name without a suffix

## TYPE_ANNOTATIONS [ID:STD-API-TYPE-001]
ANNOTATION.LISTS: Use `List[Type]` for arrays (e.g., `List[str]`)
ANNOTATION.DICTIONARIES: Use `Dict[KeyType, ValueType]` for objects with keys (e.g., `Dict[str, int]`)
ANNOTATION.OPTIONAL: Use `Optional[Type]` for nullable fields (e.g., `Optional[str]`)
ANNOTATION.UNION: Use `Union[Type1, Type2]` for fields that can be multiple types
ANNOTATION.ANY: Use `Any` only when absolutely necessary

## VALIDATION_PATTERNS [ID:STD-API-VAL-001]
PATTERN.API_SCHEMAS_FILE: Module must include api_schemas.py file
TARGET: All modules
REGEX: .*

PATTERN.PYDANTIC_IMPORTS: API files must import Pydantic classes
TARGET: api_schemas.py, api.py
REGEX: from\\s+pydantic\\s+import\\s+(?:BaseModel|Field|validator|root_validator)

PATTERN.SCHEMA_CLASSES: API schemas must extend BaseModel
TARGET: api_schemas.py
REGEX: class\\s+[A-Z][a-zA-Z0-9]*(?:Request|Response|Schema|Model|Config)\\s*\\(\\s*BaseModel\\s*\\)

PATTERN.RESPONSE_MODEL_USAGE: Endpoints must specify response_model
TARGET: api.py
REGEX: response_model\\s*=\\s*[A-Z][a-zA-Z0-9]*(?:Request|Response|Schema|Model|Config)

PATTERN.FIELD_TYPE_ANNOTATIONS: Fields must have type annotations
TARGET: api_schemas.py
REGEX: \\w+\\s*:\\s*(?:\\w+|List\\[\\w+\\]|Dict\\[\\w+,\\s*\\w+\\]|Optional\\[\\w+\\]|Union\\[)

## ANTI_PATTERNS [ID:STD-API-ANTI-001]

ANTI_PATTERN.PYDANTIC_V1_CONFIG_SYNTAX [ID:STD-API-ANTI-001-01]
PATTERN: class\\s+Config.*?allow_population_by_field_name\\s*=
TARGET: api_schemas.py
MESSAGE: Pydantic V1 syntax 'allow_population_by_field_name' detected, use 'populate_by_name' instead for V2 compatibility

ANTI_PATTERN.PYDANTIC_V1_SCHEMA_EXTRA [ID:STD-API-ANTI-001-02]
PATTERN: class\\s+Config.*?schema_extra\\s*=
TARGET: api_schemas.py
MESSAGE: Pydantic V1 syntax 'schema_extra' detected, use 'json_schema_extra' instead for V2 compatibility

ANTI_PATTERN.SCHEMA_FIELD_CONFLICT [ID:STD-API-ANTI-001-03]
PATTERN: schema\\s*:\\s*(?:Optional\\[)?Dict\\[
TARGET: api_schemas.py
MESSAGE: Field name 'schema' conflicts with Pydantic BaseModel attribute, use an alternative name like 'schema_definition'

ANTI_PATTERN.EXTRA_FIELD_V1 [ID:STD-API-ANTI-001-04]
PATTERN: extra\\s*=\\s*['\"](?:allow|ignore|forbid)['\"]
TARGET: api_schemas.py
MESSAGE: Pydantic V1 'extra' field syntax, use 'model_config' dictionary with 'extra' key instead

## IMPLEMENTATION_EXAMPLES [ID:STD-API-IMPL-001]

EXAMPLE.DATABASE_MODEL [ID:STD-API-IMPL-001-01]
FILE: db_models.py
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from modules.core.database.models import Base

class User(Base):
    """Database model for user data."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
```

EXAMPLE.API_SCHEMA [ID:STD-API-IMPL-001-02]
FILE: api_schemas.py
```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

class UserResponse(BaseModel):
    """Response model for user data."""
    id: int = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john@example.com",
                "is_active": True,
                "created_at": "2025-01-01T12:00:00Z"
            }
        }
    }
```

EXAMPLE.SCHEMA_WITH_VALIDATION [ID:STD-API-IMPL-001-03]
FILE: api_schemas.py
```python
from typing import List, Optional
from pydantic import BaseModel, Field, validator

class CreateItemRequest(BaseModel):
    """Request model for creating a new item."""
    name: str = Field(..., 
                    description="Item name", 
                    min_length=3, 
                    max_length=50)
    description: Optional[str] = Field(None, 
                                    description="Item description",
                                    max_length=500)
    price: float = Field(..., 
                       description="Item price",
                       gt=0)
    tags: List[str] = Field(default_factory=list, 
                          description="Item tags")
    
    @validator('price')
    def price_must_be_reasonable(cls, v):
        """Validate that the price is reasonable."""
        if v > 1000000:
            raise ValueError('price seems unreasonably high')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "New Item",
                "description": "This is a new item",
                "price": 19.99,
                "tags": ["new", "featured"]
            }
        }
    }
```

EXAMPLE.API_ENDPOINT [ID:STD-API-IMPL-001-04]
FILE: api.py
```python
from fastapi import APIRouter, Path, HTTPException
from typing import List

from .api_schemas import ItemResponse, CreateItemRequest
from .service import item_service

router = APIRouter(prefix="/items", tags=["Items"])

@router.post("/", response_model=ItemResponse, status_code=201)
async def create_item(item_data: CreateItemRequest):
    """
    Create a new item.
    
    This endpoint accepts item information and creates a new item record.
    """
    try:
        # Create item using service layer
        new_item = await item_service.create_item(item_data)
        
        # Convert to response model
        return ItemResponse(
            id=new_item.id,
            name=new_item.name,
            description=new_item.description,
            price=new_item.price,
            tags=new_item.tags
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Failed to create item",
                "details": {"error": str(e)}
            }
        )
```

## COMMON_ISSUES [ID:STD-API-ISS-001]

ISSUE.USING_DATABASE_MODELS_DIRECTLY [ID:STD-API-ISS-001-01]
DESCRIPTION: Exposing database models directly in API responses
INCORRECT:
```python
# Incorrect: Using database model directly
from .db_models import User

@router.get("/users/{user_id}", response_model=User)  # User is a database model
async def get_user(user_id: int):
    return db.get_user(user_id)
```
CORRECT:
```python
# Correct: Using API schema
from .api_schemas import UserResponse

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    db_user = await db.get_user(user_id)
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        is_active=db_user.is_active,
        created_at=db_user.created_at
    )
```

ISSUE.MISSING_TYPE_ANNOTATIONS [ID:STD-API-ISS-001-02]
DESCRIPTION: Schema fields without explicit type annotations
INCORRECT:
```python
class UserModel(BaseModel):
    id = Field(..., description="User ID")  # Missing type annotation
    name = Field(..., description="Name")   # Missing type annotation
```
CORRECT:
```python
class UserModel(BaseModel):
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="Name")
```

ISSUE.INCONSISTENT_SCHEMA_NAMING [ID:STD-API-ISS-001-03]
DESCRIPTION: Schemas with inconsistent naming patterns
INCORRECT:
```python
class Create_User(BaseModel):  # Inconsistent naming (snake_case)
    # ...

class userResponse(BaseModel):  # Inconsistent naming (camelCase)
    # ...
```
CORRECT:
```python
class CreateUserRequest(BaseModel):  # PascalCase with Request suffix
    # ...

class UserResponse(BaseModel):  # PascalCase with Response suffix
    # ...
```

ISSUE.MISSING_RESPONSE_MODEL [ID:STD-API-ISS-001-04]
DESCRIPTION: Endpoint without explicit response model
INCORRECT:
```python
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    # No response_model parameter
    user = await user_service.get_user(user_id)
    return user
```
CORRECT:
```python
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    user = await user_service.get_user(user_id)
    return user
```

ISSUE.MIXING_CONCERNS [ID:STD-API-ISS-001-05]
DESCRIPTION: Mixing database-specific and API-specific concerns in one model
INCORRECT:
```python
class User(BaseModel):
    id: int
    username: str
    email: str
    password_hash: str  # Security issue: exposing sensitive data
    # Also missing descriptions, validation, etc.
```
CORRECT:
```python
# db_models.py (Database model)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(String)

# api_schemas.py (API schema)
class UserResponse(BaseModel):
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    # No password_hash field
```

## PYDANTIC_V2_MIGRATION [ID:STD-API-MIG-001]

CHANGE.CONFIG_ATTRIBUTE_RENAME [ID:STD-API-MIG-001-01]
OLD: allow_population_by_field_name
NEW: populate_by_name
EXPLANATION: Configuration attribute renamed in Pydantic V2

CHANGE.SCHEMA_EXTRA_RENAME [ID:STD-API-MIG-001-02]
OLD: schema_extra
NEW: json_schema_extra
EXPLANATION: Configuration attribute renamed in Pydantic V2

CHANGE.CONFIG_STYLE [ID:STD-API-MIG-001-03]
OLD:
```python
class Config:
    schema_extra = {...}
```
NEW:
```python
model_config = {
    "json_schema_extra": {...}
}
```
EXPLANATION: Can use 'class Config' or top-level 'model_config' dictionary

## META_INFORMATION
DOCUMENT.ID: STD-API-001
DOCUMENT.VERSION: 1.0.1
DOCUMENT.DATE: 2025-03-20
DOCUMENT.AUDIENCE: [AI developers, Human developers, API developers]
DOCUMENT.STATUS: Active
DOCUMENT.PURPOSE: Define standard for API schema validation using Pydantic V2

# HUMAN: This document focuses specifically on the technical requirements and examples needed to shape code correctly, omitting more verbose explanations while retaining essential implementation patterns.
