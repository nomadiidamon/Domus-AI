# Handles all AI Runtime commands. Should be the main entry point for the CLI.
import sys
import logging
from typing import Optional

from Faber.ollama_service import start_ollama, stop_ollama
from Faber.session import stop_session, get_status, get_all_sessions
from Faber.models import start_model, stop_model, build_model
from Janus.doctor import full_diagnostic

from utils import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def print_help() -> None:
    """Print help message with available commands and usage."""
    help_text = """
Local AI Runtime - CLI for managing local AI models with Ollama and Claude Code

USAGE:
    python -m Janus <command> [options]

COMMANDS:
    start <model>       Start a model instance
                        Example: python -m Janus start mercury
    
    stop [model]        Stop a running model (or all if no model specified)
                        Example: python -m Janus stop mercury
    
    status              Show status of all active models
                        Example: python -m Janus status
    
    build <model>       Build a custom model from Modelfile
                        Example: python -m Janus build mercury
    
    doctor              Run diagnostic checks on your setup
                        Example: python -m Janus doctor
    
    mcp <action>        Manage MCP server and profiles
                        Example: python -m Janus mcp enable <server>
    
    help                Show this help message

EXAMPLES:
    python -m Janus status               # Check running models
    python -m Janus start mercury        # Start the Mercury model
    python -m Janus stop                 # Stop all models
    python -m Janus doctor               # Diagnose setup issues

For more information, visit: https://github.com/nomadiidamon/Local-AI-Runtime
"""
    print(help_text)

