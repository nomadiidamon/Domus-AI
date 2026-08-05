# Monitors the hardware type and logs usage statistics
# psutil is a cross-platform library for retrieving information on running processes and system utilization (CPU, memory, disks, network, sensors) in Python.
# pynvml is a Python binding for the NVIDIA Management Library (NVML), which allows you to query GPU information and monitor GPU usage.
# Other gpu libraries can be used to monitor GPU usage for non-NVIDIA GPUs.

"""
hardware.py - Detect and profile system hardware capabilities for AI model optimization.

Gathers insights on CPU, RAM, GPU, VRAM, and recommends models based on available resources.
"""

import os
import sys
import platform
import psutil
import subprocess
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class AcceleratorType(Enum):
    """Supported hardware accelerators."""
    NONE = "none"
    NVIDIA_CUDA = "nvidia_cuda"
    NVIDIA_MPS = "nvidia_mps"
    AMD_ROCM = "amd_rocm"
    INTEL_ONEAPI = "intel_oneapi"
    APPLE_METAL = "apple_metal"
    QUALCOMM_HEXAGON = "qualcomm_hexagon"


class ModelSize(Enum):
    """Model size categories based on parameter count."""
    TINY = "tiny"  # <1B parameters
    SMALL = "small"  # 1-7B parameters
    MEDIUM = "medium"  # 7-13B parameters
    LARGE = "large"  # 13-40B parameters
    XLARGE = "xlarge"  # 40B+ parameters


@dataclass
class GPUInfo:
    """GPU capability information."""
    index: int
    name: str
    accelerator: AcceleratorType
    total_memory_gb: float
    free_memory_gb: float
    compute_capability: Optional[str] = None
    driver_version: Optional[str] = None
    is_available: bool = True


@dataclass
class HardwareProfile:
    """Complete hardware profile of the system."""
    cpu_count: int
    cpu_cores_physical: int
    cpu_cores_logical: int
    cpu_frequency_ghz: float
    cpu_brand: str
    
    ram_total_gb: float
    ram_available_gb: float
    
    gpus: List[GPUInfo]
    total_vram_gb: float
    
    platform_name: str
    platform_version: str
    python_version: str
    
    primary_accelerator: AcceleratorType
    
    # Computed properties
    available_for_models_gb: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['gpus'] = [asdict(gpu) for gpu in self.gpus]
        data['primary_accelerator'] = self.primary_accelerator.value
        return data


@dataclass
class ModelRecommendation:
    """
    Recommended model configuration for the detected hardware.

    recommended_models: Best general-purpose models for this tier.
    thinking_models:    Models with chain-of-thought / extended reasoning.
    tool_models:        Models with native function/tool-call support.
    """
    model_size: ModelSize
    recommended_models: List[str]
    thinking_models: List[str]
    tool_models: List[str]
    max_context_tokens: int
    quantization_level: str
    batch_size: int
    estimated_performance: str
    reasoning: str


