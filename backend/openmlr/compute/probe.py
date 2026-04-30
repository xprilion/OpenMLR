"""Environment probing for all sandbox types."""

import time

from .capabilities import ComputeCapabilities, GPUInfo


async def probe_sandbox(sandbox) -> ComputeCapabilities:
    """Deep capability discovery for any sandbox implementation."""
    caps = ComputeCapabilities()
    start = time.monotonic()

    # Platform
    result = await sandbox.execute("uname -s -r 2>/dev/null || echo 'unknown'", timeout=5)
    if result.success:
        caps.platform = result.output.strip()

    # CPU cores and architecture
    result = await sandbox.execute(
        "nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo '0'", timeout=5
    )
    if result.success:
        try:
            caps.cpu_cores = int(result.output.strip())
        except ValueError:
            pass

    result = await sandbox.execute("uname -m 2>/dev/null || echo 'unknown'", timeout=5)
    if result.success:
        caps.cpu_arch = result.output.strip()

    # RAM (Linux)
    result = await sandbox.execute(
        "free -g 2>/dev/null | grep Mem | awk '{print $2, $7}' || echo '0 0'",
        timeout=5,
    )
    if result.success:
        parts = result.output.strip().split()
        if len(parts) >= 2:
            try:
                caps.total_ram_gb = float(parts[0])
                caps.available_ram_gb = float(parts[1])
            except ValueError:
                pass

    # Disk
    result = await sandbox.execute(
        "df -BG / 2>/dev/null | tail -1 | awk '{print $2, $4}' || echo '0 0'",
        timeout=5,
    )
    if result.success:
        parts = result.output.strip().split()
        if len(parts) >= 2:
            try:
                caps.total_disk_gb = float(parts[0].replace("G", ""))
                caps.available_disk_gb = float(parts[1].replace("G", ""))
            except ValueError:
                pass

    # GPU — query model, memory, driver; then get CUDA version separately
    result = await sandbox.execute(
        "nvidia-smi --query-gpu=name,memory.total,driver_version "
        "--format=csv,noheader 2>/dev/null || echo ''",
        timeout=10,
    )
    if result.success and result.output.strip():
        lines = [ln.strip() for ln in result.output.strip().split("\n") if ln.strip()]
        caps.gpu_count = len(lines)
        caps.gpu_available = caps.gpu_count > 0

        # Get CUDA toolkit version
        cuda_ver = ""
        cuda_result = await sandbox.execute(
            "nvidia-smi 2>/dev/null | grep 'CUDA Version' | awk '{print $9}'",
            timeout=5,
        )
        if cuda_result.success and cuda_result.output.strip():
            cuda_ver = cuda_result.output.strip()

        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                gpu = GPUInfo(
                    model=parts[0],
                    vram_gb=_parse_vram(parts[1]),
                    cuda_version=cuda_ver,
                    driver_version=parts[2],
                )
                caps.gpu_info.append(gpu)

    # Python versions
    result = await sandbox.execute(
        "python3 --version 2>/dev/null; ls /usr/bin/python* 2>/dev/null || true",
        timeout=5,
    )
    if result.success:
        versions = []
        for line in result.output.strip().split("\n"):
            line = line.strip()
            if line.startswith("Python "):
                versions.append(line.replace("Python ", ""))
            elif "/python" in line and not line.endswith("*"):
                # Extract version from path like /usr/bin/python3.11
                ver = line.split("/")[-1].replace("python", "")
                if ver and ver not in versions:
                    versions.append(ver)
        caps.python_versions = versions

    # Docker
    result = await sandbox.execute(
        "docker info >/dev/null 2>&1 && echo 'DOCKER_OK' || echo 'DOCKER_FAIL'",
        timeout=5,
    )
    if result.success and "DOCKER_OK" in result.output:
        caps.docker_available = True

    # Conda envs
    result = await sandbox.execute(
        "conda env list 2>/dev/null | grep -v '^#' | awk '{print $1}' || true",
        timeout=5,
    )
    if result.success:
        envs = [ln.strip() for ln in result.output.strip().split("\n") if ln.strip()]
        caps.conda_envs = envs

    # Key packages
    result = await sandbox.execute(
        "pip list --format=freeze 2>/dev/null | head -50 || true",
        timeout=10,
    )
    if result.success:
        caps.installed_packages = [
            line.strip()
            for line in result.output.strip().split("\n")
            if line.strip() and "==" in line
        ]

    # Internet connectivity
    result = await sandbox.execute(
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://pypi.org/simple/ 2>/dev/null || echo '000'",
        timeout=10,
    )
    if result.success and result.output.strip() == "200":
        caps.has_internet = True
    else:
        # Fallback ping
        result = await sandbox.execute(
            "ping -c 1 -W 3 8.8.8.8 2>/dev/null || true",
            timeout=10,
        )
        caps.has_internet = result.success and "1 received" in result.output

    caps.latency_ms = (time.monotonic() - start) * 1000
    return caps


def _parse_vram(vram_str: str) -> float:
    """Parse VRAM string like '24576 MiB' or '24 GB' to GB."""
    vram_str = vram_str.strip().lower()
    try:
        if "mib" in vram_str:
            return float(vram_str.replace("mib", "").strip()) / 1024
        elif "gib" in vram_str:
            return float(vram_str.replace("gib", "").strip())
        elif "gb" in vram_str:
            return float(vram_str.replace("gb", "").strip())
        elif "mb" in vram_str:
            return float(vram_str.replace("mb", "").strip()) / 1024
        else:
            return float(vram_str)
    except ValueError:
        return 0.0