def handle_start(args: list) -> None:
    """Handle the 'start' command."""
    if len(args) < 1:  # <- VALIDATION
        logger.error("'start' command requires a model name")
        print("Usage: python -m Janus start <model>")
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
        print(f"[OK] Model '{model}' is running")  # <- USER FEEDBACK
        
    except RuntimeError as e:
        logger.error(f"Failed to start model: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error starting model: {e}")
        print(f"[X] Unexpected error: {e}")
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
                print(f"[OK] Model '{model}' stopped")
            else:
                logger.warning(f"Model '{model}' was not running")
                print(f"[!] Model '{model}' was not running")
        else:
            # Stop all active sessions, then the Ollama server itself
            logger.info("Stopping all models and Ollama server")
            for session_name in list(get_all_sessions().keys()):
                stop_session(session_name)
            stop_ollama()
            logger.info("All models stopped")
            print("[OK] All models and Ollama server stopped")
            
    except Exception as e:
        logger.error(f"Error stopping model: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)

def handle_status() -> None:
    """Handle the 'status' command."""
    from Hestia.hardware import print_hardware_report

    sessions = get_status()

    if not sessions:
        print("No active sessions")
    else:
        print("\nActive Sessions:")

        for session in sessions:

            state = "RUNNING" if session["running"] else "STOPPED"

            print(
                f"""
Name:    {session['name']}
Type:    {session['type']}
PID:     {session['pid']}
State:   {state}
Started: {session['started']}
"""
            )

    try:
        from Faber.models import _context as ctx

        if ctx is not None:
            ctx.refresh_hardware()
            print_hardware_report(ctx.hardware_profile, ctx.model_recommendation)
        else:
            from Hestia.hardware import detect_hardware, recommend_model
            profile = detect_hardware()
            print_hardware_report(profile, recommend_model(profile))

    except Exception as e:
        logger.warning(f"Could not display hardware report: {e}")

def handle_build(args: list) -> None:
    """Handle the 'build' command."""
    if len(args) < 1:
        logger.error("'build' command requires a model name")
        print("Usage: python -m Janus build <model>")
        print("Example: python -m Janus build mercury")
        sys.exit(1)
    
    model = args[0]
    logger.info(f"Building model: {model}")
    
    try:
        build_model(model)
        logger.info(f"Model '{model}' built successfully")
        print(f"[OK] Model '{model}' built successfully")
        
    except Exception as e:
        logger.error(f"Failed to build model: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)

def handle_doctor():
    """Handle the 'doctor' command."""
    logger.info("Running diagnostic checks...")
    print("\n[FIND] Running diagnostic checks...")
    print("=" * 50)
    
    try:
        status = full_diagnostic()
        print("=" * 50)
        if status:
            print("[OK] All checks passed")
            logger.info("Diagnostic checks completed successfully")
        else:
            print("[X] Some checks failed")
            logger.warning("Diagnostic checks completed with issues")
        
    except Exception as e:
        logger.error(f"Diagnostic check failed: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)

def handle_mcp(args: list) -> None:
    """Handle the 'mcp' command."""
    if len(args) < 1:
        logger.error("'mcp' command requires an action")
        print("Usage: python -m Janus mcp <action> [options]")
        print("Example: python -m Janus mcp launch mercury")
        sys.exit(1)
    
    action = args[0].lower()
    logger.info(f"MCP action: {action}")
    
    if action == "launch":
        handle_mcp_launch(args[1:])
    else:
        print(f"[!] MCP functionality not yet fully implemented: {action}")
        # TODO: Implement other MCP functionality
 
def handle_mcp_launch(args: list) -> None:
    """Handle launching Claude Code via Ollama."""
    if len(args) < 1:
        logger.error("'mcp launch' requires a model name")
        print("Usage: python -m Janus mcp launch <model> [--yes]")
        print("Example: python -m Janus mcp launch qwen3.5")
        print("Example: python -m Janus mcp launch gemma4:cloud --yes")
        sys.exit(1)
    
    model = args[0]
    auto_yes = "--yes" in args
    
    try:
        from Faber.claude_service import ollama_launch_claude
        
        logger.info(f"Launching Claude Code with model: {model}")
        print(f"[LAUNCH] Launching Claude Code with model: {model}")
        print("   See: https://docs.ollama.com/integrations/claude-code")
        
        process = ollama_launch_claude(model, auto_yes=auto_yes)
        
        logger.info(f"Claude Code launched (PID: {process.pid})")
        print(f"[OK] Claude Code is running (PID: {process.pid})")
        print("   You can now use Claude Code in your terminal!")
        
    except RuntimeError as e:
        logger.error(f"Failed to launch Claude Code: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error launching Claude Code: {e}")
        print(f"[X] Unexpected error: {e}")
        sys.exit(1)

def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Show help if no arguments
    if len(sys.argv) < 2:
        print_help()
        return 0
    
    # --root is a suggestion only - context.startup() still prompts for confirmation
    raw_args = sys.argv[1:]
    suggested_root = None

    if "--root" in raw_args:
        idx = raw_args.index("--root")
        if idx + 1 < len(raw_args):
            suggested_root = raw_args[idx + 1]
            raw_args = raw_args[:idx] + raw_args[idx + 2:]
        else:
            print("[X] --root requires a path argument")
            return 1

    command = raw_args[0].lower() if raw_args else ""
    args = raw_args[1:]

    try:
        if command in ["help", "-h", "--help"]:
            print_help()
        elif command == "status":
            handle_status() 
        elif command == "doctor":
            handle_doctor()
        else:
            ctx = None
            # Initialize runtime context and bind it to models
            try:
                from Mentis.context import RuntimeContext
                from Faber.models import set_context
                from pathlib import Path

                ctx = RuntimeContext(project_name="LocalAIRuntime")
                started = ctx.startup(
                    suggested_host=Path(suggested_root) if suggested_root else None
                )

                if not started:
                    return 1

                set_context(ctx)

            except Exception as e:
                logger.warning(f"RuntimeContext unavailable, continuing without it: {e}")
                ctx = None
            
            try:
                if command == "start":
                    handle_start(args)
                elif command == "stop":
                    handle_stop(args)
                elif command == "build":
                    handle_build(args)
                elif command == "mcp":
                    handle_mcp(args)
                else:
                    logger.error(f"Unknown command: {command}")
                    print(f"[X] Unknown command: '{command}'")
                    print("\nRun 'python -m Janus help' for usage information")
                    return 1  # <- PROPER EXIT CODE
                
                return 0  # <- SUCCESS EXIT CODE
                
            except KeyboardInterrupt:
                logger.info("Operation cancelled by user")
                print("\n[!] Operation cancelled")
                return 1  # <- GRACEFUL Ctrl+C
            except Exception as e:
                logger.critical(f"Unexpected error in main: {e}", exc_info=True)
                print(f"\n[X] Unexpected error: {e}")
                return 1

        return 0

    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\n[X] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())  # <- PROPER EXIT CODE