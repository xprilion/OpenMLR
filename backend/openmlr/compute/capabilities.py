"""Compute capability discovery and planning."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GPUInfo:
    """Information about a GPU."""

    model: str = ""
    vram_gb: float = 0.0
    cuda_version: str = ""
    driver_version: str = ""


@dataclass
class ComputeCapabilities:
    """Comprehensive capabilities of a compute node."""

    # Platform
    platform: str = "unknown"
    cpu_cores: int = 0
    cpu_arch: str = "unknown"

    # Memory
    total_ram_gb: float = 0.0
    available_ram_gb: float = 0.0

    # Storage
    total_disk_gb: float = 0.0
    available_disk_gb: float = 0.0

    # GPU
    gpu_available: bool = False
    gpu_count: int = 0
    gpu_info: list[GPUInfo] = field(default_factory=list)

    # Software
    python_versions: list[str] = field(default_factory=list)
    docker_available: bool = False
    conda_envs: list[str] = field(default_factory=list)
    installed_packages: list[str] = field(default_factory=list)

    # Network
    has_internet: bool = True
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "platform": self.platform,
            "cpu_cores": self.cpu_cores,
            "cpu_arch": self.cpu_arch,
            "total_ram_gb": self.total_ram_gb,
            "available_ram_gb": self.available_ram_gb,
            "total_disk_gb": self.total_disk_gb,
            "available_disk_gb": self.available_disk_gb,
            "gpu_available": self.gpu_available,
            "gpu_count": self.gpu_count,
            "gpu_info": [
                {
                    "model": g.model,
                    "vram_gb": g.vram_gb,
                    "cuda_version": g.cuda_version,
                    "driver_version": g.driver_version,
                }
                for g in self.gpu_info
            ],
            "python_versions": self.python_versions,
            "docker_available": self.docker_available,
            "conda_envs": self.conda_envs,
            "installed_packages": self.installed_packages,
            "has_internet": self.has_internet,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ComputeCapabilities":
        """Deserialize from dict."""
        caps = cls()
        for key, value in data.items():
            if key == "gpu_info" and value:
                caps.gpu_info = [GPUInfo(**g) for g in value]
            elif hasattr(caps, key):
                setattr(caps, key, value)
        return caps
