# Core Authentication Module

**Status: PLANNED - Not Implemented Yet**

This module will provide production-ready authentication and authorization for the Modular Python Framework, enabling secure deployment beyond localhost development.

## Purpose

The `core.auth` module will transform the framework from a development-only tool into a production-ready platform by providing:

- **User Management** - Registration, authentication, and user profiles
- **Role-Based Access Control** - Admin, user, and custom roles with granular permissions  
- **API Security** - JWT tokens, API keys, and request authentication
- **UI Security** - Login screens, session management, and permission-based UI components
- **Production Deployment** - Secure server/client architecture for networked access

## Critical Need

**Without this module, the framework is limited to:**
- ❌ Localhost development only
- ❌ Personal hobby projects  
- ❌ Single-user applications

**With this module, the framework enables:**
- ✅ Production business applications
- ✅ Multi-user systems
- ✅ Remote deployment and access
- ✅ Client-server architectures
- ✅ Enterprise-ready security

## Planned Architecture

### Module Structure
```
modules/core/auth/
├── api.py              # Authentication endpoints (/login, /register, /users)
├── services.py         # AuthService - user management and authentication logic
├── settings.py         # Authentication configuration (JWT secrets, timeouts)
├── database.py         # User/role database operations with Result pattern
├── db_models.py        # User, Role, Session, Permission SQLAlchemy models
├── middleware.py       # FastAPI authentication middleware for all requests
├── decorators.py       # @require_auth, @require_role protection decorators
├── ui.py              # Admin UI for user management in Streamlit
└── schemas.py          # Login, registration, user management API schemas
```

### Core Features

#### 1. User Management System
```python
# User registration and authentication
@register_service("core.auth.service")
class AuthService:
    async def register_user(self, username: str, password: str, email: str, role: str = "user") -> Result
    async def authenticate_user(self, username: str, password: str) -> Result
    async def get_user_permissions(self, user_id: int) -> Result
    async def update_user_role(self, user_id: int, role: str) -> Result
```

#### 2. Authentication Decorators
```python
# Protect API endpoints
@require_auth
@router.get("/protected-data")
async def get_protected_data():
    return {"data": "sensitive information"}

@require_role("admin")
@router.delete("/admin/users/{user_id}")  
async def delete_user(user_id: int):
    # Admin-only operation
```

#### 3. UI Integration
```python
# Streamlit UI with authentication
def render_main_tab(ui_context):
    current_user = ui_context.get_current_user()
    
    if not current_user:
        st.error("Please log in to access this feature")
        return
        
    if current_user.has_permission("admin"):
        # Show admin features
        render_admin_panel()
    
    # Show user features
    render_user_content()
```

#### 4. Role-Based Access Control
- **Admin Role**: Full system access, user management, system configuration
- **User Role**: Standard application access, personal data management
- **Custom Roles**: Module-specific permissions, fine-grained access control
- **Guest Role**: Limited read-only access (optional)

### Integration with Existing Framework

#### Database Integration
- Uses framework's `integrity_session()` pattern for all database operations
- Automatic user database creation and management
- Integration with existing multi-database architecture

#### Settings Integration  
```python
class AuthSettings(BaseModel):
    jwt_secret: str = Field(description="JWT token signing secret")
    session_timeout_minutes: int = Field(default=60, description="Session timeout")
    require_email_verification: bool = Field(default=False)
    password_min_length: int = Field(default=8)
    max_failed_logins: int = Field(default=5)
    lockout_duration_minutes: int = Field(default=15)
```

#### API Integration
- Middleware automatically protects all API endpoints
- Authentication headers handled transparently
- Existing module APIs work unchanged with added security

#### UI Integration
- Login/logout components available to all module UIs
- User context available in all UI rendering functions
- Permission-based component visibility

### Security Features

#### Authentication Methods
- **JWT Tokens** - Stateless API authentication with configurable expiration
- **Session Cookies** - Streamlit UI authentication with secure session management
- **API Keys** - Programmatic access for automated systems
- **Optional OAuth** - Integration with external authentication providers

#### Security Measures  
- Password hashing with bcrypt
- JWT token signing and validation
- Session management and timeout
- Rate limiting for login attempts
- Account lockout after failed attempts
- Audit logging of authentication events

#### Network Security
- HTTPS/TLS requirement for production
- Secure cookie configuration
- CSRF protection for UI forms
- Request origin validation

## Implementation Phases

### Phase 1: Core Authentication
- User model and database operations
- Password hashing and validation
- JWT token generation and validation
- Basic login/logout API endpoints

### Phase 2: Authorization System
- Role and permission models
- Role-based access decorators
- API endpoint protection middleware
- Permission checking utilities

### Phase 3: UI Integration
- Streamlit login/logout components
- User management admin interface
- Session management for UI
- Permission-based UI rendering

### Phase 4: Advanced Features
- OAuth integration options
- Audit logging and monitoring
- Advanced security policies
- Multi-factor authentication support

## Configuration Options

### Development Mode
```bash
# .env - Development (auth disabled)
AUTH_ENABLED=false
HOST=127.0.0.1
```

### Production Mode
```bash
# .env - Production (auth required)
AUTH_ENABLED=true
HOST=127.0.0.1  # Still localhost - use reverse proxy for external access
JWT_SECRET=your-secure-secret-key
SESSION_TIMEOUT_MINUTES=60
REQUIRE_EMAIL_VERIFICATION=true
```

## Migration Strategy

### Backward Compatibility
- **Existing applications continue to work unchanged** in development mode
- Auth module is optional - can be enabled/disabled via configuration
- No breaking changes to existing module patterns or APIs

### Deployment Options
- **Development**: Auth disabled, localhost access only (current behavior)
- **Testing**: Auth enabled, test users and roles configured
- **Production**: Full authentication required, admin-managed users

## Benefits for Framework Adoption

### For Developers
- **Rapid prototyping** - Start without auth, add it when ready for production
- **Production-ready security** - Enterprise-grade authentication built-in
- **Flexible deployment** - Single codebase works for dev and production
- **Standard patterns** - Uses familiar framework decorators and Result pattern

### For Applications  
- **Multi-user support** - Built-in user management and role separation
- **Secure deployment** - Ready for network access with proper authentication
- **Compliance readiness** - Audit trails and access controls for regulatory requirements
- **Scalable architecture** - Server/client separation enables distributed deployments

### For Enterprise Use
- **Security by design** - Authentication integrated into framework core
- **Role-based access** - Granular permissions for different user types
- **Audit capabilities** - Track user actions and system access
- **Integration ready** - OAuth and external auth provider support

## Next Steps

1. **Design database schema** for users, roles, and permissions
2. **Implement core authentication service** with Result pattern
3. **Create API endpoints** for user management
4. **Build authentication middleware** for FastAPI integration
5. **Develop Streamlit UI components** for login and user management
6. **Create documentation and examples** for module integration
7. **Test with existing modules** to ensure seamless integration

This module will be the key enabler for transforming the Modular Python Framework from a development tool into a production-ready application platform.