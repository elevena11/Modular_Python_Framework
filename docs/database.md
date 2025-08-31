# Database System

The framework provides a multi-database architecture where each module can have its own isolated SQLite database with automatic lifecycle management.

## Core Concepts

### Multi-Database Architecture
- **Each module gets its own database** - Clean separation of data
- **Cross-database access allowed** - Modules can access other databases when needed
- **Automatic discovery** - Framework finds and initializes databases
- **Session management** - Built-in transaction and lifecycle handling
- **Zero configuration** - Database creation and management handled automatically

**Important:** While modules can access any database, doing so creates a dependency relationship. Consider the architectural implications before accessing another module's database.

### Database Naming
Databases are automatically named based on your module:
- Module `standard.user_manager` → Database `user_manager.db`
- Module `core.settings` → Database `settings.db` 
- Module `standard.inventory_system` → Database `inventory_system.db`

## The integrity_session Pattern

All database operations use the `integrity_session` pattern for automatic session lifecycle management:

```python
async with app_context.database.integrity_session("database_name", "operation_purpose") as session:
    # Your database operations here
    result = await session.execute(query)
    await session.commit()  # Automatic rollback on exceptions
```

**Parameters:**
- `database_name` (str): Name of the database (usually your module name)
- `purpose` (str): Description of the operation (for logging and debugging)

**Benefits:**
- **Automatic rollback** on exceptions
- **Session cleanup** guaranteed
- **Transaction management** handled automatically
- **Connection pooling** built-in
- **Debugging support** with operation logging

## Setting Up Your Module Database

### 1. Define Database Models

```python
# modules/standard/user_manager/db_models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from core.database import get_database_base

# Define database name for discovery
DATABASE_NAME = "user_manager"

# Get base class for this database
UserManagerBase = get_database_base(DATABASE_NAME)

class User(UserManagerBase):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

class UserSession(UserManagerBase):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
```

**Important:**
- **DATABASE_NAME constant** - Required for framework discovery
- **Use get_database_base()** - Creates proper base class for your database
- **Standard SQLAlchemy models** - No framework-specific model requirements

### 2. Initialize Tables in Your Module

```python
# modules/standard/user_manager/api.py
async def initialize_service(self):
    """Phase 2: Set up database tables."""
    await self.create_database_tables()

async def create_database_tables(self):
    """Create tables for this module."""
    from .db_models import UserManagerBase
    
    async with self.app_context.database.integrity_session("user_manager", "create_tables") as session:
        # Create all tables for this database
        await session.run_sync(UserManagerBase.metadata.create_all)
        
        # Add initial data if needed
        await self.create_initial_data(session)

async def create_initial_data(self, session):
    """Add any initial data your module needs."""
    from .db_models import User
    
    # Check if admin user exists
    admin_exists = await session.execute(
        select(User).where(User.email == "admin@example.com")
    )
    
    if not admin_exists.first():
        admin_user = User(
            name="Administrator",
            email="admin@example.com", 
            created_at=datetime.utcnow()
        )
        session.add(admin_user)
```

## Database Operations in Services

### Basic CRUD Operations

