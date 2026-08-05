# Handles the current state of the runtime environment, including hardware specifications, project and working directories and AI memory.

"""
context.py - Runtime context and state management for Local AI Runtime.

Manages project state, working directories, hardware capabilities, and AI memory.
Serves as the central state store for the entire runtime.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading

from hardware import (
    HardwareProfile, HardwareDetector, ModelRecommender, ModelRecommendation,
    AcceleratorType, ModelSize
)


logger = logging.getLogger(__name__)


class RuntimeMode(Enum):
    """Operating modes for the runtime."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    INFERENCE_ONLY = "inference_only"
    TRAINING = "training"


class ContextEventType(Enum):
    """Events that can be tracked in context."""
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    MODEL_LOADED = "model_loaded"
    MODEL_UNLOADED = "model_unloaded"
    INFERENCE_RUN = "inference_run"
    ERROR = "error"
    WARNING = "warning"
    STATE_CHANGED = "state_changed"


@dataclass
class ContextEvent:
    """Record of a runtime event."""
    timestamp: str
    event_type: ContextEventType
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type.value,
            'message': self.message,
            'metadata': self.metadata,
        }


@dataclass
class AIMemory:
    """AI system memory and learning state."""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    learned_preferences: Dict[str, Any] = field(default_factory=dict)
    system_instructions: str = ""
    context_window_size: int = 8192
    memory_limit_entries: int = 1000
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'role': role,
            'content': content,
            'metadata': metadata or {}
        }
        self.conversation_history.append(entry)
        
        # Maintain size limit
        if len(self.conversation_history) > self.memory_limit_entries:
            # Keep recent messages, remove oldest
            self.conversation_history = self.conversation_history[-self.memory_limit_entries:]
    
    def get_recent_context(self, num_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent messages for context."""
        return self.conversation_history[-num_messages:] if self.conversation_history else []
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'conversation_history': self.conversation_history,
            'learned_preferences': self.learned_preferences,
            'system_instructions': self.system_instructions,
            'context_window_size': self.context_window_size,
        }


@dataclass
class ProjectConfig:
    """Project-specific configuration."""
    name: str
    description: str = ""
    version: str = "0.0.1"
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Model configuration
    default_model: str = "mistral:7b"
    model_size_preference: ModelSize = ModelSize.SMALL
    allow_model_downloads: bool = True
    max_model_size_gb: float = 20.0
    
    # Runtime configuration
    max_concurrent_requests: int = 4
    timeout_seconds: int = 300
    enable_caching: bool = True
    cache_size_mb: int = 512
    
    # Safety and compliance
    enable_safety_checks: bool = True
    enable_audit_logging: bool = True
    compliance_level: str = "standard"  # minimal, standard, strict
    
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['model_size_preference'] = self.model_size_preference.value
        return data


class RuntimeContext:
    """
    Central context manager for the Local AI Runtime.
    
    Manages:
    - Project state and configuration
    - Working directories
    - Hardware capabilities
    - AI memory and learning
    - Runtime events and logging
    - Resource tracking
    """
    
    def __init__(
        self,
        project_name: str = "DefaultProject",
        project_dir: Optional[Path] = None,
        mode: RuntimeMode = RuntimeMode.DEVELOPMENT,
    ):
        """
        Initialize runtime context.
        
        Args:
            project_name: Name of the project
            project_dir: Project root directory
            mode: Operating mode for the runtime
        """
        self.project_name = project_name
        self.mode = mode
        
        # Setup directories
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.working_dir = self.project_dir / "runtime"
        self.cache_dir = self.working_dir / "cache"
        self.logs_dir = self.working_dir / "logs"
        self.models_dir = self.working_dir / "models"
        self.memory_dir = self.working_dir / "memory"
        self.config_dir = self.working_dir / "config"
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Initialize state
        self.config = ProjectConfig(name=project_name)
        self.ai_memory = AIMemory()
        self.hardware_profile: Optional[HardwareProfile] = None
        self.model_recommendation: Optional[ModelRecommendation] = None
        
        # Runtime tracking
        self.startup_time: Optional[datetime] = None
        self.shutdown_time: Optional[datetime] = None
        self.is_running = False
        
        # Resource tracking
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self.active_requests: int = 0
        self.total_inference_runs: int = 0
        self.total_tokens_processed: int = 0
        
        # Event logging
        self.events: List[ContextEvent] = []
        self.max_events_memory = 1000
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Setup logging
        self._setup_logging()
        
        logger.info(f"RuntimeContext initialized for project: {project_name}")
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        for dir_path in [
            self.project_dir,
            self.working_dir,
            self.cache_dir,
            self.logs_dir,
            self.models_dir,
            self.memory_dir,
            self.config_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _setup_logging(self):
        """Setup logging for the context."""
        log_file = self.logs_dir / f"runtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    def startup(self, suggested_host: Optional[Path] = None, non_interactive: bool = False) -> bool:
        """
        Initialize and startup the runtime context.

        Prompts the user to confirm the host project root before any
        directories are created or state is written to disk.

        Args:
            suggested_host:  Path to suggest as the host project root.
                             Defaults to cwd if not provided.
            non_interactive: Skip prompting (for automated/test environments).

        Returns:
            bool: True if startup successful
        """
        with self._lock:
            try:
                # Confirm host project root before touching anything on disk
                from paths import initialize_host, ensure_host_dirs
                from paths import get_logs_dir, get_cache_dir, get_models_dir
                from paths import get_memory_dir, get_config_dir, get_sessions_dir

                host = initialize_host(
                    suggested=suggested_host,
                    non_interactive=non_interactive,
                )

                self.project_dir = host
                self.working_dir  = host / ".ai-runtime"
                self.cache_dir    = get_cache_dir()
                self.logs_dir     = get_logs_dir()
                self.models_dir   = get_models_dir()
                self.memory_dir   = get_memory_dir()
                self.config_dir   = get_config_dir()
                self.sessions_dir = get_sessions_dir()

                ensure_host_dirs()

                self.startup_time = datetime.now()
                self.is_running = True

                # Logging can only start after logs_dir exists
                self._setup_logging()

                # Detect hardware
                self._detect_hardware()

                # Load saved state if available
                self._load_saved_state()

                self.log_event(
                    ContextEventType.STARTUP,
                    "Runtime context started successfully",
                    {
                        'host_project': str(host),
                        'hardware': self.hardware_profile.primary_accelerator.value if self.hardware_profile else None,
                        'available_memory_gb': self.hardware_profile.available_for_models_gb if self.hardware_profile else 0,
                    }
                )

                logger.info("Runtime context startup complete")
                return True

            except RuntimeError as e:
                # Covers user cancellation and invalid paths
                logger.error(f"Startup aborted: {e}")
                print(f"\n✗ {e}")
                return False

            except Exception as e:
                logger.error(f"Error during startup: {e}")
                self.log_event(ContextEventType.ERROR, f"Startup error: {str(e)}")
                return False    
          
    def shutdown(self) -> bool:
        """
        Gracefully shutdown the runtime context.
        
        Returns:
            bool: True if shutdown successful
        """
        with self._lock:
            try:
                self.shutdown_time = datetime.now()
                self.is_running = False
                
                # Unload all models
                for model_name in list(self.loaded_models.keys()):
                    self.unload_model(model_name)
                
                # Save state
                self._save_state()
                
                # Log shutdown
                uptime_seconds = (self.shutdown_time - self.startup_time).total_seconds()
                self.log_event(
                    ContextEventType.SHUTDOWN,
                    "Runtime context shutdown",
                    {
                        'uptime_seconds': uptime_seconds,
                        'total_inference_runs': self.total_inference_runs,
                        'total_tokens_processed': self.total_tokens_processed,
                    }
                )
                
                logger.info("Runtime context shutdown complete")
                return True
                
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
                return False
    
    def _detect_hardware(self):
        """Detect system hardware."""
        try:
            detector = HardwareDetector()
            self.hardware_profile = detector.detect()
            
            recommender = ModelRecommender(self.hardware_profile)
            self.model_recommendation = recommender.recommend()
            
            logger.info(f"Hardware detected: {self.hardware_profile.primary_accelerator.value}")
            logger.info(f"Model recommendation: {self.model_recommendation.model_size.value}")
            
        except Exception as e:
            logger.warning(f"Hardware detection failed: {e}")
    
    def refresh_hardware(self) -> bool:
        """
        Re-run hardware detection and update the cached profile in-place.

        Should be called before any operation that needs current memory
        availability (e.g. status display, model load decisions).

        Returns:
            bool: True if refresh succeeded, False if detection failed.
        """
        with self._lock:
            previous = self.hardware_profile

            self._detect_hardware()

            if self.hardware_profile is None:
                self.hardware_profile = previous
                logger.warning("Hardware refresh failed — retaining previous profile")
                return False

            if previous is not None:
                logger.info(
                    f"Hardware refreshed — RAM available: "
                    f"{previous.ram_available_gb:.1f}GB → "
                    f"{self.hardware_profile.ram_available_gb:.1f}GB"
                )

            self.log_event(
                ContextEventType.STATE_CHANGED,
                "Hardware profile refreshed",
                {
                    "ram_available_gb": self.hardware_profile.ram_available_gb,
                    "total_vram_gb": self.hardware_profile.total_vram_gb,
                    "primary_accelerator": self.hardware_profile.primary_accelerator.value,
                }
            )

            return True

    def load_model(
        self,
        model_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a loaded model in the context.
        
        Args:
            model_name: Name/identifier of the model
            metadata: Optional metadata about the model
            
        Returns:
            bool: True if model loaded successfully
        """
        with self._lock:
            try:
                self.loaded_models[model_name] = {
                    'name': model_name,
                    'loaded_at': datetime.now().isoformat(),
                    'metadata': metadata or {},
                }
                
                self.log_event(
                    ContextEventType.MODEL_LOADED,
                    f"Model loaded: {model_name}",
                    {'model_name': model_name, 'metadata': metadata}
                )
                
                logger.info(f"Model registered: {model_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error loading model {model_name}: {e}")
                self.log_event(
                    ContextEventType.ERROR,
                    f"Error loading model {model_name}: {str(e)}"
                )
                return False
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from the context.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            bool: True if successful
        """
        with self._lock:
            if model_name in self.loaded_models:
                del self.loaded_models[model_name]
                
                self.log_event(
                    ContextEventType.MODEL_UNLOADED,
                    f"Model unloaded: {model_name}",
                    {'model_name': model_name}
                )
                
                logger.info(f"Model unloaded: {model_name}")
                return True
            return False
    
    def record_inference(
        self,
        model_name: str,
        tokens_processed: int,
        latency_ms: float,
        metadata: Optional[Dict] = None
    ):
        """
        Record an inference run.
        
        Args:
            model_name: Model used for inference
            tokens_processed: Number of tokens processed
            latency_ms: Latency in milliseconds
            metadata: Optional metadata
        """
        with self._lock:
            self.total_inference_runs += 1
            self.total_tokens_processed += tokens_processed
            
            self.log_event(
                ContextEventType.INFERENCE_RUN,
                f"Inference run completed: {model_name}",
                {
                    'model_name': model_name,
                    'tokens_processed': tokens_processed,
                    'latency_ms': latency_ms,
                    'metadata': metadata,
                }
            )
    
    def log_event(
        self,
        event_type: ContextEventType,
        message: str,
        metadata: Optional[Dict] = None
    ):
        """
        Log a runtime event.
        
        Args:
            event_type: Type of event
            message: Event message
            metadata: Optional metadata
        """
        with self._lock:
            event = ContextEvent(
                timestamp=datetime.now().isoformat(),
                event_type=event_type,
                message=message,
                metadata=metadata or {}
            )
            
            self.events.append(event)
            
            # Maintain size limit
            if len(self.events) > self.max_events_memory:
                self.events = self.events[-self.max_events_memory:]
    
    def update_ai_memory(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Update AI memory with new information.
        
        Args:
            role: Role (user, assistant, system)
            content: Message content
            metadata: Optional metadata
        """
        with self._lock:
            self.ai_memory.add_message(role, content, metadata)
    
    def get_ai_context(self, num_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent AI context for prompting."""
        with self._lock:
            return self.ai_memory.get_recent_context(num_messages)
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """
        Get all active sessions from session manager.

        Returns:
            Dict mapping session names to their status snapshots
        """
        from session import get_all_sessions

        sessions = get_all_sessions()
        result = {}

        for name, session in sessions.items():
            result[name] = {
                "name": name,
                "type": session.session_type,
                "running": session.is_running(),
                "pid": session.process.pid,
                "started": session.started_at.isoformat(),
                "metadata": session.metadata,
            }

        return result

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status including live session data."""
        with self._lock:
            uptime = None
            if self.startup_time:
                uptime = (datetime.now() - self.startup_time).total_seconds()

            return {
                'is_running': self.is_running,
                'mode': self.mode.value,
                'uptime_seconds': uptime,
                'active_sessions': self.get_active_sessions(),
                'loaded_models': list(self.loaded_models.keys()),
                'active_requests': self.active_requests,
                'total_inference_runs': self.total_inference_runs,
                'total_tokens_processed': self.total_tokens_processed,
                'hardware': self.hardware_profile.to_dict() if self.hardware_profile else None,
                'recommendation': asdict(self.model_recommendation) if self.model_recommendation else None,
            }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage."""
        if not self.hardware_profile:
            return {}
        
        with self._lock:
            return {
                'ram_total_gb': self.hardware_profile.ram_total_gb,
                'ram_available_gb': self.hardware_profile.ram_available_gb,
                'vram_total_gb': self.hardware_profile.total_vram_gb,
                'available_for_models_gb': self.hardware_profile.available_for_models_gb,
            }
    
    def _load_saved_state(self):
        """Load previously saved state from disk."""
        try:
            # Load config if exists
            config_file = self.config_dir / "config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    # Merge with defaults
                    logger.info(f"Loaded saved config from {config_file}")
            
            # Load AI memory if exists
            memory_file = self.memory_dir / "ai_memory.json"
            if memory_file.exists():
                with open(memory_file, 'r') as f:
                    memory_data = json.load(f)
                    # Restore memory
                    logger.info(f"Loaded saved AI memory from {memory_file}")
                    
        except Exception as e:
            logger.warning(f"Error loading saved state: {e}")
    
    def _save_state(self):
        """Save current state to disk."""
        try:
            # Save config
            config_file = self.config_dir / "config.json"
            with open(config_file, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            
            # Save AI memory
            memory_file = self.memory_dir / "ai_memory.json"
            with open(memory_file, 'w') as f:
                json.dump(self.ai_memory.to_dict(), f, indent=2)
            
            # Save events log
            events_file = self.logs_dir / "events.json"
            with open(events_file, 'w') as f:
                json.dump(
                    [event.to_dict() for event in self.events],
                    f,
                    indent=2
                )
            
            logger.info("Runtime state saved to disk")
            
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def export_state(self) -> Dict[str, Any]:
        """Export complete runtime state."""
        with self._lock:
            return {
                'project_name': self.project_name,
                'mode': self.mode.value,
                'config': self.config.to_dict(),
                'ai_memory': self.ai_memory.to_dict(),
                'hardware': self.hardware_profile.to_dict() if self.hardware_profile else None,
                'status': self.get_system_status(),
                'events': [event.to_dict() for event in self.events[-100:]],  # Last 100 events
            }


# Global context instance
_global_context: Optional[RuntimeContext] = None


def get_context() -> RuntimeContext:
    """Get the global runtime context."""
    global _global_context
    if _global_context is None:
        _global_context = RuntimeContext()
    return _global_context


def initialize_context(
    project_name: str = "DefaultProject",
    project_dir: Optional[Path] = None,
    mode: RuntimeMode = RuntimeMode.DEVELOPMENT,
) -> RuntimeContext:
    """Initialize and return the global runtime context."""
    global _global_context
    _global_context = RuntimeContext(project_name, project_dir, mode)
    return _global_context


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    print("\n" + "="*60)
    print("RUNTIME CONTEXT DEMO")
    print("="*60 + "\n")
    
    # Initialize context
    ctx = initialize_context(
        project_name="LocalAIDemo",
        project_dir=Path.cwd(),
        mode=RuntimeMode.DEVELOPMENT
    )
    
    # Startup
    if ctx.startup():
        print("✓ Context initialized successfully\n")
        
        # Load a model
        ctx.load_model("mistral:7b", metadata={'quantization': 'q4_k_m'})
        
        # Update AI memory
        ctx.update_ai_memory(
            "user",
            "Hello, what is your name?",
            metadata={'source': 'direct_input'}
        )
        ctx.update_ai_memory(
            "assistant",
            "I'm an AI assistant running locally.",
            metadata={'model': 'mistral:7b'}
        )
        
        # Record inference
        ctx.record_inference(
            "mistral:7b",
            tokens_processed=150,
            latency_ms=2500,
            metadata={'temperature': 0.7}
        )
        
        # Print status
        status = ctx.get_system_status()
        print("System Status:")
        print(f"  Running: {status['is_running']}")
        print(f"  Mode: {status['mode']}")
        print(f"  Loaded Models: {status['loaded_models']}")
        print(f"  Total Inference Runs: {status['total_inference_runs']}")
        
        # Print hardware
        print("\nHardware Summary:")
        hw = status['hardware']
        if hw:
            print(f"  CPU: {hw['cpu_brand']}")
            print(f"  RAM: {hw['ram_total_gb']:.1f} GB")
            print(f"  GPUs: {len(hw['gpus'])} detected")
            print(f"  Accelerator: {hw['primary_accelerator']}")
        
        # Export state
        state = ctx.export_state()
        print(f"\nState exported with {len(state['events'])} events logged")
        
        # Shutdown
        ctx.shutdown()
        print("\n✓ Context shutdown complete")
    else:
        print("✗ Failed to initialize context")