#!/usr/bin/env python3
"""
Pre-push validation script.
Checks code integrity before pushing to repository.
"""

import sys
import ast
import importlib.util
from pathlib import Path
from typing import List, Tuple

def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """Check Python syntax of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error: {e.msg} at line {e.lineno}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_imports(file_path: Path) -> Tuple[bool, str]:
    """Check if file can be imported (basic check)."""
    try:
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if spec and spec.loader:
            # Don't actually import to avoid side effects, just check syntax
            return True, ""
        return False, "Could not create module spec"
    except Exception as e:
        return False, f"Import check failed: {str(e)}"

def check_critical_methods() -> Tuple[bool, str]:
    """Check that critical methods exist in key files."""
    errors = []
    
    # Check engine.py for critical methods (now in modules/conservative/execution/engine.py)
    engine_path = Path("modules/conservative/execution/engine.py")
    if not engine_path.exists():
        # Fallback to old location for backward compatibility
        engine_path = Path("core/engine.py")
    
    if engine_path.exists():
        with open(engine_path, 'r', encoding='utf-8') as f:
            engine_code = f.read()
        
        required_methods = [
            '_get_constraints',
            '_get_action_space',
            '_execute_buy',
            '_execute_sell',
            '_check_exit_conditions'
        ]
        
        for method in required_methods:
            if f"def {method}" not in engine_code:
                errors.append(f"Missing method: {method} in {engine_path}")
    
    # Check grok.py for critical methods
    grok_path = Path("providers/grok.py")
    if grok_path.exists():
        with open(grok_path, 'r', encoding='utf-8') as f:
            grok_code = f.read()
        
        if "def analyze" not in grok_code:
            errors.append("Missing method: analyze in providers/grok.py")
        if "def _parse_response" not in grok_code:
            errors.append("Missing method: _parse_response in providers/grok.py")
    
    if errors:
        return False, "\n".join(errors)
    return True, ""

def check_none_safety() -> Tuple[bool, str]:
    """Check for common None safety issues."""
    errors = []
    
    # Check grok.py for .lower() calls without None checks
    grok_path = Path("providers/grok.py")
    if grok_path.exists():
        with open(grok_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            # Look for .lower() calls that might not handle None
            if '.lower()' in line and 'if' not in lines[max(0, i-3):i]:
                # Check if there's a None check nearby
                context = ''.join(lines[max(0, i-5):i])
                if 'is None' not in context and 'if' not in context and 'get(' in context:
                    # This is a potential issue, but be lenient
                    # Only flag if it's clearly unsafe
                    if 'market_data.get(' in line or 'data.get(' in line:
                        if 'or ""' not in line and 'if' not in lines[max(0, i-2):i]:
                            errors.append(f"Potential None safety issue in providers/grok.py line {i}: {line.strip()}")
    
    if errors:
        return False, "\n".join(errors[:5])  # Limit to first 5 errors
    return True, ""

def main():
    """Run all pre-push checks."""
    print("🔍 Running pre-push validation...")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # Critical files to check
    critical_files = [
        Path("modules/conservative/execution/engine.py"),  # New location
        Path("core/engine.py"),  # Old location (for backward compatibility)
        Path("providers/grok.py"),
        Path("main.py"),
        Path("services/analytics.py"),
        Path("storage/state_manager.py"),
    ]
    
    # Check syntax
    print("\n📝 Checking syntax...")
    for file_path in critical_files:
        if file_path.exists():
            is_valid, error = check_syntax(file_path)
            if not is_valid:
                errors.append(f"{file_path}: {error}")
                print(f"  ❌ {file_path}: {error}")
            else:
                print(f"  ✅ {file_path}: syntax OK")
        else:
            warnings.append(f"{file_path}: file not found")
            print(f"  ⚠️  {file_path}: file not found")
    
    # Check critical methods
    print("\n🔧 Checking critical methods...")
    is_valid, error = check_critical_methods()
    if not is_valid:
        errors.append(f"Critical methods: {error}")
        print(f"  ❌ {error}")
    else:
        print("  ✅ All critical methods present")
    
    # Check None safety (warnings only)
    print("\n🛡️  Checking None safety...")
    is_valid, error = check_none_safety()
    if not is_valid:
        warnings.append(f"None safety: {error}")
        print(f"  ⚠️  Potential issues:\n{error}")
    else:
        print("  ✅ None safety checks passed")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print("❌ VALIDATION FAILED")
        print(f"\nFound {len(errors)} critical error(s):")
        for error in errors:
            print(f"  • {error}")
        print("\n⚠️  DO NOT PUSH until errors are fixed!")
        return 1
    elif warnings:
        print("⚠️  VALIDATION PASSED WITH WARNINGS")
        print(f"\nFound {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  • {warning}")
        print("\n✅ Safe to push, but review warnings")
        return 0
    else:
        print("✅ VALIDATION PASSED")
        print("\nAll checks passed. Safe to push!")
        return 0

if __name__ == "__main__":
    sys.exit(main())