```python
# modules/standard/user_manager/services.py
from core.error_utils import Result
from sqlalchemy import select
from .db_models import User

class UserManagerService:
    def __init__(self, app_context):
        self.app_context = app_context
    
    async def create_user(self, name: str, email: str) -> Result:
        """Create a new user."""
        try:
            async with self.app_context.database.integrity_session("user_manager", "create_user") as session:
                # Check if user exists
                existing = await session.execute(
                    select(User).where(User.email == email)
                )
                
                if existing.first():
                    return Result.error("USER_EXISTS", "User with this email already exists")
                
                # Create new user
                user = User(
                    name=name,
                    email=email,
                    created_at=datetime.utcnow()
                )
                
                session.add(user)
                await session.commit()  # Explicit commit for data creation
                
                return Result.success(data={
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                })
                
        except Exception as e:
            return Result.error("DATABASE_ERROR", f"Failed to create user: {str(e)}")
    
    async def get_user(self, user_id: int) -> Result:
        """Get user by ID."""
        try:
            async with self.app_context.database.integrity_session("user_manager", "get_user") as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                
                user = result.scalar_one_or_none()
                
                if not user:
                    return Result.error("USER_NOT_FOUND", f"User {user_id} not found")
                
                return Result.success(data={
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "is_active": user.is_active
                })
                
        except Exception as e:
            return Result.error("DATABASE_ERROR", f"Failed to get user: {str(e)}")
    
    async def update_user(self, user_id: int, name: str = None, email: str = None) -> Result:
        """Update user information."""
        try:
            async with self.app_context.database.integrity_session("user_manager", "update_user") as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                
                user = result.scalar_one_or_none()
                
                if not user:
                    return Result.error("USER_NOT_FOUND", f"User {user_id} not found")
                
                # Update fields if provided
                if name is not None:
                    user.name = name
                if email is not None:
                    user.email = email
                
                await session.commit()
                
                return Result.success(data={
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                })
                
        except Exception as e:
            return Result.error("DATABASE_ERROR", f"Failed to update user: {str(e)}")
    
    async def list_users(self, active_only: bool = True) -> Result:
        """List all users."""
        try:
            async with self.app_context.database.integrity_session("user_manager", "list_users") as session:
                query = select(User)
                
                if active_only:
                    query = query.where(User.is_active == True)
                
                result = await session.execute(query)
                users = result.scalars().all()
                
                return Result.success(data=[{
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "is_active": user.is_active
                } for user in users])
                
        except Exception as e:
            return Result.error("DATABASE_ERROR", f"Failed to list users: {str(e)}")
```

### Complex Queries and Joins

```python
async def get_user_with_sessions(self, user_id: int) -> Result:
    """Get user with their active sessions."""
    try:
        async with self.app_context.database.integrity_session("user_manager", "user_with_sessions") as session:
            # Complex query with join
            result = await session.execute(
                select(User, UserSession)
                .join(UserSession, User.id == UserSession.user_id)
                .where(User.id == user_id)
                .where(UserSession.expires_at > datetime.utcnow())
            )
            
            user_sessions = result.all()
            
            if not user_sessions:
                return Result.error("USER_NOT_FOUND", f"User {user_id} not found or no active sessions")
            
            # Process results
            user = user_sessions[0].User
            sessions = [row.UserSession for row in user_sessions]
            
            return Result.success(data={
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                },
                "active_sessions": [{
                    "token": session.token,
                    "expires_at": session.expires_at.isoformat()
                } for session in sessions]
            })
            
    except Exception as e:
        return Result.error("DATABASE_ERROR", f"Failed to get user sessions: {str(e)}")
```

## Database Configuration

### Default Settings
The framework provides sensible defaults:
- **SQLite databases** stored in `data/database/`
- **Connection pooling** with automatic cleanup
- **Async operations** using SQLAlchemy async
- **UTF-8 encoding** for international support
- **WAL mode** for better concurrent access

### Custom Database Settings (Advanced)

```python
# In your module's settings.py
from pydantic import BaseModel, Field

class UserManagerSettings(BaseModel):
    database_timeout: int = Field(default=30, description="Database operation timeout in seconds")
    max_connections: int = Field(default=10, description="Maximum database connections")
    enable_foreign_keys: bool = Field(default=True, description="Enable SQLite foreign key constraints")

# Access in your service
async def get_database_settings(self):
    settings_service = self.app_context.get_service("core.settings.service") 
    return await settings_service.get_typed_settings("user_manager", UserManagerSettings)
```

## Migration Patterns

### Schema Updates
When you need to change your database schema:

```python
async def migrate_database_v2(self):
    """Migrate database to version 2."""
    async with self.app_context.database.integrity_session("user_manager", "migrate_v2") as session:
        # Check current schema version
        try:
            await session.execute("SELECT migration_version FROM schema_info")
        except:
            # First migration - create schema_info table
            await session.execute("""
                CREATE TABLE schema_info (
                    migration_version INTEGER PRIMARY KEY
                )
            """)
            await session.execute("INSERT INTO schema_info (migration_version) VALUES (1)")
        
        # Get current version
        result = await session.execute("SELECT migration_version FROM schema_info")
        current_version = result.scalar()
        
        if current_version < 2:
            # Apply migration
            await session.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
            await session.execute("UPDATE schema_info SET migration_version = 2")
            await session.commit()
```

