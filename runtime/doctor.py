# Checks for all needed dependencies: Python, Ollama, Claude, Git, Models, MCP validation, and more. If any dependencies are missing, it will prompt the user to install them.

import subprocess
import logging
import urllib.request
import urllib.error
from typing import Dict, List, Tuple
from pathlib import Path
from runtime.dependencies import (
    DependencyChecker, PythonPackageDependency,
    SystemCommandDependency, DependencyStatus
)

logger = logging.getLogger(__name__)

OLLAMA_API_BASE = "http://localhost:11434"

def _build_checker() -> DependencyChecker:
    """Build the standard dependency checker for the runtime."""
    checker = DependencyChecker()

    checker.register_many([
        SystemCommandDependency("python",  required=True,  description="Python interpreter"),
        SystemCommandDependency("ollama",  required=True,  description="Ollama runtime"),
        SystemCommandDependency("git",     required=True,  description="Git version control"),
        SystemCommandDependency("claude",  required=False, description="Claude Code (optional)"),
        PythonPackageDependency("psutil",  required=True,  description="System monitoring"),
        PythonPackageDependency("pynvml",  required=True, description="NVIDIA GPU monitoring (required only for NVIDIA GPUs)"),
    ])

    return checker

def check_dependencies() -> Tuple[bool, Dict[str, bool]]:
    """
    Check for all required dependencies.
    
    Returns:
        Tuple of (all_satisfied, dependency_status_dict)
    """
    print("\n📦 Checking Dependencies")
    print("-" * 50)
    
    checker = _build_checker()
    results = checker.check_all()

    status = {}
    all_satisfied = True

    for name, result in results.items():
        status[name] = result.is_healthy
        dep = checker.dependencies[name]

        if result.is_healthy:
            print(f"✓ {name}: {result.version or result.message}")
        elif not dep.required:
            print(f"⚠ {name}: NOT FOUND (optional)")
        else:
            print(f"✗ {name}: NOT FOUND")
            all_satisfied = False

    summary = checker.get_summary()

    if not all_satisfied:
        print("\n⚠ REQUIRED dependencies missing:")
        for name, result in results.items():
            dep = checker.dependencies[name]
            if dep.required and not result.is_healthy:
                print(f"  • {name} — {dep.get_install_instructions()}")

    missing_optional = [
        name for name, result in results.items()
        if not result.is_healthy and not checker.dependencies[name].required
    ]
    if missing_optional:
        print("\n⚠ OPTIONAL dependencies missing:")
        for name in missing_optional:
            print(f"  • {name} — {checker.dependencies[name].get_install_instructions()}")

    return all_satisfied, status

def _check_ollama_server_running(timeout: int = 3) -> bool:
    """
    Check whether the Ollama server is reachable via its health endpoint.

    Uses a plain HTTP request with a short timeout — no subprocess involved,
    so it cannot hang due to child process pipe issues.

    Args:
        timeout: Seconds to wait before giving up.

    Returns:
        True if the server responded, False otherwise.
    """
    try:
        urllib.request.urlopen(f"{OLLAMA_API_BASE}/api/tags", timeout=timeout)
        return True
    except urllib.error.URLError:
        return False
    except Exception:
        return False

def check_models() -> Tuple[bool, List[str]]:
    """
    Check if configured models are available in Ollama.
    
    Returns:
        Tuple of (models_found, list_of_model_names)
    """
    print("\n🤖 Checking Models")
    print("-" * 50)
    
    if not _check_ollama_server_running():
        print("⚠ Ollama server is not running — cannot list models")
        print("  Start it with:  ollama serve")
        logger.warning("Ollama server unreachable at %s", OLLAMA_API_BASE)
        return False, []

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
        from runtime.paths import get_mcp_path
        
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
    print("\n**DEPENDENCIES CHECK COMPLETE**")
    print("\n" + "=" * 50)
    models_ok, models = check_models()
    print("\n**MODELS CHECK COMPLETE**")
    print("\n" + "=" * 50)
    mcp_ok, mcp_config = check_mcp()
    print("\n**MCP CHECK COMPLETE**")
    
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