class HardwareDetector:
    """Detect and analyze system hardware capabilities."""
    
    def __init__(self):
        """Initialize hardware detector."""
        self.profile: Optional[HardwareProfile] = None
        self.logger = logging.getLogger(__name__)
    
    def detect(self) -> HardwareProfile:
        """
        Perform complete hardware detection.
        
        Returns:
            HardwareProfile: Complete system hardware information
        """
        self.logger.info("Starting hardware detection...")
        
        cpu_count = os.cpu_count() or 1
        cpu_info = self._detect_cpu()
        ram_info = self._detect_ram()
        gpus = self._detect_gpus()
        total_vram = sum(gpu.total_memory_gb for gpu in gpus)
        platform_info = self._detect_platform()
        primary_accelerator = self._determine_primary_accelerator(gpus)
        
        # Calculate available memory for models
        # Conservative estimate: use 70% of available RAM to leave headroom
        available_for_models = ram_info['available'] * 0.7
        if gpus:
            # Use smallest GPU's free memory as constraint
            gpu_available = min(gpu.free_memory_gb for gpu in gpus)
            available_for_models = min(available_for_models, gpu_available * 0.8)
        
        profile = HardwareProfile(
            cpu_count=cpu_count,
            cpu_cores_physical=cpu_info['physical_cores'],
            cpu_cores_logical=cpu_info['logical_cores'],
            cpu_frequency_ghz=cpu_info['frequency_ghz'],
            cpu_brand=cpu_info['brand'],
            
            ram_total_gb=ram_info['total'],
            ram_available_gb=ram_info['available'],
            
            gpus=gpus,
            total_vram_gb=total_vram,
            
            platform_name=platform_info['name'],
            platform_version=platform_info['version'],
            python_version=platform_info['python_version'],
            
            primary_accelerator=primary_accelerator,
            available_for_models_gb=available_for_models,
        )
        
        self.profile = profile
        self.logger.info(f"Hardware detection complete: {profile.primary_accelerator.value}")
        
        return profile
    
    def _detect_cpu(self) -> Dict[str, any]:
        """Detect CPU information."""
        try:
            physical_cores = psutil.cpu_count(logical=False) or 1
            logical_cores = psutil.cpu_count(logical=True) or 1
            frequency_ghz = psutil.cpu_freq().current / 1000.0 if psutil.cpu_freq() else 0.0
            
            # Detect CPU brand
            brand = self._detect_cpu_brand()
            
            return {
                'physical_cores': physical_cores,
                'logical_cores': logical_cores,
                'frequency_ghz': frequency_ghz,
                'brand': brand,
            }
        except Exception as e:
            self.logger.warning(f"Error detecting CPU: {e}")
            return {
                'physical_cores': 1,
                'logical_cores': 1,
                'frequency_ghz': 0.0,
                'brand': 'Unknown',
            }
    
    def _detect_cpu_brand(self) -> str:
        """Detect CPU brand/model."""
        system = platform.system()
        
        try:
            if system == "Windows":
                cmd = "wmic cpu get name"
                output = subprocess.check_output(cmd, shell=True, text=True)
                lines = output.strip().split('\n')
                return lines[1].strip() if len(lines) > 1 else "Unknown"
            elif system == "Darwin":  # macOS
                cmd = "sysctl -n machdep.cpu.brand_string"
                output = subprocess.check_output(cmd, shell=True, text=True)
                return output.strip()
            elif system == "Linux":
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if line.startswith('model name'):
                                return line.split(':', 1)[1].strip()
                except:
                    pass
                return "Unknown"
        except Exception as e:
            self.logger.debug(f"Could not detect CPU brand: {e}")
        
        return "Unknown"
    
    def _detect_ram(self) -> Dict[str, float]:
        """Detect system RAM."""
        try:
            memory = psutil.virtual_memory()
            return {
                'total': memory.total / (1024**3),  # Convert to GB
                'available': memory.available / (1024**3),
            }
        except Exception as e:
            self.logger.warning(f"Error detecting RAM: {e}")
            return {'total': 0.0, 'available': 0.0}
    
    def _detect_gpus(self) -> List[GPUInfo]:
        """
        Attempt detection of all GPU types.
        Each detector is fully independent — failure in one does not affect others.
        """
        gpus = []
        gpus.extend(self._detect_nvidia_gpus())
        gpus.extend(self._detect_amd_gpus())
        gpus.extend(self._detect_intel_gpus())
        gpus.extend(self._detect_apple_gpus())
        return gpus
    
    # ------------------------------------------------------------------
    # NVIDIA — via pynvml (pip install pynvml)
    # Requires only the NVIDIA driver, not the full CUDA toolkit.
    # ------------------------------------------------------------------
    def _detect_nvidia_gpus(self) -> List[GPUInfo]:
        """
        Detect NVIDIA GPUs via pynvml.

        pynvml wraps NVML which is bundled with the NVIDIA display driver.
        No CUDA toolkit or torch installation required.
        """
        gpus = []
        try:
            import pynvml

            pynvml.nvmlInit()
            driver_version = pynvml.nvmlSystemGetDriverVersion()
            device_count = pynvml.nvmlDeviceGetCount()

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

                total_gb = mem_info.total / (1024 ** 3)
                free_gb = mem_info.free / (1024 ** 3)

                # Compute capability via CUDA device attributes
                try:
                    major = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
                    compute = f"{major[0]}.{major[1]}"
                except Exception:
                    compute = None

                gpus.append(GPUInfo(
                    index=i,
                    name=name,
                    accelerator=AcceleratorType.NVIDIA_CUDA,
                    total_memory_gb=total_gb,
                    free_memory_gb=free_gb,
                    compute_capability=compute,
                    driver_version=driver_version,
                ))
                self.logger.info(f"Detected NVIDIA GPU {i}: {name} ({total_gb:.1f}GB)")

            pynvml.nvmlShutdown()

        except ImportError:
            self.logger.debug("pynvml not installed — skipping NVIDIA detection")
        except Exception as e:
            self.logger.debug(f"NVIDIA GPU detection failed: {e}")

        return gpus
    
    # ------------------------------------------------------------------
    # AMD — via rocm-smi system tool (installed with ROCm driver)
    # No pip package required.
    # ------------------------------------------------------------------
    def _detect_amd_gpus(self) -> List[GPUInfo]:
        """
        Detect AMD GPUs via rocm-smi.

        rocm-smi is installed alongside the AMD ROCm driver.
        No pip package required — if ROCm is present, the tool is present.
        """
        gpus = []
        try:
            result = subprocess.run(
                ['rocm-smi', '--showmeminfo', 'vram', '--json'],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return gpus

            data = json.loads(result.stdout)

            # rocm-smi JSON: {"card0": {"VRAM Total Memory (B)": "...", "VRAM Total Used Memory (B)": "..."}}
            for i, (card_key, card_data) in enumerate(data.items()):
                if not isinstance(card_data, dict):
                    continue

                total_bytes = int(card_data.get("VRAM Total Memory (B)", 0))
                used_bytes = int(card_data.get("VRAM Total Used Memory (B)", 0))
                total_gb = total_bytes / (1024 ** 3)
                free_gb = (total_bytes - used_bytes) / (1024 ** 3)

                # Get GPU name separately
                name = self._get_amd_gpu_name(i) or f"AMD GPU {i}"

                gpus.append(GPUInfo(
                    index=i,
                    name=name,
                    accelerator=AcceleratorType.AMD_ROCM,
                    total_memory_gb=total_gb,
                    free_memory_gb=free_gb,
                ))
                self.logger.info(f"Detected AMD GPU {i}: {name} ({total_gb:.1f}GB)")

        except FileNotFoundError:
            self.logger.debug("rocm-smi not found — skipping AMD detection")
        except Exception as e:
            self.logger.debug(f"AMD GPU detection failed: {e}")

        return gpus

    def _get_amd_gpu_name(self, index: int) -> Optional[str]:
        """Retrieve the name of an AMD GPU by index via rocm-smi."""
        try:
            result = subprocess.run(
                ['rocm-smi', '--showproductname', '--json'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                card_key = f"card{index}"
                card = data.get(card_key, {})
                return card.get("Card Series") or card.get("Card model") or None
        except Exception:
            pass
        return None
    
    # ------------------------------------------------------------------
    # Intel — via platform-native system tools
    # Windows: wmic / PowerShell   Linux: /sys/class/drm + lspci
    # No pip package required.
    # ------------------------------------------------------------------
    def _detect_intel_gpus(self) -> List[GPUInfo]:
        """
        Detect Intel GPUs using platform-native system tools.

        Windows: PowerShell Get-WmiObject Win32_VideoController
        Linux:   /sys/class/drm device enumeration + lspci

        No pip package required.
        """
        system = platform.system()

        if system == "Windows":
            return self._detect_intel_gpus_windows()
        elif system == "Linux":
            return self._detect_intel_gpus_linux()

        return []

    def _detect_intel_gpus_windows(self) -> List[GPUInfo]:
        """Detect Intel GPUs on Windows via PowerShell WMI."""
        gpus = []
        try:
            ps_cmd = (
                'Get-WmiObject Win32_VideoController | '
                'Where-Object { $_.Name -like "*Intel*" } | '
                'Select-Object Name, AdapterRAM, DriverVersion | '
                'ConvertTo-Json'
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return gpus

            raw = json.loads(result.stdout)

            # PowerShell returns a dict when there is one result, list when multiple
            if isinstance(raw, dict):
                raw = [raw]

            for i, entry in enumerate(raw):
                name = entry.get("Name", f"Intel GPU {i}")
                adapter_ram = entry.get("AdapterRAM") or 0
                total_gb = int(adapter_ram) / (1024 ** 3)
                driver = entry.get("DriverVersion")

                gpus.append(GPUInfo(
                    index=i,
                    name=name,
                    accelerator=AcceleratorType.INTEL_ONEAPI,
                    total_memory_gb=total_gb,
                    free_memory_gb=0.0,  # WMI does not expose free VRAM
                    driver_version=driver,
                ))
                self.logger.info(f"Detected Intel GPU {i}: {name} ({total_gb:.1f}GB)")

        except FileNotFoundError:
            self.logger.debug("PowerShell not found — skipping Intel GPU detection")
        except Exception as e:
            self.logger.debug(f"Intel GPU detection (Windows) failed: {e}")

        return gpus

    def _detect_intel_gpus_linux(self) -> List[GPUInfo]:
        """Detect Intel GPUs on Linux via /sys/class/drm and lspci."""
        gpus = []
        try:
            drm_path = Path("/sys/class/drm")
            if not drm_path.exists():
                return gpus

            index = 0
            for card in sorted(drm_path.iterdir()):
                # Only top-level card entries, not render nodes
                if not card.name.startswith("card") or card.name.count('-') > 0:
                    continue

                vendor_path = card / "device" / "vendor"
                if not vendor_path.exists():
                    continue

                vendor_id = vendor_path.read_text().strip()

                # Intel vendor ID is 0x8086
                if vendor_id != "0x8086":
                    continue

                name = self._read_sys_file(card / "device" / "product_name") or "Intel GPU"
                driver = self._read_sys_file(card / "device" / "driver" / "module" / "version")

                # LMEM (local memory) size is exposed for Intel Arc/Xe discrete GPUs
                lmem_path = card / "device" / "drm" / card.name / "lmem_total_bytes"
                total_gb = 0.0
                if lmem_path.exists():
                    try:
                        total_gb = int(lmem_path.read_text().strip()) / (1024 ** 3)
                    except ValueError:
                        pass

                gpus.append(GPUInfo(
                    index=index,
                    name=name,
                    accelerator=AcceleratorType.INTEL_ONEAPI,
                    total_memory_gb=total_gb,
                    free_memory_gb=0.0,  # Not exposed via sysfs without i915 debugfs
                    driver_version=driver,
                ))
                self.logger.info(f"Detected Intel GPU {index}: {name} ({total_gb:.1f}GB)")
                index += 1

        except Exception as e:
            self.logger.debug(f"Intel GPU detection (Linux) failed: {e}")

        return gpus

    def _read_sys_file(self, path: Path) -> Optional[str]:
        """Safely read a sysfs file, returning None on any error."""
        try:
            return path.read_text().strip() if path.exists() else None
        except Exception:
            return None    

    # ------------------------------------------------------------------
    # Apple — via system_profiler (macOS built-in)
    # No pip package required.
    # ------------------------------------------------------------------
    def _detect_apple_gpus(self) -> List[GPUInfo]:
        """
        Detect Apple GPU via system_profiler SPDisplaysDataType.

        system_profiler is a macOS built-in tool — no pip package required.
        Returns real VRAM figures for both discrete and Apple Silicon GPUs.
        """
        gpus = []
        if platform.system() != "Darwin":
            return gpus

        try:
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return gpus

            data = json.loads(result.stdout)
            displays = data.get("SPDisplaysDataType", [])

            for i, display in enumerate(displays):
                name = display.get("sppci_model", f"Apple GPU {i}")

                # VRAM is reported as e.g. "1536 MB" or "16 GB"
                vram_raw = display.get("spdisplays_vram") or display.get("spdisplays_vram_shared", "0 MB")
                total_gb = self._parse_apple_vram(vram_raw)

                gpus.append(GPUInfo(
                    index=i,
                    name=name,
                    accelerator=AcceleratorType.APPLE_METAL,
                    total_memory_gb=total_gb,
                    free_memory_gb=0.0,  # macOS does not expose free GPU memory via system_profiler
                    driver_version=display.get("spdisplays_metal"),
                ))
                self.logger.info(f"Detected Apple GPU {i}: {name} ({total_gb:.1f}GB)")

        except FileNotFoundError:
            self.logger.debug("system_profiler not found — skipping Apple GPU detection")
        except Exception as e:
            self.logger.debug(f"Apple GPU detection failed: {e}")

        return gpus

    def _parse_apple_vram(self, vram_str: str) -> float:
        """Parse Apple VRAM string ('1536 MB', '8 GB') into GB float."""
        try:
            parts = vram_str.strip().split()
            value = float(parts[0])
            unit = parts[1].upper() if len(parts) > 1 else "MB"
            return value / 1024.0 if unit == "MB" else value
        except Exception:
            return 0.0
    
    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _determine_primary_accelerator(self, gpus: List[GPUInfo]) -> AcceleratorType:
        """Determine the highest-priority accelerator present."""
        if not gpus:
            return AcceleratorType.NONE

        priority = {
            AcceleratorType.NVIDIA_CUDA: 5,
            AcceleratorType.AMD_ROCM:    4,
            AcceleratorType.INTEL_ONEAPI: 3,
            AcceleratorType.APPLE_METAL: 2,
        }

        return max(gpus, key=lambda g: priority.get(g.accelerator, 0)).accelerator    

    def _detect_platform(self) -> Dict[str, str]:
        """Detect platform information."""
        return {
            'name': platform.system(),
            'version': platform.release(),
            'python_version': platform.python_version(),
        }
    
    def get_profile(self) -> Optional[HardwareProfile]:
        """Get current hardware profile."""
        return self.profile


class ModelRecommender:
    """
    Recommend models based on hardware capabilities.
    Model data lives in model_catalog.py — add new categories there.
    """
    
    def __init__(self, profile: HardwareProfile):
        """Initialize recommender with hardware profile."""
        self.profile = profile
        self.logger = logging.getLogger(__name__)
    
    def recommend(self) -> ModelRecommendation:
        """Recommend a model configuration based on available hardware."""
        
        from model_catalog import get_tier, get_category

        model_size = self._determine_model_size()
        accelerator = self.profile.primary_accelerator
        tier = get_tier(accelerator, model_size)

        db = self.MODEL_DATABASE.get(accelerator, {})
        rec_data = db.get(model_size)

        return ModelRecommendation(
            model_size=model_size,
            recommended_models=get_category(tier, 'models'),
            thinking_models=get_category(tier, 'thinking'),
            tool_models=get_category(tier, 'tools'),
            vision_models=get_category(tier, 'vision'),
            max_context_tokens=tier.get('context', 4096),
            quantization_level=tier.get('quantization', 'q4_k_m'),
            batch_size=tier.get('batch_size', 1),
            estimated_performance=tier.get('performance', 'Unknown'),
            reasoning=self._generate_reasoning(model_size, accelerator),
        )
    
    def _determine_model_size(self) -> ModelSize:
        """Determine appropriate model size based on available memory."""
        available_gb = self.profile.available_for_models_gb
        
        # Decision tree based on available memory
        if available_gb < 2:
            return ModelSize.TINY
        elif available_gb < 4:
            return ModelSize.SMALL
        elif available_gb < 12:
            return ModelSize.MEDIUM
        elif available_gb < 40:
            return ModelSize.LARGE
        else:
            return ModelSize.XLARGE
    
    def _generate_reasoning(self, model_size: ModelSize, accelerator: AcceleratorType) -> str:
        """Generate human-readable reasoning for recommendation."""
        reasons = [
            f"Available memory: {self.profile.available_for_models_gb:.1f}GB",
            f"Accelerator: {accelerator.value}",
            f"CPU cores: {self.profile.cpu_cores_physical} physical, {self.profile.cpu_cores_logical} logical",
        ]
        
        if self.profile.gpus:
            vram_str = ", ".join([f"{gpu.name} ({gpu.total_memory_gb:.1f}GB)" for gpu in self.profile.gpus])
            reasons.append(f"GPUs: {vram_str}")
        
        return " | ".join(reasons)


# Convenience functions
def detect_hardware() -> HardwareProfile:
    """Detect system hardware."""
    detector = HardwareDetector()
    return detector.detect()


def recommend_model(profile: HardwareProfile) -> ModelRecommendation:
    """Get model recommendation for hardware."""
    recommender = ModelRecommender(profile)
    return recommender.recommend()


def get_system_summary() -> Dict[str, any]:
    """Get summary of system capabilities and recommendations."""
    profile = detect_hardware()
    recommendation = recommend_model(profile)
    
    return {
        'hardware': profile.to_dict(),
        'recommendation': asdict(recommendation) if recommendation else None,
    }


def print_hardware_report(profile: HardwareProfile, recommendation: Optional[ModelRecommendation] = None) -> None:
    """
    Print a formatted hardware and recommendation report to stdout.

    Args:
        profile:        The hardware profile to display.
        recommendation: Optional model recommendation to display beneath hardware info.
    """
    print("\n" + "=" * 50)
    print("💻 Hardware")
    print("=" * 50)

    print(f"CPU:       {profile.cpu_brand}")
    print(f"Cores:     {profile.cpu_cores_physical} physical / {profile.cpu_cores_logical} logical")
    print(f"Frequency: {profile.cpu_frequency_ghz:.2f} GHz")

    print(f"\nRAM:       {profile.ram_total_gb:.1f} GB total  |  {profile.ram_available_gb:.1f} GB available")

    if profile.gpus:
        print(f"\nGPUs ({len(profile.gpus)} detected):")
        for gpu in profile.gpus:
            print(f"  [{gpu.index}] {gpu.name}")
            print(f"       Type:   {gpu.accelerator.value}")
            print(f"       VRAM:   {gpu.total_memory_gb:.1f} GB total  |  {gpu.free_memory_gb:.1f} GB free")
            if gpu.compute_capability:
                print(f"       Compute: {gpu.compute_capability}")
            if gpu.driver_version:
                print(f"       Driver:  {gpu.driver_version}")
    else:
        print("\nGPU:       None detected — CPU only")

    print(f"\nPlatform:  {profile.platform_name} {profile.platform_version}")
    print(f"Python:    {profile.python_version}")
    print(f"Accelerator: {profile.primary_accelerator.value}")
    print(f"Available for models: {profile.available_for_models_gb:.1f} GB")

    if recommendation is not None:
        print("\n" + "=" * 50)
        print("🤖 Model Recommendation")
        print("=" * 50)
        print(f"Tier:         {recommendation.model_size.value}")
        print(f"Quantization: {recommendation.quantization_level}")
        print(f"Batch size:   {recommendation.batch_size}")
        print(f"Max context:  {recommendation.max_context_tokens:,} tokens")
        print(f"Performance:  {recommendation.estimated_performance}")
        print(f"\nGeneral:      {', '.join(recommendation.recommended_models)}")
        if recommendation.thinking_models:
            print(f"Thinking:     {', '.join(recommendation.thinking_models)}")
        if recommendation.tool_models:
            print(f"Tool use:     {', '.join(recommendation.tool_models)}")
        print(f"\nReasoning:    {recommendation.reasoning}")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Detect and print hardware info
    print("\n" + "="*60)
    print("SYSTEM HARDWARE DETECTION")
    print("="*60 + "\n")
    
    profile = detect_hardware()
    recommendation = recommend_model(profile)
    print_hardware_report(profile, recommendation)