### Data Migrations

```python
async def migrate_user_data(self):
    """Migrate user data to new format."""
    async with self.app_context.database.integrity_session("user_manager", "migrate_data") as session:
        # Get all users that need migration
        result = await session.execute(
            select(User).where(User.email.like("%@old-domain.com"))
        )
        
        users_to_update = result.scalars().all()
        
        for user in users_to_update:
            # Update email domain
            user.email = user.email.replace("@old-domain.com", "@new-domain.com")
        
        await session.commit()
        
        return f"Migrated {len(users_to_update)} user emails"

## Cross-Database Access

While each module typically uses its own database, modules can access other databases when necessary.

### Accessing Another Module's Database

```python
async def get_user_with_orders(self, user_id: int) -> Result:
    """Get user data from user_manager and orders from order_system."""
    try:
        user_data = None
        orders_data = []
        
        # Access user_manager database
        async with self.app_context.database.integrity_session("user_manager", "get_user") as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return Result.error("USER_NOT_FOUND", f"User {user_id} not found")
            
            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        
        # Access order_system database (different module's database)
        async with self.app_context.database.integrity_session("order_system", "get_orders") as session:
            from modules.standard.order_system.db_models import Order
            
            result = await session.execute(
                select(Order).where(Order.user_id == user_id)
            )
            orders = result.scalars().all()
            
            orders_data = [{
                "id": order.id,
                "total": order.total,
                "status": order.status
            } for order in orders]
        
        return Result.success(data={
            "user": user_data,
            "orders": orders_data
        })
        
    except Exception as e:
        return Result.error("DATABASE_ERROR", f"Failed to get user with orders: {str(e)}")
```

### Architectural Considerations

When accessing another module's database, consider:

**Dependency Management:**
- Your module now depends on the other module's database schema
- Changes to the other module's models may break your code
- Module loading order becomes important

**Alternative Approaches:**
```python
# Instead of direct database access, consider using the other module's service
async def get_user_with_orders_via_service(self, user_id: int) -> Result:
    """Use service interface instead of direct database access."""
    try:
        # Get user via user_manager service
        user_service = self.app_context.get_service("user_manager.service")
        user_result = await user_service.get_user(user_id)
        
        if not user_result.success:
            return user_result
        
        # Get orders via order_system service  
        order_service = self.app_context.get_service("order_system.service")
        orders_result = await order_service.get_user_orders(user_id)
        
        if not orders_result.success:
            return orders_result
        
        return Result.success(data={
            "user": user_result.data,
            "orders": orders_result.data
        })
        
    except Exception as e:
        return Result.error("SERVICE_ERROR", f"Failed to get user with orders: {str(e)}")
```

**Best Practices:**
- **Prefer service interfaces** over direct database access when possible
- **Document dependencies** in your module documentation
- **Use stable APIs** - Access well-defined data structures, not internal models
- **Handle missing dependencies** - Check if other modules/databases exist

**When Cross-Database Access Makes Sense:**
- **Reporting modules** that aggregate data from multiple sources
- **Migration scripts** that need to move data between modules
- **Analytics modules** that compute metrics across multiple domains
- **Search modules** that index content from various sources

**When to Avoid It:**
- **Core business logic** should use service interfaces
- **Frequent operations** - API calls are more maintainable
- **Unstable schemas** - Direct database access is fragile

### Module Packages with Shared Databases

A powerful pattern is creating **module packages** - related modules that share a database and work as a cohesive unit.

**Example: E-commerce Package**
```
modules/standard/ecommerce_core/     # Database owner
├── db_models.py                     # All shared models
├── api.py                          # Core data management
└── services.py                     # Shared business logic

modules/standard/ecommerce_orders/   # Uses ecommerce_core database
├── api.py                          # Order-specific endpoints
└── services.py                     # Order operations

modules/standard/ecommerce_payments/ # Uses ecommerce_core database  
├── api.py                          # Payment endpoints
└── services.py                     # Payment processing
```

**Shared Database Models:**
```python
# modules/standard/ecommerce_core/db_models.py
DATABASE_NAME = "ecommerce"  # One database for entire package

