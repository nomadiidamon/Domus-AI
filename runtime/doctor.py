# Checks for all needed dependencies: Python, Ollama, Claude, Git, Models, MCP validation, and more. If any dependencies are missing, it will prompt the user to install them.

import subprocess
import sys
import os
import logging
from typing import Dict, List, Tuple
import json

logger = logging.getLogger(__name__)

def check_dependency(name: str, command: str) -> Tuple[bool, str]:
    """
    Check if a dependency is installed.
    
    Args:
        name: Friendly name of the dependency
        command: Command to check version
        
    Returns:
        Tuple of (is_installed, version_output)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        version = result.stdout.strip().split('\n')[0] if result.stdout else "installed"
        logger.debug(f"{name}: {version}")
        return True, version
        
    except subprocess.TimeoutExpired:
        logger.warning(f"{name} check timed out")
        return False, "timeout"
    except subprocess.CalledProcessError as e:
        logger.debug(f"{name} not found: {e}")
        return False, str(e)
    except FileNotFoundError:
        logger.debug(f"{name} command not found in PATH")
        return False, "not in PATH"
    except Exception as e:
        logger.debug(f"Error checking {name}: {e}")
        return False, str(e)

def check_dependencies() -> Tuple[bool, Dict[str, bool]]:
    """
    Check for all required dependencies.
    
    Returns:
        Tuple of (all_satisfied, dependency_status_dict)
    """
    print("\n📦 Checking Dependencies")
    print("-" * 50)
    
    dependencies = {
        "Python": "python --version",
        "Ollama": "ollama --version",
        "Git": "git --version",
    }
    
    optional_dependencies = {
        "Claude Code": "claude --version",
    }
    
    status = {}
    missing_required = []
    missing_optional = []
    
    # Check required dependencies
    for name, command in dependencies.items():
        is_installed, version = check_dependency(name, command)
        status[name] = is_installed
        
        if is_installed:
            print(f"✓ {name}: {version}")
        else:
            print(f"✗ {name}: NOT FOUND")
            missing_required.append(name)
    
    # Check optional dependencies
    for name, command in optional_dependencies.items():
        is_installed, version = check_dependency(name, command)
        status[name] = is_installed
        
        if is_installed:
            print(f"✓ {name}: {version}")
        else:
            print(f"⚠ {name}: NOT FOUND (optional)")
            missing_optional.append(name)
    
    all_satisfied = len(missing_required) == 0
    
    if missing_required:
        print("\n⚠ REQUIRED dependencies missing:")
        for dep in missing_required:
            print(f"  • {dep}")
        print("\nPlease install the missing dependencies:")
        print("  - Ollama: https://ollama.ai")
        print("  - Git: https://git-scm.com")
    
    if missing_optional:
        print("\n⚠ OPTIONAL dependencies missing:")
        for dep in missing_optional:
            print(f"  • {dep}")
        print("\nTo enable Claude Code integration, install from:")
        print("  https://github.com/anthropics/claude-code")
    
    return all_satisfied, status

def check_models() -> Tuple[bool, List[str]]:
    """
    Check if configured models are available in Ollama.
    
    Returns:
        Tuple of (models_found, list_of_model_names)
    """
    print("\n🤖 Checking Models")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print("⚠ Could not list Ollama models")
            logger.warning(f"Ollama list failed: {result.stderr}")
            return False, []
        
        # Parse model list
        models = []
        if result.stdout:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
                    print(f"✓ Found model: {model_name}")
        
        if not models:
            print("⚠ No models installed")
            print("Run 'ollama pull <model>' to download a model")
            return False, []
        
        return True, models
        
    except FileNotFoundError:
        print("✗ Ollama not found - cannot check models")
        return False, []
    except subprocess.TimeoutExpired:
        print("⚠ Ollama check timed out")
        return False, []
    except Exception as e:
        print(f"✗ Error checking models: {e}")
        logger.error(f"Error checking models: {e}")
        return False, []

def check_mcp() -> Tuple[bool, Dict]:
    """
    Check MCP server configuration.
    
    Returns:
        Tuple of (config_valid, config_info)
    """
    print("\n🔌 Checking MCP Configuration")
    print("-" * 50)
    
    try:
        from paths import get_mcp_path
        
        mcp_path = get_mcp_path()
        config_file = mcp_path / "servers.json"
        
        if not config_file.exists():
            print("⚠ MCP configuration not found")
            logger.warning(f"MCP servers.json not found at {config_file}")
            return False, {}
        
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if not config:
            print("⚠ No MCP servers configured")
            return False, config
        
        print(f"✓ Found {len(config)} MCP server(s) configured")
        for server in config:
            print(f"  • {server}")
        
        return True, config
        
    except ImportError:
        logger.error("Could not import paths module")
        return False, {}
    except FileNotFoundError:
        print("⚠ MCP configuration not found")
        return False, {}
    except json.JSONDecodeError as e:
        print(f"✗ Invalid MCP configuration: {e}")
        logger.error(f"MCP config JSON error: {e}")
        return False, {}
    except Exception as e:
        print(f"✗ Error checking MCP: {e}")
        logger.error(f"Error checking MCP: {e}")
        return False, {}

def full_diagnostic() -> bool:
    """
    Run full diagnostic suite.
    
    Returns:
        True if all critical checks passed, False otherwise
    """
    logger.info("Starting full diagnostic")
    print("\n" + "=" * 50)
    print("🔍 Local AI Runtime Diagnostic")
    print("=" * 50)
    
    deps_ok, dep_status = check_dependencies()
    models_ok, models = check_models()
    mcp_ok, mcp_config = check_mcp()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Diagnostic Summary")
    print("=" * 50)
    print(f"Dependencies: {'✓ OK' if deps_ok else '✗ FAILED'}")
    print(f"Models: {'✓ OK' if models_ok else '⚠ WARNING'}")
    print(f"MCP Config: {'✓ OK' if mcp_ok else '⚠ WARNING'}")
    print("=" * 50)
    
    if deps_ok:
        print("\n✓ Your environment is ready to use!")
        logger.info("Diagnostic completed - environment is ready")
        return True
    else:
        print("\n✗ Please fix the issues above before using the runtime")
        logger.error("Diagnostic completed - environment has issues")
        return False