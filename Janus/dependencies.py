"""
dependencies.py - Dependency management and health checking system.

Provides a framework for checking, validating, and repairing system dependencies.
Designed to work with doctor.py for comprehensive system diagnostics.
"""

import os
import sys
import subprocess
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from datetime import datetime
import shutil
import platform
import json

logger = logging.getLogger(__name__)

class DependencyStatus(Enum):
    """Status of a dependency."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    MISSING = "missing"
    BROKEN = "broken"
    INCOMPATIBLE = "incompatible"

class DependencyType(Enum):
    """Types of dependencies."""
    PYTHON_PACKAGE = "python_package"
    SYSTEM_COMMAND = "system_command"
    SYSTEM_LIBRARY = "system_library"
    EXTERNAL_SERVICE = "external_service"
    DIRECTORY = "directory"
    FILE = "file"
    ENVIRONMENT_VAR = "environment_var"
    GPU_DRIVER = "gpu_driver"

@dataclass
class DependencyCheckResult:
    """Result of a dependency check."""
    name: str
    dep_type: DependencyType
    status: DependencyStatus
    version: Optional[str] = None
    expected_version: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def is_healthy(self) -> bool:
        """Check if dependency is healthy."""
        return self.status in (DependencyStatus.HEALTHY, DependencyStatus.DEGRADED)
    
    @property
    def is_critical(self) -> bool:
        """Check if dependency failure is critical."""
        return self.status in (DependencyStatus.MISSING, DependencyStatus.BROKEN)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['dep_type'] = self.dep_type.value
        data['status'] = self.status.value
        return data

class Dependency(ABC):
    """
    Base class for all dependencies.
    
    Subclasses implement specific dependency checking and repair logic.
    """
    
    def __init__(
        self,
        name: str,
        dep_type: DependencyType,
        required: bool = True,
        description: str = "",
    ):
        """
        Initialize dependency.
        
        Args:
            name: Dependency name
            dep_type: Type of dependency
            required: Whether this dependency is required
            description: Human-readable description
        """
        self.name = name
        self.dep_type = dep_type
        self.required = required
        self.description = description
        self.last_check: Optional[DependencyCheckResult] = None
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def check(self) -> DependencyCheckResult:
        """
        Check if dependency is available and healthy.
        
        Returns:
            DependencyCheckResult: Result of the check
        """
        pass
    
    @abstractmethod
    def repair(self) -> Tuple[bool, str]:
        """
        Attempt to repair/install the dependency.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        pass
    
    def get_install_instructions(self) -> str:
        """Get manual installation instructions."""
        return f"Please install {self.name} manually"
    
    def get_status(self, refresh: bool = False) -> DependencyCheckResult:
        """
        Get current status of dependency.
        
        Args:
            refresh: If True, perform a fresh check
            
        Returns:
            DependencyCheckResult: Current status
        """
        if refresh or self.last_check is None:
            self.last_check = self.check()
        return self.last_check