EcommerceBase = get_database_base(DATABASE_NAME)

class Customer(EcommerceBase):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

class Product(EcommerceBase):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Decimal(10, 2), nullable=False)

class Order(EcommerceBase):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    total = Column(Decimal(10, 2), nullable=False)

class Payment(EcommerceBase):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    amount = Column(Decimal(10, 2), nullable=False)
```

**Using Shared Database in Each Module:**
```python
# modules/standard/ecommerce_orders/services.py
async def create_order(self, customer_id: int, items: list) -> Result:
    """Create order using shared ecommerce database."""
    try:
        async with self.app_context.database.integrity_session("ecommerce", "create_order") as session:
            from modules.standard.ecommerce_core.db_models import Customer, Product, Order
            
            # Verify customer exists
            customer = await session.execute(
                select(Customer).where(Customer.id == customer_id)
            )
            if not customer.scalar_one_or_none():
                return Result.error("CUSTOMER_NOT_FOUND", "Customer does not exist")
            
            # Create order
            order = Order(customer_id=customer_id, total=0)
            session.add(order)
            await session.flush()  # Get order ID
            
            # Add order items and calculate total
            total = 0
            for item in items:
                product = await session.execute(
                    select(Product).where(Product.id == item["product_id"])
                )
                product = product.scalar_one_or_none()
                if product:
                    total += product.price * item["quantity"]
            
            order.total = total
            await session.commit()
            
            return Result.success(data={"order_id": order.id, "total": float(total)})
            
    except Exception as e:
        return Result.error("ORDER_CREATION_FAILED", str(e))
```

**Benefits of Module Packages:**
- **Shared data model** - Consistent schema across related functionality
- **Transaction safety** - Operations can span multiple related entities
- **Performance** - No cross-service calls for related data
- **Data integrity** - Foreign key constraints work within the package
- **Simpler deployment** - Package modules deploy together

**Package Organization Guidelines:**
- **One "core" module** - Owns the database and defines all models
- **Feature modules** - Implement specific functionality using shared models
- **Clear boundaries** - Package should represent a business domain
- **Documentation** - Document which modules share the database
```

## Best Practices

### Session Management
- **Always use integrity_session** - Never create sessions manually
- **One session per operation** - Don't reuse sessions across different operations  
- **Descriptive purpose strings** - Helps with debugging and logging
- **Handle exceptions** - Return Result objects with meaningful errors

### Query Patterns
- **Use SQLAlchemy select()** - Modern syntax, better type hints
- **Avoid raw SQL when possible** - Use ORM for type safety
- **Index important columns** - Add indexes for frequently queried columns
- **Batch operations** - Process multiple records in single transactions

### Model Design
- **Clear table names** - Use descriptive __tablename__ values
- **Appropriate data types** - Choose correct SQLAlchemy column types
- **Proper relationships** - Use ForeignKey constraints
- **Include timestamps** - created_at, updated_at fields

### Error Handling
- **Return Result objects** - Consistent error patterns
- **Log database errors** - Include context for debugging
- **Handle constraint violations** - Provide user-friendly messages
- **Transaction rollback** - Let integrity_session handle rollbacks

## Troubleshooting

### Database Not Found
```
Error: Database 'my_module' not found
```

**Cause:** Missing DATABASE_NAME constant in db_models.py
**Solution:** Add `DATABASE_NAME = "my_module"` to your db_models.py file

### Table Not Found
```
Error: no such table: users
```

**Cause:** Tables not created during module initialization
**Solution:** Call `create_database_tables()` in your `initialize_service()` method

### Session Errors
```
Error: Session is not bound to a connection
```

**Cause:** Trying to use session outside of integrity_session context
**Solution:** Ensure all database operations are inside `async with integrity_session():`

### Permission Denied
```
Error: database is locked
```

**Cause:** Multiple processes accessing SQLite database
**Solution:** Ensure only one process accesses each database, or use WAL mode (enabled by default)

The database system handles all the complexity of multi-database management while providing a simple, consistent interface for your modules.