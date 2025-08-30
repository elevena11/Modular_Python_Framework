# RAH Framework Startup Flow Diagram

## Complete Startup Sequence Visualization

```
TIME   PHASE                    ACTIVITY                           CRITICAL DEPENDENCIES
====   ===================     ==================================  ======================

T+0    PRE-BOOTSTRAP           Import Core Components              None
       app.py                  ├─ core.config (settings)         
                              ├─ core.app_context (AppContext)   
                              └─ core.module_loader (ModuleLoader)

T+10   BOOTSTRAP               Create Application Foundation       Settings loaded
       app.py startup()        ├─ AppContext(settings)            
                              │  ├─ Service registry init        
                              │  ├─ Session ID generation        
                              │  └─ Logging setup               
                              └─ ModuleLoader(app_context)       

T+50   MODULE DISCOVERY        Scan Filesystem for Modules        AppContext ready
       module_loader           ├─ Scan modules/core/              
                              ├─ Scan modules/standard/           
                              ├─ Scan modules/extensions/         
                              ├─ Parse manifest.json files        
                              ├─ Check .disabled files            
                              ├─ Build dependency graph           
                              └─ Calculate load order             

T+100  PHASE 1: BOOTSTRAP      Database Infrastructure Setup       Discovery complete
       CRITICAL DATABASE       ┌─────────────────────────────────┐
                              │ core.database Phase 1 (SPECIAL) │
                              │ ├─ Create DatabaseService        │ <- NO DEPS!
                              │ ├─ Immediate DB Discovery        │ <- Scans all db_models.py
                              │ │  ├─ Find DATABASE_NAME consts  │
                              │ │  └─ Group tables by database   │  
                              │ ├─ Create ALL Databases NOW      │ <- framework.db, semantic_core.db
                              │ │  ├─ Import all schemas         │
                              │ │  ├─ Create engines & tables    │
                              │ │  └─ Set SQLite pragmas         │
                              │ ├─ Register services             │
                              │ │  ├─ core.database.service      │
                              │ │  └─ core.database.crud_service │
                              │ └─ Make Base available           │ <- app_context.db_base
                              └─────────────────────────────────┘

T+150  PHASE 1: CORE           Core Service Registration           Database ready
       SERVICE REGISTRATION    ┌─ core.settings                   
                              │  ├─ Depends: ["core.database"]    <- Needs DB for storage
                              │  ├─ Create SettingsService        
                              │  ├─ Register models with framework DB
                              │  └─ Register post-init hooks      
                              ├─ core.error_handler              
                              │  ├─ Create ErrorService           
                              │  ├─ Register models with framework DB
                              │  └─ Register post-init hooks      
                              ├─ core.global                     
                              │  ├─ Create GlobalService          
                              │  └─ Register post-init hooks      
                              └─ core.model_manager              
                                 ├─ Create ModelService          
                                 └─ Register post-init hooks      

T+300  PHASE 1: STANDARD       Application Service Registration    Core services ready
       SERVICE REGISTRATION    ├─ semantic_core                   
                              │  ├─ Import models (DBs exist!)    <- Safe now
                              │  ├─ Create SemanticService        
                              │  └─ Register post-init hooks      
                              ├─ vector_operations               
                              │  ├─ Import models                 
                              │  ├─ Create VectorService          
                              │  └─ Register post-init hooks      
                              └─ document_processing             
                                 ├─ Create DocumentService        
                                 └─ Register post-init hooks      

T+500  PHASE 2: COMPLEX        Post-Initialization Hooks          All services registered
       INITIALIZATION          ┌─ Hook Priority & Dependency Sort  
       run_delayed_hooks()     │  ├─ Sort by priority (lower first)
                              │  └─ Respect dependency chains     
                              ├─ Priority 10: core.database.setup
                              │  └─ Minimal setup (DBs exist)     
                              ├─ Priority 20: database_register_settings
                              │  ├─ Depends: ["core.settings.setup"]
                              │  └─ Register DB settings for UI   
                              ├─ Priority 50: core.settings.setup 
                              │  ├─ Load all module settings      
                              │  └─ Validate configurations       
                              ├─ Priority 100: core.error_handler.setup
                              │  ├─ Initialize error registry     
                              │  └─ Load error log files          
                              ├─ Priority 100: core.global.setup  
                              │  └─ Initialize global utilities   
                              ├─ Priority 150: core.model_manager.setup
                              │  ┌─────────────────────────────────┐
                              │  │ RESOURCE INTENSIVE (10 seconds) │
                              │  │ ├─ Detect GPU availability       │
                              │  │ ├─ Create worker pool (2 GPUs)   │
                              │  │ ├─ Load Mixedbread models        │
                              │  │ │  ├─ 1024-dimensional vectors    │
                              │  │ │  └─ Load on both GPU workers   │
                              │  │ └─ Start processing loops        │
                              │  └─────────────────────────────────┘
                              └─ Priority 200+: Standard modules  
                                 ├─ semantic_core.setup           
                                 ├─ vector_operations.setup       
                                 └─ document_processing.setup     

T+10000 APPLICATION READY      Production Services Start          All modules initialized
        uvicorn.run()          ├─ FastAPI server starts          
                              ├─ API endpoints active            
                              ├─ Health checks available         
                              ├─ Background tasks running        
                              └─ Ready for requests              

SHUTDOWN SIGNAL RECEIVED       Graceful Shutdown Sequence         Runtime complete
         shutdown()            ├─ Stop accepting requests         
                              ├─ Complete in-flight requests     
                              ├─ Run shutdown handlers           
                              ├─ Close database connections      
                              ├─ Stop background tasks           
                              └─ Final cleanup                   
```

