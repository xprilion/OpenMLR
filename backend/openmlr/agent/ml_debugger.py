"""Automated ML error diagnostic and self-healing engine.

Analyzes stdout/stderr/tracebacks from model training and research experiments,
identifies failure modes (CUDA OOM, loss NaN/divergence, shape mismatch,
missing packages, timeouts), and generates actionable self-healing guidance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

MODULE_TO_PIP_MAP: dict[str, str] = {
    "cv2": "opencv-python",
    "yaml": "pyyaml",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "fitz": "PyMuPDF",
    "bs4": "beautifulsoup4",
    "serial": "pyserial",
    "skimage": "scikit-image",
    "faiss": "faiss-cpu",
    "wandb": "wandb",
    "sentence_transformers": "sentence-transformers",
    "transformers": "transformers",
    "torchvision": "torchvision",
    "torchaudio": "torchaudio",
    "accelerate": "accelerate",
    "datasets": "datasets",
    "deepspeed": "deepspeed",
    "triton": "triton",
    "einops": "einops",
    "timm": "timm",
    "optuna": "optuna",
    "hydra": "hydra-core",
}


class MLErrorCategory(str, Enum):
    """Categorized classes of machine learning and deep learning errors."""

    CUDA_OOM = "cuda_oom"
    LOSS_NAN_INF = "loss_nan_inf"
    SHAPE_MISMATCH = "shape_mismatch"
    MISSING_PACKAGE = "missing_package"
    DEVICE_MISMATCH = "device_mismatch"
    TIMEOUT_DEADLOCK = "timeout_deadlock"
    UNKNOWN = "unknown"


@dataclass
class MLErrorDiagnostic:
    """Structured diagnostic result with root-cause analysis and remedies."""

    category: MLErrorCategory
    summary: str
    root_cause: str
    extracted_details: dict[str, Any] = field(default_factory=dict)
    suggested_actions: list[str] = field(default_factory=list)
    auto_fix_patch: str | None = None
    remedy_prompt: str = ""


def get_package_install_name(module_name: str) -> str:
    """Map a Python import module name to its PyPI distribution name."""
    clean_name = module_name.split(".")[0].strip()
    return MODULE_TO_PIP_MAP.get(clean_name, clean_name)


class MLErrorDebugger:
    """Diagnostic parser and automated healing transformer for ML code execution."""

    # Regex patterns for ML failure modes
    _CUDA_OOM_RE = re.compile(
        r"(?:torch\.cuda\.OutOfMemoryError|CUDA out of memory\."
        r"|Tried to allocate\s+([0-9\.]+\s+[GMK]i?B)"
        r".*?total capacity of\s+([0-9\.]+\s+[GMK]i?B))",
        re.IGNORECASE | re.DOTALL,
    )

    _NAN_INF_RE = re.compile(
        r"(?:(?:loss|Loss)\s*(?:is|=|:)?\s*(?:nan|NaN|inf|Inf)"
        r"|Function\s+'([^']+)'\s+returned\s+(?:nan|inf)\s+values"
        r"|grad(?:ient)?\s+(?:norm\s+)?is\s+(?:nan|inf)"
        r"|overflow encountered in)",
        re.IGNORECASE,
    )

    _SHAPE_LINEAR_RE = re.compile(
        r"mat1 and mat2 shapes cannot be multiplied\s*\(([^)]+)\s+and\s+([^)]+)\)",
        re.IGNORECASE,
    )

    _SHAPE_ELEMENTWISE_RE = re.compile(
        r"The size of tensor a\s*\(([^)]+)\)\s*must match the size of tensor b\s*\(([^)]+)\)",
        re.IGNORECASE,
    )

    _SHAPE_INVALID_RE = re.compile(
        r"shape\s*'([^']+)'\s*is invalid for input of size\s*(\d+)",
        re.IGNORECASE,
    )

    _DEVICE_MISMATCH_RE = re.compile(
        r"(?:Expected all tensors to be on the same device"
        r"|found at least two devices"
        r"|tensors on different devices)",
        re.IGNORECASE,
    )

    _MISSING_MODULE_RE = re.compile(
        r"(?:ModuleNotFoundError:\s*No module named\s*['\"]([^'\"]+)['\"]"
        r"|ImportError:\s*cannot import name\s*['\"]([^'\"]+)['\"]\s*from\s*['\"]([^'\"]+)['\"])",
        re.IGNORECASE,
    )

    _TIMEOUT_NCCL_RE = re.compile(
        r"(?:Watchdog caught collective operation timeout"
        r"|NCCL error"
        r"|DataLoader worker.*killed"
        r"|Process timed out after\s*(\d+)\s*seconds)",
        re.IGNORECASE,
    )

    def diagnose(self, text: str) -> MLErrorDiagnostic | None:
        """Analyze tool execution output for ML-specific failure patterns."""
        if not text:
            return None

        # Check CUDA OOM
        oom_match = self._CUDA_OOM_RE.search(text)
        if oom_match or "OutOfMemoryError" in text or "CUDA out of memory" in text:
            return self._diagnose_cuda_oom(text, oom_match)

        # Check Loss NaN / Inf
        nan_match = self._NAN_INF_RE.search(text)
        if nan_match:
            return self._diagnose_nan_inf(text, nan_match)

        # Check Tensor Shape Mismatch
        if "shapes cannot be multiplied" in text or "must match the size of tensor" in text or "is invalid for input of size" in text:
            return self._diagnose_shape_mismatch(text)

        # Check Missing Module / Package
        missing_match = self._MISSING_MODULE_RE.search(text)
        if missing_match:
            return self._diagnose_missing_package(text, missing_match)

        # Check Device Mismatch
        if self._DEVICE_MISMATCH_RE.search(text):
            return self._diagnose_device_mismatch(text)

        # Check Timeout / Deadlock / NCCL
        timeout_match = self._TIMEOUT_NCCL_RE.search(text)
        if timeout_match:
            return self._diagnose_timeout_deadlock(text, timeout_match)

        return None

    def _diagnose_cuda_oom(self, text: str, match: re.Match | None) -> MLErrorDiagnostic:
        details: dict[str, Any] = {}
        alloc_m = re.search(r"Tried to allocate\s+([0-9\.]+\s+[GMK]i?B)", text)
        cap_m = re.search(r"([0-9\.]+\s+[GMK]i?B)\s+total capacity", text)
        if alloc_m:
            details["attempted_alloc"] = alloc_m.group(1).strip()
        if cap_m:
            details["total_capacity"] = cap_m.group(1).strip()

        alloc_str = details.get("attempted_alloc", "memory block")
        summary = f"CUDA Out-of-Memory error while allocating {alloc_str}."
        root_cause = "GPU VRAM capacity exceeded by model weights, activations, or batch size."

        suggested = [
            "Reduce per-device batch size (e.g. half batch_size) and increase gradient accumulation steps.",
            "Enable mixed precision training (torch.cuda.amp.autocast() / bfloat16 / fp16).",
            "Enable gradient checkpointing (torch.utils.checkpoint.checkpoint) for transformer layers.",
            "Clear cache before memory-intensive steps with torch.cuda.empty_cache().",
            "Use FlashAttention (attn_implementation='flash_attention_2' or F.scaled_dot_product_attention).",
        ]

        prompt = (
            f"### [Self-Healing Alert] CUDA Out-of-Memory (OOM)\n\n"
            f"**Cause:** {root_cause} (Attempted alloc: {alloc_str})\n\n"
            f"**Recommended Fixes:**\n"
            + "\n".join(f"- {s}" for s in suggested)
        )

        return MLErrorDiagnostic(
            category=MLErrorCategory.CUDA_OOM,
            summary=summary,
            root_cause=root_cause,
            extracted_details=details,
            suggested_actions=suggested,
            auto_fix_patch=None,
            remedy_prompt=prompt,
        )

    def _diagnose_nan_inf(self, text: str, match: re.Match) -> MLErrorDiagnostic:
        details: dict[str, Any] = {}
        fn_match = re.search(r"Function\s+'([^']+)'\s+returned\s+(?:nan|inf)", text)
        if fn_match:
            details["offending_fn"] = fn_match.group(1)
            summary = f"Loss NaN/Inf divergence detected in function '{fn_match.group(1)}'."
        else:
            summary = "Loss/gradient explosion or NaN divergence encountered during training."

        root_cause = "Numerical instability, exploding gradients, unscaled learning rate, or log(0)/division by zero."

        suggested = [
            "Add gradient clipping: `torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)`.",
            "Reduce the initial learning rate (e.g., divide by 5x or 10x) and add a learning rate warmup.",
            "Add numerical epsilon to denominators/log operations: `torch.log(x.clamp(min=1e-8))`.",
            "Ensure loss computations run in FP32 precision even when using FP16 autocast.",
            "Enable `torch.autograd.set_detect_anomaly(True)` to trace the exact backward operation producing NaN.",
        ]

        prompt = (
            f"### [Self-Healing Alert] Loss Divergence / NaN\n\n"
            f"**Cause:** {root_cause}\n\n"
            f"**Recommended Fixes:**\n"
            + "\n".join(f"- {s}" for s in suggested)
        )

        return MLErrorDiagnostic(
            category=MLErrorCategory.LOSS_NAN_INF,
            summary=summary,
            root_cause=root_cause,
            extracted_details=details,
            suggested_actions=suggested,
            auto_fix_patch=None,
            remedy_prompt=prompt,
        )

    def _diagnose_shape_mismatch(self, text: str) -> MLErrorDiagnostic:
        details: dict[str, Any] = {}
        suggested: list[str] = []

        mat_m = self._SHAPE_LINEAR_RE.search(text)
        elem_m = self._SHAPE_ELEMENTWISE_RE.search(text)
        inv_m = self._SHAPE_INVALID_RE.search(text)

        if mat_m:
            shape_a = mat_m.group(1).strip()
            shape_b = mat_m.group(2).strip()
            details["shape_a"] = shape_a
            details["shape_b"] = shape_b
            summary = f"Matrix multiplication dimension mismatch: {shape_a} vs {shape_b}."
            root_cause = f"Inner matrix dimensions do not align for matmul ({shape_a} and {shape_b})."
            suggested.append(
                f"Align the projection layer in_features ({shape_b.split('x')[0]}) to match output features ({shape_a.split('x')[-1]})."
            )
            suggested.append("Check if a transpose, permute, or reshape is required prior to the Linear layer.")
        elif elem_m:
            dim_a = elem_m.group(1).strip()
            dim_b = elem_m.group(2).strip()
            details["dim_a"] = dim_a
            details["dim_b"] = dim_b
            summary = f"Tensor element-wise size mismatch: dimension {dim_a} vs {dim_b}."
            root_cause = f"Tensors have mismatched broadcasting dimensions ({dim_a} != {dim_b})."
            suggested.append(f"Ensure tensors have matching shapes ({dim_a} vs {dim_b}) or use broadcasting/unsqueeze.")
        elif inv_m:
            req_shape = inv_m.group(1).strip()
            total_sz = inv_m.group(2).strip()
            details["target_shape"] = req_shape
            details["input_size"] = total_sz
            summary = f"Invalid tensor reshape: shape '{req_shape}' incompatible with input size {total_sz}."
            root_cause = "Product of target dimensions does not equal input element count."
            suggested.append(f"Adjust reshape dimensions so their product equals total size {total_sz}.")
        else:
            summary = "PyTorch tensor dimension / shape alignment error."
            root_cause = "Tensor shapes incompatible for the requested operation."
            suggested.append("Inspect intermediate tensor shapes with `print(tensor.shape)`.")

        prompt = (
            f"### [Self-Healing Alert] Tensor Shape Mismatch\n\n"
            f"**Cause:** {root_cause}\n\n"
            f"**Recommended Fixes:**\n"
            + "\n".join(f"- {s}" for s in suggested)
        )

        return MLErrorDiagnostic(
            category=MLErrorCategory.SHAPE_MISMATCH,
            summary=summary,
            root_cause=root_cause,
            extracted_details=details,
            suggested_actions=suggested,
            auto_fix_patch=None,
            remedy_prompt=prompt,
        )

    def _diagnose_missing_package(self, text: str, match: re.Match) -> MLErrorDiagnostic:
        details: dict[str, Any] = {}
        missing_mod = match.group(1) or match.group(3) or ""
        pip_pkg = get_package_install_name(missing_mod)
        details["missing_module"] = missing_mod
        details["pip_package"] = pip_pkg

        summary = f"Missing Python module: '{missing_mod}' (PyPI package: '{pip_pkg}')."
        root_cause = f"The package '{pip_pkg}' is not installed in the active environment."
        patch_cmd = f"pip install {pip_pkg}"

        suggested = [
            f"Install the missing dependency: `{patch_cmd}`.",
            "Check requirements.txt or pyproject.toml to ensure dependencies are declared.",
        ]

        prompt = (
            f"### [Self-Healing Alert] Missing Dependency\n\n"
            f"**Cause:** Module `{missing_mod}` is required but missing.\n\n"
            f"**Automated Fix:** Run `{patch_cmd}` before executing the script."
        )

        return MLErrorDiagnostic(
            category=MLErrorCategory.MISSING_PACKAGE,
            summary=summary,
            root_cause=root_cause,
            extracted_details=details,
            suggested_actions=suggested,
            auto_fix_patch=patch_cmd,
            remedy_prompt=prompt,
        )

    def _diagnose_device_mismatch(self, text: str) -> MLErrorDiagnostic:
        summary = "Device mismatch error (tensors on different devices like CPU and CUDA)."
        root_cause = "Operations attempted on tensors resident on conflicting devices (e.g. CPU vs cuda:0)."
        suggested = [
            "Ensure input tensors and model parameters are moved to the same device: `x = x.to(device)`.",
            "Check that custom loss functions or target labels are on `device`.",
            "Verify all buffers in custom modules are registered with `register_buffer()` so `.to(device)` moves them.",
        ]

        prompt = (
            "### [Self-Healing Alert] Device Mismatch\n\n"
            f"**Cause:** {root_cause}\n\n"
            "**Recommended Fixes:**\n"
            + "\n".join(f"- {s}" for s in suggested)
        )

        return MLErrorDiagnostic(
            category=MLErrorCategory.DEVICE_MISMATCH,
            summary=summary,
            root_cause=root_cause,
            extracted_details={},
            suggested_actions=suggested,
            auto_fix_patch=None,
            remedy_prompt=prompt,
        )

    def _diagnose_timeout_deadlock(self, text: str, match: re.Match) -> MLErrorDiagnostic:
        summary = "Execution timeout / distributed communication (NCCL) deadlock."
        root_cause = "Hanging worker process, deadlocked DDP barrier, or dataloader multiprocessing stall."
        suggested = [
            "Set `num_workers=0` on PyTorch DataLoader to prevent multiprocessing deadlocks inside containers.",
            "Verify distributed communication backend (use 'gloo' on CPU or ensure NCCL network interfaces are reachable).",
            "Increase timeout or inspect whether long evaluation loops lack progress logging.",
        ]

        prompt = (
            "### [Self-Healing Alert] Timeout / Collective Communication Deadlock\n\n"
            f"**Cause:** {root_cause}\n\n"
            "**Recommended Fixes:**\n"
            + "\n".join(f"- {s}" for s in suggested)
        )

        return MLErrorDiagnostic(
            category=MLErrorCategory.TIMEOUT_DEADLOCK,
            summary=summary,
            root_cause=root_cause,
            extracted_details={},
            suggested_actions=suggested,
            auto_fix_patch=None,
            remedy_prompt=prompt,
        )

    def generate_self_healing_code(self, code: str, diagnostic: MLErrorDiagnostic) -> str | None:
        """Apply automated AST/text transformations to heal common ML issues in Python scripts."""
        if not code or not diagnostic:
            return None

        healed = code

        if diagnostic.category == MLErrorCategory.CUDA_OOM:
            # 1. Halve batch size if found
            batch_m = re.search(r"(batch_size\s*=\s*)(\d+)", healed)
            if batch_m:
                old_bs = int(batch_m.group(2))
                new_bs = max(1, old_bs // 2)
                healed = healed[:batch_m.start()] + f"batch_size = {new_bs}" + healed[batch_m.end():]

            # 2. Inject empty_cache and gradient accumulation note
            if "torch.cuda.empty_cache()" not in healed:
                healed = "import torch\n" + healed
                healed = healed.replace(
                    "loss.backward()",
                    "loss.backward()\n        torch.cuda.empty_cache()"
                )
            return healed

        elif diagnostic.category == MLErrorCategory.LOSS_NAN_INF:
            # 1. Reduce learning rate if found
            lr_m = re.search(r"(lr\s*=\s*)([0-9\.eE\-]+)", healed)
            if lr_m:
                try:
                    old_lr = float(lr_m.group(2))
                    new_lr = old_lr * 0.2
                    healed = healed[:lr_m.start()] + f"lr={new_lr:.4g}" + healed[lr_m.end():]
                except ValueError:
                    pass

            # 2. Add gradient clipping before optimizer.step()
            if "clip_grad_norm_" not in healed and "optimizer.step()" in healed:
                healed = healed.replace(
                    "optimizer.step()",
                    "torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)\n        optimizer.step()"
                )
            return healed

        return healed


def diagnose_ml_error(text: str) -> MLErrorDiagnostic | None:
    """Convenience function to diagnose ML error from text output."""
    debugger = MLErrorDebugger()
    return debugger.diagnose(text)
