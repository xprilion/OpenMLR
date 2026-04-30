#!/usr/bin/env python3
"""
Benchmark sub-1B language models on Apple Silicon
Tests performance, memory usage, and inference speed
"""

import gc
import json
import time

import psutil
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Test models (all <1B parameters)
MODELS_TO_TEST = [
    {"name": "Microsoft DialoGPT-small", "model_id": "microsoft/DialoGPT-small", "params": "117M"},
    {"name": "DistilGPT-2", "model_id": "distilgpt2", "params": "82M"},
    {"name": "GPT-2 Small", "model_id": "gpt2", "params": "124M"},
    {"name": "Qwen2-0.5B", "model_id": "Qwen/Qwen2-0.5B", "params": "494M"},
    {"name": "SmolLM-135M", "model_id": "HuggingFaceTB/SmolLM-135M", "params": "135M"},
    {"name": "TinyLlama-1.1B", "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "params": "1.1B"},
]

# Test prompts for different capabilities
TEST_PROMPTS = [
    "The capital of France is",
    "In Python, to create a list you use",
    "Explain quantum computing in simple terms:",
    "Write a short poem about machine learning:",
    "What is 15 * 23 + 7?",
]


def get_memory_usage() -> float:
    """Get current memory usage in GB"""
    return psutil.virtual_memory().used / (1024**3)


def get_model_size(model) -> float:
    """Get model size in MB"""
    param_size = sum(p.numel() * p.element_size() for p in model.parameters())
    return param_size / (1024**2)


def benchmark_model(model_info: dict) -> dict:
    """Benchmark a single model"""
    print(f"\n🔍 Testing {model_info['name']} ({model_info['params']})")

    results = {
        "name": model_info["name"],
        "model_id": model_info["model_id"],
        "params": model_info["params"],
        "load_time": 0,
        "model_size_mb": 0,
        "memory_usage_gb": 0,
        "inference_times": [],
        "tokens_per_second": [],
        "outputs": {},
        "errors": [],
    }

    try:
        results = _run_benchmark(model_info, results)
    except Exception as e:
        error_msg = f"Failed to load {model_info['name']}: {str(e)}"
        results["errors"].append(error_msg)
        print(f"  ❌ {error_msg}")

    return results


def _run_benchmark(model_info: dict, results: dict) -> dict:
    """Run the actual benchmark logic."""
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    initial_memory = get_memory_usage()

    # Load model
    start_time = time.time()
    print("  Loading tokenizer and model...")

    tokenizer = AutoTokenizer.from_pretrained(model_info["model_id"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_info["model_id"],
        torch_dtype=torch.float16 if torch.backends.mps.is_available() else torch.float32,
        device_map="auto" if torch.backends.mps.is_available() else None,
        trust_remote_code=True,
    )

    if torch.backends.mps.is_available():
        model = model.to("mps")

    load_time = time.time() - start_time
    results["load_time"] = load_time
    results["model_size_mb"] = get_model_size(model)
    results["memory_usage_gb"] = get_memory_usage() - initial_memory

    print(f"  ✅ Loaded in {load_time:.2f}s")
    print(f"  📦 Model size: {results['model_size_mb']:.1f} MB")
    print(f"  🧠 Memory usage: {results['memory_usage_gb']:.2f} GB")

    # Test inference
    print("  🚀 Running inference tests...")

    results = _run_inference_tests(model, tokenizer, results)

    # Calculate averages
    if results["inference_times"]:
        results["avg_inference_time"] = sum(results["inference_times"]) / len(
            results["inference_times"]
        )
        results["avg_tokens_per_second"] = sum(results["tokens_per_second"]) / len(
            results["tokens_per_second"]
        )

    print(f"  📊 Average: {results.get('avg_tokens_per_second', 0):.1f} tokens/sec")

    # Cleanup
    if "model" in locals():
        del model
    if "tokenizer" in locals():
        del tokenizer
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    return results


def _run_inference_tests(model, tokenizer, results: dict) -> dict:
    """Run inference tests on the model."""
    for i, prompt in enumerate(TEST_PROMPTS):
        try:
            inputs = tokenizer(prompt, return_tensors="pt", padding=True)
            if torch.backends.mps.is_available():
                inputs = {k: v.to("mps") for k, v in inputs.items()}

            start_time = time.time()

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=50,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=tokenizer.eos_token_id,
                )

            inference_time = time.time() - start_time

            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

            new_tokens = len(outputs[0]) - len(inputs["input_ids"][0])
            tokens_per_sec = new_tokens / inference_time if inference_time > 0 else 0

            results["inference_times"].append(inference_time)
            results["tokens_per_second"].append(tokens_per_sec)
            results["outputs"][f"prompt_{i}"] = {
                "prompt": prompt,
                "output": generated_text,
                "inference_time": inference_time,
                "tokens_per_sec": tokens_per_sec,
            }

            print(f"    Prompt {i + 1}: {tokens_per_sec:.1f} tokens/sec")

        except Exception as e:
            error_msg = f"Error on prompt {i}: {str(e)}"
            results["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")

    return results


def main():
    """Run benchmarks on all models"""
    print("🤖 Small Language Model Benchmark")
    print("=" * 50)
    print("💻 Device: Apple M3 with MPS")
    print(f"🧠 Total Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    print(f"🔥 PyTorch: {torch.__version__}")

    all_results = []

    for model_info in MODELS_TO_TEST:
        results = benchmark_model(model_info)
        all_results.append(results)

    # Summary
    print("\n" + "=" * 60)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 60)

    successful_models = [r for r in all_results if not r["errors"]]

    if successful_models:
        # Sort by tokens per second
        successful_models.sort(key=lambda x: x.get("avg_tokens_per_second", 0), reverse=True)

        print(f"{'Model':<25} {'Params':<8} {'Size (MB)':<10} {'Tokens/sec':<12} {'Load Time':<10}")
        print("-" * 75)

        for result in successful_models:
            print(
                f"{result['name']:<25} "
                f"{result['params']:<8} "
                f"{result['model_size_mb']:<10.1f} "
                f"{result.get('avg_tokens_per_second', 0):<12.1f} "
                f"{result['load_time']:<10.2f}"
            )

        # Best performer
        best = successful_models[0]
        print(f"\n🏆 Best Performer: {best['name']}")
        print(f"   Speed: {best.get('avg_tokens_per_second', 0):.1f} tokens/sec")
        print(
            f"   Efficiency: {best.get('avg_tokens_per_second', 0) / best['model_size_mb']:.3f} tokens/sec/MB"
        )

        # Show sample output from best model
        if "prompt_0" in best["outputs"]:
            print(f"\n💬 Sample output from {best['name']}:")
            print(f"   Prompt: {best['outputs']['prompt_0']['prompt']}")
            print(f"   Output: {best['outputs']['prompt_0']['output']}")

    # Save detailed results
    with open("benchmark_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n📄 Detailed results saved to benchmark_results.json")

    # Failed models
    failed_models = [r for r in all_results if r["errors"]]
    if failed_models:
        print(f"\n❌ Failed to test {len(failed_models)} models:")
        for result in failed_models:
            print(
                f"   {result['name']}: {result['errors'][0] if result['errors'] else 'Unknown error'}"
            )


if __name__ == "__main__":
    main()