## Critical Bootstrap Flow Analysis

### **Database Bootstrap (T+100ms)**
```
WHY DATABASE MUST BE FIRST:
┌─ Other modules need database utilities during Phase 1
├─ Models must be imported after databases exist  
├─ Session factories require database discovery
└─ No circular dependencies possible

HOW IT WORKS:
┌─ Scan ALL db_models.py files before any module loads
├─ Group tables by DATABASE_NAME constant
├─ Create all .db files and tables immediately
├─ Make utilities available via app_context.db_base
└─ Other modules can safely import during Phase 1
```

### **Settings Bootstrap (T+150ms)**
```
WHY SETTINGS NEEDS DATABASE:
┌─ Settings stored in framework database
├─ Backup functionality requires database
├─ Settings versioning tracked in database
└─ UI settings require database storage

DEPENDENCY CHAIN:
database -> settings -> (everything else can use settings)
```

### **Model Loading Timing (T+10000ms)**
```
WHY MODEL LOADING IS SLOW:
┌─ GPU memory allocation (~2 seconds)
├─ Model weight loading (~4 seconds)  
├─ Model compilation (~2 seconds)
├─ Dual GPU setup (~2 seconds)
└─ Initial inference test (~1 second)

STARTUP IMPACT:
- Everything else loads quickly (~500ms)
- Model loading dominates startup time
- Can be optimized but currently necessary
```

## Interface Improvement Strategy

Based on this flow analysis, database interface improvements should:

### **✅ SAFE TO CHANGE:**
- Session access patterns (add convenience methods)
- Import consolidation (maintain lazy loading)
- Error message clarity 
- API consistency across modules

### **⚠️ CANNOT CHANGE:**
- Database discovery timing (must be Phase 1)
- Multi-database architecture (modules need separate DBs)
- Model import lazy loading (prevents circular deps)
- Service registration order (database must be first)

### **🎯 OPTIMIZATION OPPORTUNITIES:**
- Add `app_context.db.session("db_name")` convenience method
- Unify imports to single pattern: `from core.database import Base, JSON`
- Add database interface base class for services
- Create database operation decorators
- Better startup progress indicators

The verbose patterns exist for architectural necessity, but we can add convenience layers without breaking the bootstrap sequence.