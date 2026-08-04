# Handles all AI Runtime commands. Should be the main entry point for the CLI.
import sys
import logging
from typing import Optional

from .ollama_service import start_ollama, stop_ollama
from session import stop_session, get_status
from models import start_model, stop_model, build_model
from doctor import full_diagnostic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_help() -> None:
    """Print help message with available commands and usage."""
    help_text = """
Local AI Runtime - CLI for managing local AI models with Ollama and Claude Code

USAGE:
    python main.py <command> [options]

COMMANDS:
    start <model>       Start a model instance
                        Example: python main.py start mercury
    
    stop [model]        Stop a running model (or all if no model specified)
                        Example: python main.py stop mercury
    
    status              Show status of all active models
                        Example: python main.py status
    
    build <model>       Build a custom model from Modelfile
                        Example: python main.py build mercury
    
    doctor              Run diagnostic checks on your setup
                        Example: python main.py doctor
    
    mcp <action>        Manage MCP server and profiles
                        Example: python main.py mcp enable <server>
    
    help                Show this help message

EXAMPLES:
    python main.py status               # Check running models
    python main.py start mercury        # Start the Mercury model
    python main.py stop                 # Stop all models
    python main.py doctor               # Diagnose setup issues

For more information, visit: https://github.com/nomadiidamon/Local-AI-Runtime
"""
    print(help_text)

def handle_start(args: list) -> None:
    """Handle the 'start' command."""
    if len(args) < 1:  # <- VALIDATION
        logger.error("'start' command requires a model name")
        print("Usage: python main.py start <model>")
        sys.exit(1)  # <- PROPER EXIT
    
    model = args[0]
    logger.info(f"Starting model: {model}")
    
    try:
        # Ensure Ollama server is running first
        logger.debug("Checking if Ollama server is running...")
        start_ollama()
        
        # Now start the model
        start_model(model)
        logger.info(f"Model '{model}' started successfully")
        print(f"✓ Model '{model}' is running")  # <- USER FEEDBACK
        
    except RuntimeError as e:
        logger.error(f"Failed to start model: {e}")
        print(f"✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error starting model: {e}")
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)
       
def handle_stop(args: list) -> None:
    """Handle the 'stop' command."""
    try:
        if len(args) > 0:
            # Stop specific model
            model = args[0]
            logger.info(f"Stopping model: {model}")
            if stop_model(model):
                logger.info(f"Model '{model}' stopped successfully")
                print(f"✓ Model '{model}' stopped")
            else:
                logger.warning(f"Model '{model}' was not running")
                print(f"⚠ Model '{model}' was not running")
        else:
            # Stop all models and server
            logger.info("Stopping all models and Ollama server")
            stop_session()
            stop_ollama()
            logger.info("All models stopped")
            print("✓ All models and Ollama server stopped")
            
    except Exception as e:
        logger.error(f"Error stopping model: {e}")
        print(f"✗ Error: {e}")
        sys.exit(1)

def handle_status():

    sessions = get_status()


    if not sessions:

        print("No active sessions")
        return


    print("\nActive Sessions:")

    for session in sessions:

        state = (
            "RUNNING"
            if session["running"]
            else "STOPPED"
        )

        print(
            f"""
Name: {session['name']}
Type: {session['type']}
PID: {session['pid']}
State: {state}
Started: {session['started']}
"""
        )

def handle_build(args: list) -> None:
    """Handle the 'build' command."""
    if len(args) < 1:
        logger.error("'build' command requires a model name")
        print("Usage: python main.py build <model>")
        print("Example: python main.py build mercury")
        sys.exit(1)
    
    model = args[0]
    logger.info(f"Building model: {model}")
    
    try:
        build_model(model)
        logger.info(f"Model '{model}' built successfully")
        print(f"✓ Model '{model}' built successfully")
        
    except Exception as e:
        logger.error(f"Failed to build model: {e}")
        print(f"✗ Error: {e}")
        sys.exit(1)

def handle_doctor():
    """Handle the 'doctor' command."""
    logger.info("Running diagnostic checks...")
    print("\n🔍 Running diagnostic checks...")
    print("=" * 50)
    
    try:
        full_diagnostic()
        logger.info("Diagnostic checks completed successfully")
        print("=" * 50)
        print("✓ All checks passed")
        
    except Exception as e:
        logger.error(f"Diagnostic check failed: {e}")
        print(f"✗ Error: {e}")
        sys.exit(1)

def handle_mcp(args: list) -> None:
    """Handle the 'mcp' command."""
    if len(args) < 1:
        logger.error("'mcp' command requires an action")
        print("Usage: python main.py mcp <action> [options]")
        print("Example: python main.py mcp launch mercury")
        sys.exit(1)
    
    action = args[0].lower()
    logger.info(f"MCP action: {action}")
    
    if action == "launch":
        handle_mcp_launch(args[1:])
    else:
        print(f"⚠ MCP functionality not yet fully implemented: {action}")
        # TODO: Implement other MCP functionality
 
def handle_mcp_launch(args: list) -> None:
    """Handle launching Claude Code via Ollama."""
    if len(args) < 1:
        logger.error("'mcp launch' requires a model name")
        print("Usage: python main.py mcp launch <model> [--yes]")
        print("Example: python main.py mcp launch qwen3.5")
        print("Example: python main.py mcp launch gemma4:cloud --yes")
        sys.exit(1)
    
    model = args[0]
    auto_yes = "--yes" in args
    
    try:
        from claude import ollama_launch_claude
        
        logger.info(f"Launching Claude Code with model: {model}")
        print(f"🚀 Launching Claude Code with model: {model}")
        print("   See: https://docs.ollama.com/integrations/claude-code")
        
        process = ollama_launch_claude(model, auto_yes=auto_yes)
        
        logger.info(f"Claude Code launched (PID: {process.pid})")
        print(f"✓ Claude Code is running (PID: {process.pid})")
        print("   You can now use Claude Code in your terminal!")
        
    except RuntimeError as e:
        logger.error(f"Failed to launch Claude Code: {e}")
        print(f"✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error launching Claude Code: {e}")
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)

def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Show help if no arguments
    if len(sys.argv) < 2:  # <- VALIDATION
        print_help()
        return 0
    
    command = sys.argv[1].lower()
    args = sys.argv[2:]  # <- SAFE SLICING
    
    try:
        if command == "start":
            handle_start(args)
        elif command == "stop":
            handle_stop(args)
        elif command == "status":
            handle_status()
        elif command == "build":
            handle_build(args)
        elif command == "doctor":
            handle_doctor()
        elif command == "mcp":
            handle_mcp(args)
        elif command in ["help", "-h", "--help"]:
            print_help()
        else:
            logger.error(f"Unknown command: {command}")
            print(f"✗ Unknown command: '{command}'")
            print("\nRun 'python main.py help' for usage information")
            return 1  # <- PROPER EXIT CODE
        
        return 0  # <- SUCCESS EXIT CODE
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\n⚠ Operation cancelled")
        return 1  # <- GRACEFUL Ctrl+C
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\n✗ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())  # <- PROPER EXIT CODE