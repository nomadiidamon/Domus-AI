"""Domus runtime requirements expressed as Hestia dependencies."""

from Hestia.software.dependency import (
    DependencyRegistry, PythonPackageDependency, SystemCommandDependency, parse_first_version,
)


def build_registry() -> DependencyRegistry:
    registry = DependencyRegistry()
    registry.register_many([
        PythonPackageDependency("hestia-system", required=True, version_specifier=">=0.5.0"),
        PythonPackageDependency("platformdirs", required=True, version_specifier=">=3.0"),
        PythonPackageDependency("auctor-utils", required=True, version_specifier=">=0.2.1"),
        PythonPackageDependency("python-dotenv", required=True, version_specifier=">=1.0.0"),
        PythonPackageDependency("nvidia-ml-py", required=False, version_specifier=">=12.0.0"),
        PythonPackageDependency("mercurius-events", required=True, version_specifier=">=0.5.1"),
        SystemCommandDependency(
            "python", required=True, version_specifier=">=3.10",
            version_args=("--version",), version_parser=parse_first_version,
        ),
        SystemCommandDependency(
            "ollama", required=True,
            version_args=("--version",), version_parser=parse_first_version,
        ),
        SystemCommandDependency(
            "git", required=True,
            version_args=("--version",), version_parser=parse_first_version,
        ),
        SystemCommandDependency("claude", required=False),
    ])
    return registry