class PythonPackageDependency(Dependency):
    """Dependency for Python packages."""
    
    def __init__(
        self,
        package_name: str,
        import_name: Optional[str] = None,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None,
        required: bool = True,
        description: str = "",
    ):
        """
        Initialize Python package dependency.
        
        Args:
            package_name: Name of the package (as installed via pip)
            import_name: Import name (if different from package_name)
            min_version: Minimum required version
            max_version: Maximum allowed version
            required: Whether dependency is required
            description: Package description
        """
        super().__init__(
            name=package_name,
            dep_type=DependencyType.PYTHON_PACKAGE,
            required=required,
            description=description,
        )
        self.package_name = package_name
        self.import_name = import_name or package_name
        self.min_version = min_version
        self.max_version = max_version
    
    def check(self) -> DependencyCheckResult:
        """Check if Python package is installed."""
        try:
            # Try to import the package
            module = __import__(self.import_name)
            version = self._get_version(module)
            
            # Check version constraints
            status = DependencyStatus.HEALTHY
            message = f"Installed (version {version})"
            
            if self.min_version and not self._compare_version(version, self.min_version, ">="):
                status = DependencyStatus.INCOMPATIBLE
                message = f"Version {version} is below minimum required {self.min_version}"
            elif self.max_version and not self._compare_version(version, self.max_version, "<="):
                status = DependencyStatus.DEGRADED
                message = f"Version {version} exceeds maximum {self.max_version}"
            
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=status,
                version=version,
                expected_version=self.min_version,
                message=message,
            )
        
        except ImportError:
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=DependencyStatus.MISSING,
                message=f"Package '{self.package_name}' is not installed",
            )
        
        except Exception as e:
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=DependencyStatus.BROKEN,
                message=f"Error checking package: {str(e)}",
                details={'error': str(e)},
            )
    
    def repair(self) -> Tuple[bool, str]:
        """Install or repair Python package."""
        try:
            self.logger.info(f"Attempting to install {self.package_name}...")
            
            # Build pip install command
            cmd = [sys.executable, "-m", "pip", "install"]
            
            if self.min_version:
                cmd.append(f"{self.package_name}>={self.min_version}")
            elif self.max_version:
                cmd.append(f"{self.package_name}<={self.max_version}")
            else:
                cmd.append(self.package_name)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"Successfully installed {self.package_name}")
                return True, f"Installed {self.package_name}"
            else:
                error_msg = result.stderr or result.stdout
                self.logger.error(f"Installation failed: {error_msg}")
                return False, f"Installation failed: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return False, "Installation timeout"
        except Exception as e:
            return False, f"Installation error: {str(e)}"
    
    def get_install_instructions(self) -> str:
        """Get manual installation instructions."""
        if self.min_version:
            return f"pip install '{self.package_name}>={self.min_version}'"
        return f"pip install {self.package_name}"
    
    @staticmethod
    def _get_version(module) -> str:
        """Extract version from module."""
        for attr in ['__version__', 'VERSION', 'version']:
            if hasattr(module, attr):
                return str(getattr(module, attr))
        return "unknown"
    
    @staticmethod
    def _compare_version(version: str, constraint: str, op: str) -> bool:
        """Compare versions (simplified)."""
        try:
            from packaging import version as pkg_version
            
            v = pkg_version.parse(version)
            c = pkg_version.parse(constraint)
            
            if op == ">=":
                return v >= c
            elif op == "<=":
                return v <= c
            elif op == "==":
                return v == c
            elif op == ">":
                return v > c
            elif op == "<":
                return v < c
            return True
        except:
            # Fallback to string comparison if packaging not available
            return True

