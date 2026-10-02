# Handles all AI Runtime commands. Should be the main entry point for the CLI.
import itertools
import sys
import logging
import threading
import time
from typing import Optional
from unittest import result

from Faber.ollama_service import start_ollama, stop_ollama
from Faber.session import stop_session, get_status, get_all_sessions
from Faber.models import (
    start_model, stop_model, build_model, pull_model, list_models, remove_model,
    _get_context,
)
from Faber.messaging import Message, chat as chat_with_model, generate
from Janus.doctor import full_diagnostic
from Mercurius import EventType, initialize_bus, publish_event, shutdown_bus

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
    
    pull <model>        Download a model from the Ollama registry
                        Example: python -m Janus pull qwen2.5:0.5b
    
    list                List models installed in Ollama
                        Example: python -m Janus list
    
    remove <model>      Remove a model from Ollama
                        Example: python -m Janus remove mercury
    
    ask <model> <prompt>
                        Send a single one-off prompt to a model and print its reply
                        Example: python -m Janus ask mercury "What is a closure?"
 
    chat <model> [--no-tools]
                        Start an interactive multi-turn conversation with a model
                        Example: python -m Janus chat mercury
                        (type 'exit' or 'quit' to end, or press Ctrl+C/Ctrl+D)
                        (in-chat: /save /note /remember /condense /history /tools /help)
                        If the model's MCP profile allows it, the model can use
                        filesystem tools (read_file, list_directory, ...) mid-chat.
                        Pass --no-tools to disable that.

    history [n]         Recall past chat/ask turns saved to disk
                        Example: python -m Janus history 20
                        python -m Janus history --model mercury
                        python -m Janus history --notes
                        python -m Janus history --facts

    doctor              Run diagnostic checks on your setup
                        Example: python -m Janus doctor
    
    mcp <action>        Manage MCP server and profiles
                        Example: python -m Janus mcp enable <server>
    
    help                Show this help message

EXAMPLES:
    python -m Janus status               # Check running models
    python -m Janus start mercury        # Start the Mercury model
    python -m Janus stop                 # Stop all models
    python -m Janus ask mercury "..."    # One-off prompt
    python -m Janus chat mercury         # Interactive conversation
    python -m Janus history              # Recall saved chat history
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
        publish_event(EventType.MODEL_LOADED, source="janus", payload={"model": model})
        
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
                publish_event(EventType.MODEL_UNLOADED, source="janus", payload={"model": model})
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

def handle_pull(args: list) -> None:
    """Handle the 'pull' command."""
    if len(args) < 1:
        logger.error("'pull' command requires a model name")
        print("Usage: python -m Janus pull <model>")
        print("Example: python -m Janus pull qwen2.5:0.5b")
        sys.exit(1)

    model = args[0]
    logger.info(f"Pulling model: {model}")

    try:
        pull_model(model)
        logger.info(f"Model '{model}' pulled successfully")
        print(f"[OK] Model '{model}' pulled")

    except Exception as e:
        logger.error(f"Failed to pull model: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)

def handle_list(args: list) -> None:
    """Handle the 'list' command."""
    try:
        models = list_models()
        if not models:
            print("No models installed")
            print("  Pull one with: python -m Janus pull <model>")
            return

        print("\nInstalled models:")
        for model in models:
            print(f"  {model['name']:30} {model['size']:>10}  {model['modified']}")

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)

