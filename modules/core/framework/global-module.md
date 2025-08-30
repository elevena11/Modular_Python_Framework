Creating a real `modules/core/global` module to handle framework-wide concerns would be much cleaner than the current virtual approach.

This official module could:

1. **Handle Global Settings**:
   - Move global settings from special case code to a proper module
   - Apply the same patterns we use for regular modules

2. **Own Cross-Cutting Standards**:
   - ASCII-only Console Output standard
   - Naming conventions
   - File structure standards
   - Documentation format standards
   - Other framework-wide concerns

3. **Provide Framework-Wide Utilities**:
   - Common utilities that don't fit in other modules
   - Base classes for framework patterns

For the specific case of ASCII-only Console Output, I think it makes more sense in the `core.global` module than in `core.errors` since it's a broader coding standard rather than strictly error-related.

The standards would be organized like:
- `core.settings` -> Settings API standard
- `core.errors` -> Error Handling standard
- `core.database` -> Database standards
- `core.global` -> ASCII-only Console Output, File Structure, Naming Conventions, etc.

Creating this module would give us a consistent place to put framework-wide concerns and eliminate the need for special cases in the code, which aligns perfectly with your modular architecture philosophy.