class SystemCommandDependency(Dependency):
    """Dependency for system commands."""
    
    def __init__(
        self,
        command_name: str,
        required: bool = True,
        description: str = "",
        version_flag: str = "--version",
    ):
        """
        Initialize system command dependency.
        
        Args:
            command_name: Name of the command
            required: Whether dependency is required
            description: Command description
            version_flag: Flag to get version info
        """
        super().__init__(
            name=command_name,
            dep_type=DependencyType.SYSTEM_COMMAND,
            required=required,
            description=description,
        )
        self.command_name = command_name
        self.version_flag = version_flag
    
    def check(self) -> DependencyCheckResult:
        """Check if system command is available."""
        try:
            # Try to find the command
            result = subprocess.run(
                [self.command_name, self.version_flag],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            version = None
            if result.returncode == 0:
                # Try to extract version from output
                version = result.stdout.strip().split('\n')[0]
            
            status = DependencyStatus.HEALTHY if result.returncode == 0 else DependencyStatus.DEGRADED
            
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=status,
                version=version,
                message=f"Command '{self.command_name}' is available",
            )
        
        except FileNotFoundError:
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=DependencyStatus.MISSING,
                message=f"Command '{self.command_name}' not found in PATH",
            )
        
        except subprocess.TimeoutExpired:
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=DependencyStatus.BROKEN,
                message=f"Command '{self.command_name}' timed out",
            )
        
        except Exception as e:
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=DependencyStatus.BROKEN,
                message=f"Error checking command: {str(e)}",
                details={'error': str(e)},
            )
    
    def repair(self) -> Tuple[bool, str]:
        """Repair system command (platform-specific)."""
        system = platform.system()
        
        if system == "Linux":
            return self._repair_linux()
        elif system == "Darwin":  # macOS
            return self._repair_macos()
        elif system == "Windows":
            return self._repair_windows()
        else:
            return False, f"Unsupported platform: {system}"
    
    def _repair_linux(self) -> Tuple[bool, str]:
        """Repair on Linux."""
        try:
            # Try apt-get first
            cmd = ["sudo", "apt-get", "install", "-y", self.command_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return True, f"Installed {self.command_name} via apt-get"
            
            # Try yum
            cmd = ["sudo", "yum", "install", "-y", self.command_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return True, f"Installed {self.command_name} via yum"
            
            return False, "Installation failed on Linux"
        
        except Exception as e:
            return False, f"Linux installation error: {str(e)}"
    
    def _repair_macos(self) -> Tuple[bool, str]:
        """Repair on macOS."""
        try:
            # Try brew
            cmd = ["brew", "install", self.command_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return True, f"Installed {self.command_name} via brew"
            
            return False, "Installation failed on macOS"
        
        except Exception as e:
            return False, f"macOS installation error: {str(e)}"
    
    def _repair_windows(self) -> Tuple[bool, str]:
        """Repair on Windows."""
        return False, "Automatic installation not supported on Windows. Please install manually."
    
    def get_install_instructions(self) -> str:
        """Get manual installation instructions."""
        system = platform.system()
        
        if system == "Linux":
            return f"sudo apt-get install {self.command_name}"
        elif system == "Darwin":
            return f"brew install {self.command_name}"
        elif system == "Windows":
            return f"Download and install {self.command_name} from official source"
        
        return f"Install {self.command_name} manually"

class DirectoryDependency(Dependency):
    """Dependency for directories."""
    
    def __init__(
        self,
        directory_path: Path,
        required: bool = True,
        description: str = "",
        create_if_missing: bool = True,
    ):
        """
        Initialize directory dependency.
        
        Args:
            directory_path: Path to directory
            required: Whether dependency is required
            description: Directory description
            create_if_missing: Whether to create directory if missing
        """
        super().__init__(
            name=str(directory_path),
            dep_type=DependencyType.DIRECTORY,
            required=required,
            description=description,
        )
        self.directory_path = Path(directory_path)
        self.create_if_missing = create_if_missing
    
    def check(self) -> DependencyCheckResult:
        """Check if directory exists."""
        exists = self.directory_path.exists() and self.directory_path.is_dir()
        
        status = DependencyStatus.HEALTHY if exists else DependencyStatus.MISSING
        message = f"Directory exists" if exists else f"Directory not found"
        
        return DependencyCheckResult(
            name=self.name,
            dep_type=self.dep_type,
            status=status,
            message=message,
            details={'path': str(self.directory_path), 'writable': os.access(self.directory_path, os.W_OK) if exists else False},
        )
    
    def repair(self) -> Tuple[bool, str]:
        """Create directory if missing."""
        if not self.create_if_missing:
            return False, "Directory creation disabled"
        
        try:
            self.directory_path.mkdir(parents=True, exist_ok=True)
            return True, f"Created directory: {self.directory_path}"
        except Exception as e:
            return False, f"Failed to create directory: {str(e)}"
    
    def get_install_instructions(self) -> str:
        """Get manual creation instructions."""
        return f"mkdir -p {self.directory_path}"

class EnvironmentVariableDependency(Dependency):
    """Dependency for environment variables."""
    
    def __init__(
        self,
        var_name: str,
        required: bool = True,
        description: str = "",
        expected_value: Optional[str] = None,
    ):
        """
        Initialize environment variable dependency.
        
        Args:
            var_name: Name of environment variable
            required: Whether dependency is required
            description: Variable description
            expected_value: Expected value (if specific value needed)
        """
        super().__init__(
            name=var_name,
            dep_type=DependencyType.ENVIRONMENT_VAR,
            required=required,
            description=description,
        )
        self.var_name = var_name
        self.expected_value = expected_value
    
    def check(self) -> DependencyCheckResult:
        """Check if environment variable is set."""
        value = os.environ.get(self.var_name)
        
        if value is None:
            return DependencyCheckResult(
                name=self.name,
                dep_type=self.dep_type,
                status=DependencyStatus.MISSING,
                message=f"Environment variable '{self.var_name}' not set",
            )
        
        status = DependencyStatus.HEALTHY
        message = f"Environment variable is set"
        
        if self.expected_value and value != self.expected_value:
            status = DependencyStatus.DEGRADED
            message = f"Expected '{self.expected_value}', got '{value}'"
        
        return DependencyCheckResult(
            name=self.name,
            dep_type=self.dep_type,
            status=status,
            version=value,
            message=message,
        )
    
    def repair(self) -> Tuple[bool, str]:
        """Cannot automatically repair environment variables."""
        return False, "Environment variables must be set manually"
    
    def get_install_instructions(self) -> str:
        """Get manual setup instructions."""
        if self.expected_value:
            return f"export {self.var_name}={self.expected_value}"
        return f"export {self.var_name}=<value>"

class DependencyChecker:
    """Checks the health of multiple dependencies."""
    
    def __init__(self):
        """Initialize dependency checker."""
        self.dependencies: Dict[str, Dependency] = {}
        self.check_results: Dict[str, DependencyCheckResult] = {}
        self.logger = logging.getLogger(__name__)
    
    def register(self, dependency: Dependency):
        """Register a dependency to check."""
        self.dependencies[dependency.name] = dependency
    
    def register_many(self, dependencies: List[Dependency]):
        """Register multiple dependencies."""
        for dep in dependencies:
            self.register(dep)
    
    def check_all(self, skip_optional: bool = False) -> Dict[str, DependencyCheckResult]:
        """
        Check all registered dependencies.
        
        Args:
            skip_optional: Whether to skip non-required dependencies
            
        Returns:
            Dict mapping dependency names to check results
        """
        self.check_results = {}
        
        for name, dep in self.dependencies.items():
            if skip_optional and not dep.required:
                continue
            
            try:
                result = dep.check()
                self.check_results[name] = result
                
                status_icon = "✓" if result.is_healthy else "✗"
                self.logger.info(f"{status_icon} {name}: {result.message}")
            
            except Exception as e:
                self.logger.error(f"Error checking {name}: {e}")
                self.check_results[name] = DependencyCheckResult(
                    name=name,
                    dep_type=dep.dep_type,
                    status=DependencyStatus.BROKEN,
                    message=f"Check failed: {str(e)}",
                )
        
        return self.check_results
    
    def repair_failures(self, auto_repair: bool = True) -> Dict[str, Tuple[bool, str]]:
        """
        Attempt to repair failed dependencies.
        
        Args:
            auto_repair: Whether to automatically repair
            
        Returns:
            Dict mapping dependency names to (success, message) tuples
        """
        results = {}
        
        for name, result in self.check_results.items():
            if result.is_healthy:
                continue
            
            dep = self.dependencies[name]
            
            if not auto_repair:
                results[name] = (False, "Auto-repair disabled")
                continue
            
            try:
                self.logger.info(f"Attempting to repair {name}...")
                success, message = dep.repair()
                results[name] = (success, message)
                
                if success:
                    self.logger.info(f"✓ Repaired {name}")
                else:
                    self.logger.warning(f"✗ Could not repair {name}: {message}")
            
            except Exception as e:
                results[name] = (False, f"Repair failed: {str(e)}")
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of dependency status."""
        total = len(self.check_results)
        healthy = sum(1 for r in self.check_results.values() if r.is_healthy)
        missing = sum(1 for r in self.check_results.values() if r.status == DependencyStatus.MISSING)
        broken = sum(1 for r in self.check_results.values() if r.status == DependencyStatus.BROKEN)
        
        return {
            'total': total,
            'healthy': healthy,
            'degraded': total - healthy - missing - broken,
            'missing': missing,
            'broken': broken,
            'percentage_healthy': (healthy / total * 100) if total > 0 else 0,
        }
    
    def export_report(self) -> Dict[str, Any]:
        """Export complete dependency report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_summary(),
            'dependencies': {
                name: result.to_dict()
                for name, result in self.check_results.items()
            },
        }


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    print("\n" + "="*60)
    print("DEPENDENCY CHECKER DEMO")
    print("="*60 + "\n")
    
    checker = DependencyChecker()
    
    # Register dependencies
    checker.register(PythonPackageDependency("psutil", required=True))
    checker.register(PythonPackageDependency("requests", min_version="2.25.0", required=True))
    checker.register(SystemCommandDependency("python", required=True))
    checker.register(PythonPackageDependency("python-dotenv", min_version="1.0.0", required=True))
    checker.register(SystemCommandDependency("git", required=False))
    checker.register(DirectoryDependency(Path.home() / ".cache" / "ai-runtime", create_if_missing=True))
    checker.register(EnvironmentVariableDependency("PATH", required=True))

    # Check all dependencies
    print("Checking dependencies...\n")
    results = checker.check_all()
    
    # Print results
    print("\nDependency Results:")
    for name, result in results.items():
        status_icon = "✓" if result.is_healthy else "✗"
        print(f"  {status_icon} {name}: {result.message}")
        if result.version:
            print(f"      Version: {result.version}")
    
    # Print summary
    summary = checker.get_summary()
    print(f"\nSummary:")
    print(f"  Total: {summary['total']}")
    print(f"  Healthy: {summary['healthy']}")
    print(f"  Degraded: {summary['degraded']}")
    print(f"  Missing: {summary['missing']}")
    print(f"  Broken: {summary['broken']}")
    print(f"  Health: {summary['percentage_healthy']:.1f}%")