def handle_remove(args: list) -> None:
    """Handle the 'remove' command."""
    if len(args) < 1:
        logger.error("'remove' command requires a model name")
        print("Usage: python -m Janus remove <model>")
        print("Example: python -m Janus remove mercury")
        sys.exit(1)

    model = args[0]
    logger.info(f"Removing model: {model}")

    try:
        remove_model(model)
        logger.info(f"Model '{model}' removed")
        print(f"[OK] Model '{model}' removed")

    except Exception as e:
        logger.error(f"Failed to remove model: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)

def handle_ask(args: list) -> None:
    """Handle the 'ask' command - a single one-off prompt to a model."""
    if len(args) < 2:
        logger.error("'ask' command requires a model name and a prompt")
        print("Usage: python -m Janus ask <model> <prompt>")
        print('Example: python -m Janus ask mercury "What is a closure?"')
        sys.exit(1)
 
    model = args[0]
    prompt = " ".join(args[1:])
    logger.info(f"Asking model '{model}': {prompt!r}")
 
    try:
        # Ensure Ollama server is running first, same as 'start'
        start_ollama()
 
        response = generate(model, prompt)
        print(response.content)
 
    except RuntimeError as e:
        logger.error(f"Failed to get response from model: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error asking model: {e}")
        print(f"[X] Unexpected error: {e}")
        sys.exit(1)


def _print_chat_help(tools_enabled: bool) -> None:
    print(
        "\nChat commands:\n"
        "  /help                 Show this list\n"
        "  /save                 Flush conversation + memory to disk now\n"
        "  /note <text>          Store a durable note (not trimmed, survives condense)\n"
        "  /remember <k>=<v>     Store a permanent user fact\n"
        "  /condense [n]         Fold all but the last n turns (default 10) into a note\n"
        "  /history [n]          Show the last n recorded turns (default 10)\n"
        + ("  /tools                List MCP tools available to this model\n" if tools_enabled else "")
        + "  exit, quit            End the chat"
    )


class _Spinner:
    """
    Simple terminal 'thinking' indicator for a blocking call (e.g. a chat
    request that may take a while, especially with tool round-trips).
 
    Runs a small braille-dot animation on a background thread and
    overwrites it in place (\\r, no newline) so it never pushes the
    model's eventual reply down the screen. Used as a context manager:
 
        with _Spinner("model is thinking"):
            response = chat_with_model(...)
 
    Safe to use even when stdout isn't a real terminal (e.g. captured by
    pytest or piped) - it just prints plain carriage-return-separated
    frames, which is harmless, not animated-looking, but never corrupts
    other output since it always clears its own line on stop().
    """
 
    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
 
    def __init__(self, message: str = "thinking", interval: float = 0.08,
                 color: str = "", endc: str = ""):
        self._message = message
        self._interval = interval
        self._color = color
        self._endc = endc
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
 
    def _spin(self) -> None:
        for frame in itertools.cycle(self._FRAMES):
            if self._stop_event.is_set():
                break
            line = f"\r{self._color}{frame} {self._message}...{self._endc}"
            sys.stdout.write(line)
            sys.stdout.flush()
            self._stop_event.wait(self._interval)
 
    def start(self) -> "_Spinner":
        if self._thread is not None:
            return self
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self
 
    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=1)
        self._thread = None
        # Clear the spinner line so the next print (the reply, or an
        # error) starts clean rather than appending after the frame.
        clear_width = len(self._message) + 6
        sys.stdout.write("\r" + " " * clear_width + "\r")
        sys.stdout.flush()
 
    def __enter__(self) -> "_Spinner":
        return self.start()
 
    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


def _setup_filesystem_tools(model: str):
    """
    If `model`'s MCP profile grants access to the "filesystem" server,
    launch it and return (MCPClient, ollama_tools) ready to pass into
    chat_with_model(tools=..., tool_executor=...). Returns (None, None)
    when the model has no profile, the profile doesn't include
    filesystem, or the server fails to launch - chat proceeds without
    tools in every one of those cases rather than failing the session.
    """
    try:
        from Custos.mcp import MCPManager, ProfileNotFoundError, MCPConfigError, \
            filter_tools_for_model, mcp_tools_to_ollama_tools
        from Custos.mcp_client import MCPClient, MCPClientError

        manager = MCPManager()
        try:
            allowed = manager.get_tools(model)
        except ProfileNotFoundError:
            logger.info(f"No MCP profile for model '{model}' - chatting without tools")
            return None, None

        if "filesystem" not in allowed:
            return None, None

        server_config = manager.get_server_config("filesystem")
        client = MCPClient("filesystem", server_config)
        client.start()

        live_tools = client.list_tools()
        permitted = filter_tools_for_model(live_tools, "filesystem", model, manager)
        if not permitted:
            client.close()
            return None, None

        return client, mcp_tools_to_ollama_tools(permitted)

    except (MCPConfigError, MCPClientError) as e:
        logger.warning(f"MCP filesystem tools unavailable: {e}")
        print(f"[!] MCP filesystem tools unavailable ({e}) - chatting without tools")
        return None, None
    except Exception as e:
        logger.warning(f"Unexpected error setting up MCP tools: {e}")
        print(f"[!] Could not set up MCP tools ({e}) - chatting without tools")
        return None, None


