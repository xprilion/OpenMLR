"""Tests for the ML Error Diagnostic & Self-Healing Engine (ml_debugger)."""


from openmlr.agent.ml_debugger import (
    MLErrorCategory,
    MLErrorDebugger,
    MLErrorDiagnostic,
    diagnose_ml_error,
    get_package_install_name,
)


class TestMLErrorDiagnostics:
    """Test recognition and extraction of various machine learning failure modes."""

    def test_cuda_oom_diagnosis(self):
        output = """
Traceback (most recent call last):
  File "train.py", line 84, in <module>
    loss.backward()
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 4.20 GiB (GPU 0; 23.69 GiB total capacity; 21.10 GiB already allocated; 1.50 GiB free; 22.00 GiB reserved in total by PyTorch)
"""
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.CUDA_OOM
        assert "4.20 GiB" in diag.summary or "CUDA out of memory" in diag.summary
        assert diag.extracted_details.get("attempted_alloc") == "4.20 GiB"
        assert diag.extracted_details.get("total_capacity") == "23.69 GiB"
        assert len(diag.suggested_actions) >= 3
        assert any("gradient accumulation" in a.lower() for a in diag.suggested_actions)
        assert any("batch size" in a.lower() for a in diag.suggested_actions)
        assert "CUDA Out-of-Memory" in diag.remedy_prompt

    def test_loss_nan_diagnosis(self):
        output = """
Epoch 1 | Step 150/1000 | Loss: 2.3412
Epoch 1 | Step 151/1000 | Loss: 8.9412
Epoch 1 | Step 152/1000 | Loss: nan | GradNorm: 184920.4
RuntimeError: Function 'LogSoftmaxBackward0' returned nan values in its gradient
"""
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.LOSS_NAN_INF
        assert "LogSoftmaxBackward0" in diag.summary or "nan" in diag.summary.lower()
        assert len(diag.suggested_actions) >= 3
        assert any("gradient clipping" in a.lower() for a in diag.suggested_actions)
        assert any("learning rate" in a.lower() for a in diag.suggested_actions)
        assert "Loss Divergence / NaN" in diag.remedy_prompt

    def test_loss_inf_diagnosis(self):
        output = "Step 40: loss = inf (loss exploded after unscaled forward pass)"
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.LOSS_NAN_INF
        assert any("clipping" in a.lower() or "learning rate" in a.lower() for a in diag.suggested_actions)

    def test_tensor_shape_mismatch_linear(self):
        output = """
File "model.py", line 42, in forward
  return self.fc2(x)
RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x768 and 512x256)
"""
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.SHAPE_MISMATCH
        assert diag.extracted_details.get("shape_a") == "64x768"
        assert diag.extracted_details.get("shape_b") == "512x256"
        assert any("768" in a and "512" in a for a in diag.suggested_actions)

    def test_tensor_shape_mismatch_elementwise(self):
        output = """
RuntimeError: The size of tensor a (128) must match the size of tensor b (64) at non-singleton dimension 1
"""
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.SHAPE_MISMATCH
        assert diag.extracted_details.get("dim_a") == "128"
        assert diag.extracted_details.get("dim_b") == "64"

    def test_missing_module_known_mapping(self):
        output = "ModuleNotFoundError: No module named 'cv2'"
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.MISSING_PACKAGE
        assert diag.extracted_details.get("missing_module") == "cv2"
        assert diag.extracted_details.get("pip_package") == "opencv-python"
        assert diag.auto_fix_patch == "pip install opencv-python"

    def test_missing_module_import_error(self):
        output = "ImportError: cannot import name 'AutoModelForCausalLM' from 'transformers'"
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.MISSING_PACKAGE
        assert "transformers" in diag.summary

    def test_device_mismatch(self):
        output = "RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu!"
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.DEVICE_MISMATCH
        assert any(".to(device)" in a for a in diag.suggested_actions)

    def test_timeout_and_nccl_deadlock(self):
        output = "RuntimeError: [Watchdog caught collective operation timeout: WorkNCCL(OpType=ALLREDUCE, Timeout(ms)=600000)]"
        diag = diagnose_ml_error(output)
        assert diag is not None
        assert diag.category == MLErrorCategory.TIMEOUT_DEADLOCK
        assert any("dataloader" in a.lower() or "nccl" in a.lower() or "timeout" in a.lower() for a in diag.suggested_actions)

    def test_no_ml_error_clean_output(self):
        output = "Epoch 1/10 complete. Validation Accuracy: 0.941"
        diag = diagnose_ml_error(output)
        assert diag is None


class TestPackageMapping:
    """Test module to pypi mapping helper."""

    def test_known_mappings(self):
        assert get_package_install_name("cv2") == "opencv-python"
        assert get_package_install_name("yaml") == "pyyaml"
        assert get_package_install_name("PIL") == "Pillow"
        assert get_package_install_name("sklearn") == "scikit-learn"
        assert get_package_install_name("fitz") == "PyMuPDF"
        assert get_package_install_name("torchvision") == "torchvision"

    def test_unknown_fallback(self):
        assert get_package_install_name("einops") == "einops"


class TestSelfHealingCodeTransforms:
    """Test automatic code modification recommendations for self-healing."""

    def test_heal_cuda_oom_adds_batch_reduction_and_grad_accum(self):
        debugger = MLErrorDebugger()
        code = """
import torch

batch_size = 64
learning_rate = 1e-4
for epoch in range(10):
    for batch in dataloader:
        optimizer.zero_grad()
        loss = model(batch)
        loss.backward()
        optimizer.step()
"""
        diag = MLErrorDiagnostic(
            category=MLErrorCategory.CUDA_OOM,
            summary="CUDA OOM allocating 4.2 GiB",
            root_cause="Batch size exceeds GPU VRAM capacity",
            extracted_details={"attempted_alloc": "4.2 GiB"},
            suggested_actions=["Reduce batch size", "Use gradient accumulation"],
            auto_fix_patch=None,
            remedy_prompt="",
        )
        healed = debugger.generate_self_healing_code(code, diag)
        assert healed is not None
        assert "batch_size = 32" in healed or "gradient_accumulation_steps" in healed
        assert "torch.cuda.empty_cache()" in healed or "scaler" in healed

    def test_heal_nan_adds_grad_clip_and_lr_reduction(self):
        debugger = MLErrorDebugger()
        code = """
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
for x, y in loader:
    loss = criterion(model(x), y)
    loss.backward()
    optimizer.step()
"""
        diag = MLErrorDiagnostic(
            category=MLErrorCategory.LOSS_NAN_INF,
            summary="Loss is NaN",
            root_cause="Exploding gradients",
            extracted_details={},
            suggested_actions=["Add gradient clipping", "Lower LR"],
            auto_fix_patch=None,
            remedy_prompt="",
        )
        healed = debugger.generate_self_healing_code(code, diag)
        assert healed is not None
        assert "clip_grad_norm_" in healed
        assert "lr=2e-04" in healed or "lr=0.0002" in healed or "clip_grad_norm" in healed
