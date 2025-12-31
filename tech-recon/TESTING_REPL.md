# Testing the Persistent Python REPL Fix

This document explains how to test the fix for Issue #2: Python Variable Scope Errors.

## Quick Test

Run the automated test suite:

```bash
cd tech-recon
python test_python_repl.py
python test_repl_integration.py
```

Both tests should pass with ✅.

## What Was Fixed

**Before:** Variables defined in one `python_repl_tool` call were not available in subsequent calls, causing `NameError` exceptions.

**After:** Variables persist between calls using a persistent Python subprocess with a shared namespace.

## Manual Testing

### Test 1: Basic Variable Persistence

You can test manually using Python:

```python
from src.tools.python_repl_tool import handle_python_repl_tool

# Define a variable
result1 = handle_python_repl_tool("assessments = {'tech1': 85, 'tech2': 92}")
print(result1)

# Use it in a new call (this used to fail with NameError)
result2 = handle_python_repl_tool("print(f'Found {len(assessments)} technologies')")
print(result2)
```

### Test 2: Simulate Actual Agent Usage

This simulates the exact error pattern from the issue:

```python
from src.tools.python_repl_tool import handle_python_repl_tool

# Step 1: Coder agent defines assessments
handle_python_repl_tool("""
assessments = {
    'AI/ML': {'maturity': 8, 'impact': 9},
    'Cloud Native': {'maturity': 7, 'impact': 8}
}
""")

# Step 2: Coder agent uses assessments (this used to fail)
result = handle_python_repl_tool("""
for tech, scores in sorted(assessments.items()):
    print(f"{tech}: {scores}")
""")
print(result)  # Should work now!
```

### Test 3: Import Persistence

```python
from src.tools.python_repl_tool import handle_python_repl_tool

# Import once
handle_python_repl_tool("import json, pandas as pd")

# Use in subsequent calls
handle_python_repl_tool("data = json.dumps({'test': 123})")
handle_python_repl_tool("print(data)")
```

## Testing in the Full System

To test with the actual agents:

1. Run a Tech Recon Part 1 execution
2. Monitor the logs for `NameError` exceptions
3. Verify that agents no longer need to re-execute code blocks
4. Check that execution time is reduced

## Expected Behavior

✅ **Variables persist** between separate `python_repl_tool` calls  
✅ **Imports persist** - modules imported in one call are available in later calls  
✅ **Errors are handled** - if code fails, variables from previous calls still exist  
✅ **Process recovery** - if the subprocess dies, it automatically reinitializes  

## Verification Checklist

- [ ] Variables defined in call 1 are available in call 2
- [ ] Modifications to variables persist
- [ ] Imports work across calls
- [ ] Errors don't break the persistent session
- [ ] Multiple agents can use the tool without conflicts (thread-safe)

## Troubleshooting

If tests fail:

1. Check that the Python subprocess is starting correctly
2. Verify that the execution marker is being detected
3. Check for any threading issues
4. Review the logs for initialization errors

## Performance Impact

- **Before:** Agents had to re-execute code blocks, adding ~5-10 minutes
- **After:** Variables persist, eliminating re-execution overhead
- **Memory:** Minimal - uses a single persistent subprocess
- **Thread Safety:** Uses locks to prevent concurrent execution issues