def handle_chat(args: list) -> None:
    """Handle the 'chat' command - an interactive multi-turn conversation
    with a model, read from stdin one line at a time until the user types
    'exit'/'quit' or sends EOF (Ctrl+D) / interrupts (Ctrl+C).
 
    Each turn is sent with the full in-memory history for model context,
    but recorded into Mentis AIMemory exactly once per turn (record=False
    on the API call, with this handler doing the recording itself) so
    memory doesn't accumulate duplicate copies of earlier turns.
 
    Slash-commands (/save, /note, /remember, /condense, /history) give
    direct access to the memory API without leaving the chat. State is
    also saved automatically on normal CLI exit (see Janus.main.main),
    so /save is only needed for an explicit mid-session flush.

    MCP tools: if the model's MCP profile (mcp/profiles/<Model>.json)
    grants access to the "filesystem" server, this launches it and lets
    the model call its tools (read_file, list_directory, etc.) mid-chat.
    Pass --no-tools to disable this for the session. Tool calls and their
    results are printed as they happen and recorded into AIMemory
    alongside the conversation, so `janus history` shows the full trace.
    """

    class PrintColors:
        HEADER = '\033[95m'

        FAIL = '\033[91m'
        WARNING = '\033[93m'
        
        OKGREEN = '\033[92m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKYELLOW = '\033[93m'

        ENDC = '\033[0m'

        BOLD = '\033[1m'
        ITALICS = '\033[3m'
        UNDERLINE = '\033[4m'

    if len(args) < 1:
        logger.error("'chat' command requires a model name")
        print("Usage: python -m Janus chat <model>")
        print("Example: python -m Janus chat mercury")
        sys.exit(1)
 
    model = args[0]
    tools_disabled = "--no-tools" in args
    logger.info(f"Starting chat session with model: {model}")
    print("\n\n")
 
    try:
        start_ollama()
    except Exception as e:
        logger.error(f"Failed to start Ollama server: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)
 
    ctx = _get_context()
    if ctx is None:
        print("[!] No runtime context bound - this chat will not be saved to memory")

    mcp_client = None
    ollama_tools = None
    if not tools_disabled:
        mcp_client, ollama_tools = _setup_filesystem_tools(model)

    tools_enabled = mcp_client is not None
    permitted_tool_names = set()
    if tools_enabled:
        permitted_tool_names = {t["function"]["name"] for t in ollama_tools}
        print(
            f"{PrintColors.OKCYAN}[TOOLS] filesystem tools available: {PrintColors.ENDC}"
            f"{PrintColors.OKGREEN}{', '.join(permitted_tool_names)}{PrintColors.ENDC}"
        )
        print("\n")

    # Holds the active _Spinner (if any) so tool_executor can silence it
    # for the duration of its own prints and restart it afterward -
    # otherwise the spinner's background thread and the tool's [TOOL]
    # prints would interleave into garbled output, since both write to
    # stdout from the same blocking chat_with_model() call.
    active_spinner: dict = {"spinner": None}

    def tool_executor(tool_name: str, arguments: dict) -> str:
        spinner = active_spinner["spinner"]
        if spinner is not None:
            spinner.stop()
        try:
            # Enforce the profile allowlist at call time, not just at
            # advertisement time. The model can request any tool name it
            # likes (hallucination, or prompt injection via file contents
            # it read), so only tools that were actually offered may run.
            if tool_name not in permitted_tool_names:
                print(f"\n{PrintColors.FAIL}  [TOOL] {tool_name}({arguments})")
                print(f"  [TOOL] -> DENIED (not permitted for this model's MCP profile){PrintColors.ENDC}")
                raise PermissionError(
                    f"Tool '{tool_name}' is not permitted for model '{model}'. "
                    f"Available tools: {', '.join(sorted(permitted_tool_names))}"
                )
            print(f"\n\n{PrintColors.OKYELLOW}  [TOOL] {tool_name}({arguments}){PrintColors.ENDC}")
            result = mcp_client.call_tool(tool_name, arguments)
            truncated = len(result) > 200
            body = result[:200] + "..." if truncated else result
            preview = f"**START TOOL PREVIEW**\n\n{body}\n\n**END TOOL PREVIEW**\n\n"
            print(f"{PrintColors.OKCYAN}  [TOOL] ->\n{preview}{PrintColors.ENDC}")
            return result
        finally:
            if spinner is not None:
                spinner.start()
 
    print(f"{PrintColors.HEADER}[CHAT] Chatting with '{model}'{PrintColors.ENDC}")
    print(f"{PrintColors.OKYELLOW}{PrintColors.ITALICS}\tType 'exit' or 'quit' to end (Ctrl+C/Ctrl+D also work){PrintColors.ENDC}")
    print(f"{PrintColors.OKYELLOW}{PrintColors.ITALICS}\tType /help to see in-chat memory commands\n{PrintColors.ENDC}")
    history: list = []

    try:
 
        while True:
            try:
                user_input = input(f"\n{PrintColors.OKGREEN}You: {PrintColors.ENDC}").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[OK] Chat ended")
                return
 
            if not user_input:
                continue
 
            if user_input.lower() in ("exit", "quit"):
                print("[OK] Chat ended")
                return
 
            if user_input.startswith("/"):
                _handle_chat_slash_command(user_input, ctx, history, tools_enabled, ollama_tools)
                continue
 
            history.append(Message("user", user_input))
 
            try:
                # record=False: we record exactly the new turn ourselves below,
                # rather than letting the API re-record the whole history list
                # (which grows every turn) and duplicate every earlier message.
                spinner = _Spinner(f"{model} is thinking",
                                    color=PrintColors.OKCYAN, endc=PrintColors.ENDC)
                active_spinner["spinner"] = spinner
                try:
                    with spinner:
                        response = chat_with_model(
                            model, history, record=False,
                            tools=ollama_tools if tools_enabled else None,
                            tool_executor=tool_executor if tools_enabled else None,
                        )
                finally:
                    active_spinner["spinner"] = None
            except RuntimeError as e:
                logger.error(f"Chat request failed: {e}")
                print(f"[X] Error: {e}")
                # Drop the unanswered user turn so a retry doesn't duplicate it
                history.pop()
                continue
            except Exception as e:
                logger.error(f"Unexpected error during chat: {e}")
                print(f"[X] Unexpected error: {e}")
                history.pop()
                continue
 
            # Tool-call turns the loop already resolved (assistant request +
            # tool result pairs) - fold into history so the next turn's
            # context includes them, and record them the same way the API's
            # own record=True path would have. Recorded via the ctx already
            # in scope here (not Faber.messaging's own _get_context lookup)
            # so this works with whatever context handle_chat is bound to.
            history.extend(response.tool_trace)
            if ctx is not None:
                for trace_message in response.tool_trace:
                    metadata = {"model": model}
                    if trace_message.tool_name:
                        metadata["tool_name"] = trace_message.tool_name
                    ctx.update_ai_memory(trace_message.role, trace_message.content,
                                          metadata=metadata)
 
            history.append(Message(response.message.role, response.message.content))
            print(f"\n{PrintColors.OKBLUE}{model}: {PrintColors.ENDC}{response.content}\n")
 
            if ctx is not None:
                ctx.update_ai_memory("user", user_input)
                ctx.update_ai_memory(response.message.role, response.message.content,
                                      metadata={"model": model})
    finally:
        if mcp_client is not None:
            mcp_client.close()
 
 
def _handle_chat_slash_command(command: str, ctx, history: list,
                                tools_enabled: bool = False,
                                ollama_tools: Optional[list] = None) -> None:
    """Handle a single /command typed inside the chat REPL."""
    parts = command[1:].split(maxsplit=1)
    name = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""
 
    if name == "help":
        _print_chat_help(tools_enabled)
        return

    if name == "tools":
        # Doesn't need a RuntimeContext - purely reports what's loaded.
        if not tools_enabled or not ollama_tools:
            print("[!] No MCP tools are enabled for this chat "
                  "(model has no filesystem access in its profile, or --no-tools was used)")
            return
        print("\nAvailable MCP tools:")
        for tool in ollama_tools:
            fn = tool["function"]
            print(f"  {fn['name']:<20} {fn.get('description', '')}")
        return
 
    if ctx is None:
        print("[!] No runtime context bound - memory commands are unavailable")
        return
 
    if name == "save":
        ctx.shutdown()
        # shutdown() also flips is_running/unloads models, which we don't
        # want mid-chat - re-open the context so the session can continue.
        ctx.is_running = True
        print("[OK] Saved to disk")
 
    elif name == "note":
        if not rest:
            print("Usage: /note <text>")
            return
        ctx.store_conversation_note(rest)
        print("[OK] Note stored")
 
    elif name == "remember":
        if "=" not in rest:
            print("Usage: /remember <key>=<value>")
            return
        key, _, value = rest.partition("=")
        key, value = key.strip(), value.strip()
        if not key:
            print("Usage: /remember <key>=<value>")
            return
        ctx.remember_user_fact(key, value)
        print(f"[OK] Remembered {key} = {value}")
 
    elif name == "condense":
        keep_recent = 10
        if rest:
            try:
                keep_recent = int(rest)
            except ValueError:
                print("Usage: /condense [number of recent turns to keep]")
                return
        note = ctx.condense_conversation(keep_recent=keep_recent)
        if note is None:
            print("[!] Nothing to condense yet")
        else:
            print(f"[OK] Condensed into a note (kept last {keep_recent} turns)")
 
    elif name == "history":
        num = 10
        if rest:
            try:
                num = int(rest)
            except ValueError:
                print("Usage: /history [number of turns]")
                return
        recent = ctx.get_ai_context(num_messages=num)
        if not recent:
            print("(no recorded history yet)")
        else:
            for entry in recent:
                print(f"  {entry.get('role', '?')}: {entry.get('content', '')}")
 
    else:
        print(f"[X] Unknown command: /{name} (try /help)")
 
 
def handle_history(args: list) -> None:
    """Handle the 'history' command - recall past chat/ask exchanges saved
    to disk by a previous CLI session, without starting a new interactive
    session or prompting to initialize a host project.
 
    Usage:
        python -m Janus history [n]              Last n turns (default 20)
        python -m Janus history --model <name>    Only turns from that model
        python -m Janus history --notes           Show stored notes instead
        python -m Janus history --facts           Show remembered user facts
    """
    from pathlib import Path
    from Janus.paths import host_marker_exists_at
 
    cwd = Path.cwd()
    if not host_marker_exists_at(cwd):
        print("[!] No initialized Domus host project found in the current directory")
        print("    (looked for .domus-host-marker and .domus-AI/ here)")
        print("    Run a command like 'python -m Janus chat <model>' from your project directory first")
        return
 
    show_notes = "--notes" in args
    show_facts = "--facts" in args
    model_filter: Optional[str] = None
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model_filter = args[idx + 1]
 
    num = 20
    for a in args:
        if a.isdigit():
            num = int(a)
            break
 
    try:
        from Mentis.context import RuntimeContext
        ctx = RuntimeContext(project_name="LocalAIRuntime")
        started = ctx.startup(suggested_host=cwd, non_interactive=True)
        if not started:
            print("[X] Could not load saved state")
            return
    except Exception as e:
        logger.error(f"Failed to load saved state: {e}")
        print(f"[X] Error loading saved state: {e}")
        return
 
    try:
        if show_notes:
            notes = ctx.ai_memory.conversation_notes
            if not notes:
                print("(no notes stored)")
                return
            print(f"\n[NOTES] {len(notes)} stored note(s):")
            for note in notes[-num:]:
                print(f"\n  [{note.get('timestamp', '?')}] ({note.get('kind', 'note')})")
                print(f"  {note.get('content', '')}")
            return
 
        if show_facts:
            facts = ctx.ai_memory.user_memory
            if not facts:
                print("(no user facts remembered)")
                return
            print(f"\n[FACTS] {len(facts)} remembered fact(s):")
            for key, entry in facts.items():
                print(f"  {key} = {entry.get('value')}  (updated {entry.get('updated_at', '?')})")
            return
 
        history = ctx.ai_memory.conversation_history
        if model_filter:
            history = [
                h for h in history
                if h.get("metadata", {}).get("model") == model_filter
            ]
 
        if not history:
            print("(no recorded chat/ask history yet)")
            return
 
        recent = history[-num:]
        print(f"\n[HISTORY] Showing last {len(recent)} of {len(history)} recorded turn(s):")
        for entry in recent:
            role = entry.get("role", "?")
            content = entry.get("content", "")
            model = entry.get("metadata", {}).get("model")
            tag = f" ({model})" if model else ""
            print(f"\n  [{entry.get('timestamp', '?')}] {role}{tag}:")
            print(f"  {content}")
 
    finally:
        # Read-only recall - persist nothing, don't touch the saved state.
        ctx.is_running = False
 

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
    elif action == "tools":
        handle_mcp_tools(args[1:])
    else:
        print(f"[!] MCP functionality not yet fully implemented: {action}")
        # TODO: Implement other MCP functionality
 
def handle_mcp_tools(args: list) -> None:
    """Handle listing the MCP tools a model's profile permits."""
    if len(args) < 1:
        logger.error("'mcp tools' requires a model name")
        print("Usage: python -m Janus mcp tools <model>")
        print("Example: python -m Janus mcp tools Mercury")
        sys.exit(1)

    model = args[0]

    try:
        from Custos.mcp import MCPManager

        manager = MCPManager()
        tools = manager.get_tools(model)

        print(f"MCP tools permitted for '{model}':")
        if not tools:
            print("  (none - profile has no servers/tools declared)")
        for server, allowed in tools.items():
            rendered = ", ".join(allowed) if allowed else "(no tools allowed)"
            print(f"  {server}: {rendered}")

    except Exception as e:
        logger.error(f"Failed to list MCP tools: {e}")
        print(f"[X] Error: {e}")
        sys.exit(1)
 
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
        elif command == "list":
            # Read-only query against the Ollama server - no RuntimeContext needed
            handle_list(args)
        elif command == "history":
            # Read-only recall of saved chat/ask memory - no interactive prompt
            handle_history(args)
        elif command == "mcp" and args and args[0].lower() == "tools":
            # Read-only config query - no RuntimeContext needed
            handle_mcp_tools(args[1:])
        else:
            ctx = None
            bus_running = False
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

                initialize_bus()
                publish_event(EventType.STARTUP, source="janus", payload={"command": command})
                bus_running = True

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
                elif command == "pull":
                    handle_pull(args)
                elif command == "list":
                    handle_list(args)
                elif command == "remove":
                    handle_remove(args)
                elif command == "ask":
                    handle_ask(args)
                elif command == "chat":
                    handle_chat(args)
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
            finally:
                # Pair SHUTDOWN with STARTUP - only when the bus actually started
                if bus_running:
                    publish_event(EventType.SHUTDOWN, source="janus", payload={"command": command})
                    shutdown_bus()
                # Persist AI memory / config / events to disk - only when
                # startup actually succeeded and produced a live context.
                if ctx is not None:
                    ctx.shutdown()
                    
        return 0

    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\n[X] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())  # <- PROPER EXIT CODE