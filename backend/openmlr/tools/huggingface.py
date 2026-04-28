"""Hugging Face Hub tools — model search, dataset search, model/dataset cards, file reading."""

import logging
import os

from ..agent.types import ToolSpec
from .http_utils import RateLimitError, fetch_with_retry

log = logging.getLogger(__name__)

HF_API = "https://huggingface.co"


def _headers() -> dict:
    token = os.environ.get("HF_TOKEN")
    h: dict[str, str] = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def create_huggingface_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="hf_search_models",
            description=(
                "Search Hugging Face Hub for models by keyword, pipeline task, or library. "
                "Useful for finding pre-trained models, fine-tuned checkpoints, and SOTA architectures."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g. 'llama 3 instruct', 'stable diffusion xl')",
                    },
                    "pipeline_tag": {
                        "type": "string",
                        "description": (
                            "Filter by pipeline task (e.g. text-generation, "
                            "image-classification, text-to-image, automatic-speech-recognition)"
                        ),
                    },
                    "library": {
                        "type": "string",
                        "description": "Filter by library (e.g. transformers, diffusers, gguf, safetensors)",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by: downloads, likes, trending, created, modified (default: trending)",
                        "enum": ["downloads", "likes", "trending", "created", "modified"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 15)",
                    },
                },
                "required": ["query"],
            },
            handler=_handle_search_models,
        ),
        ToolSpec(
            name="hf_model_info",
            description=(
                "Get detailed information about a Hugging Face model, including its model card "
                "(README), metadata, download count, pipeline tag, library, and tags. "
                "Provide the full repo ID like 'deepseek-ai/DeepSeek-V3' or 'meta-llama/Llama-3-8B'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Model repo ID (e.g. 'meta-llama/Llama-3-8B', 'mistralai/Mistral-7B-v0.1')",
                    },
                    "include_readme": {
                        "type": "boolean",
                        "description": "Whether to fetch the full model card / README (default: true)",
                    },
                },
                "required": ["repo_id"],
            },
            handler=_handle_model_info,
        ),
        ToolSpec(
            name="hf_search_datasets",
            description=(
                "Search Hugging Face Hub for datasets by keyword or task. "
                "Useful for finding training data, benchmarks, and evaluation datasets."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g. 'code instruction', 'medical qa')",
                    },
                    "task": {
                        "type": "string",
                        "description": (
                            "Filter by task category (e.g. text-classification, "
                            "question-answering, summarization, text-generation)"
                        ),
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by: downloads, likes, trending, created, modified (default: trending)",
                        "enum": ["downloads", "likes", "trending", "created", "modified"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 15)",
                    },
                },
                "required": ["query"],
            },
            handler=_handle_search_datasets,
        ),
        ToolSpec(
            name="hf_dataset_info",
            description=(
                "Get detailed information about a Hugging Face dataset, including its dataset card "
                "(README), metadata, download count, and tags. "
                "Provide the full repo ID like 'tatsu-lab/alpaca' or 'Open-Orca/OpenOrca'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Dataset repo ID (e.g. 'tatsu-lab/alpaca', 'Open-Orca/OpenOrca')",
                    },
                    "include_readme": {
                        "type": "boolean",
                        "description": "Whether to fetch the full dataset card / README (default: true)",
                    },
                },
                "required": ["repo_id"],
            },
            handler=_handle_dataset_info,
        ),
        ToolSpec(
            name="hf_read_file",
            description=(
                "Read a file from a Hugging Face repository (model, dataset, or space). "
                "Useful for reading config.json, tokenizer configs, training scripts, etc. "
                "For model cards / READMEs, prefer hf_model_info or hf_dataset_info instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repo ID (e.g. 'meta-llama/Llama-3-8B')",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path within the repo (e.g. 'config.json', 'tokenizer_config.json')",
                    },
                    "repo_type": {
                        "type": "string",
                        "description": "Repository type: model, dataset, space (default: model)",
                        "enum": ["model", "dataset", "space"],
                    },
                    "revision": {
                        "type": "string",
                        "description": "Branch, tag, or commit hash (default: main)",
                    },
                },
                "required": ["repo_id", "path"],
            },
            handler=_handle_read_file,
        ),
    ]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def _handle_search_models(
    query: str,
    pipeline_tag: str | None = None,
    library: str | None = None,
    sort: str = "trending",
    limit: int = 15,
    **kwargs,
) -> tuple[str, bool]:
    """Search Hugging Face Hub for models."""
    url = f"{HF_API}/api/models"

    params: dict[str, str | int] = {
        "search": query,
        "limit": min(limit, 50),
        "sort": sort,
        "direction": "-1",
    }
    if pipeline_tag:
        params["pipeline_tag"] = pipeline_tag
    if library:
        params["library"] = library

    try:
        resp = await fetch_with_retry(
            url, headers=_headers(), params=params, timeout=30, max_retries=3
        )
    except RateLimitError:
        return "Hugging Face rate limit reached. Try again later or add HF_TOKEN.", False
    except Exception as e:
        log.warning(f"HF search models error: {e}")
        return f"Hugging Face API error: {str(e)[:200]}", False

    if resp.status_code != 200:
        return f"Hugging Face API error {resp.status_code}: {resp.text[:500]}", False

    models = resp.json()
    if not models:
        return f"No models found for: {query}", True

    lines = [f"Found {len(models)} models for '{query}':\n"]
    for m in models[:limit]:
        model_id = m.get("modelId") or m.get("id", "?")
        downloads = m.get("downloads", 0)
        likes = m.get("likes", 0)
        pipeline = m.get("pipeline_tag", "")
        tags = m.get("tags", [])[:5]
        lib_tags = [
            t
            for t in tags
            if t
            in (
                "transformers",
                "diffusers",
                "gguf",
                "safetensors",
                "pytorch",
                "tensorflow",
                "jax",
                "onnx",
                "openvino",
            )
        ]

        lines.append(f"**{model_id}** ({downloads:,} downloads, {likes} likes)")
        meta_parts = []
        if pipeline:
            meta_parts.append(f"Task: {pipeline}")
        if lib_tags:
            meta_parts.append(f"Libraries: {', '.join(lib_tags)}")
        if meta_parts:
            lines.append(f"  {' | '.join(meta_parts)}")
        lines.append(f"  https://huggingface.co/{model_id}\n")

    return "\n".join(lines), True


async def _handle_model_info(
    repo_id: str, include_readme: bool = True, **kwargs
) -> tuple[str, bool]:
    """Get detailed info + model card for a Hugging Face model."""
    url = f"{HF_API}/api/models/{repo_id}"

    try:
        resp = await fetch_with_retry(url, headers=_headers(), timeout=30, max_retries=3)
    except RateLimitError:
        return "Hugging Face rate limit reached. Try again later or add HF_TOKEN.", False
    except Exception as e:
        log.warning(f"HF model info error: {e}")
        return f"Hugging Face API error: {str(e)[:200]}", False

    if resp.status_code == 404:
        return f"Model not found: {repo_id}", False
    if resp.status_code != 200:
        return f"Hugging Face API error {resp.status_code}: {resp.text[:500]}", False

    data = resp.json()

    # Build metadata summary
    lines = [f"# Model: {repo_id}\n"]
    lines.append(f"- **URL**: https://huggingface.co/{repo_id}")
    if data.get("pipeline_tag"):
        lines.append(f"- **Pipeline**: {data['pipeline_tag']}")
    if data.get("library_name"):
        lines.append(f"- **Library**: {data['library_name']}")
    lines.append(f"- **Downloads**: {data.get('downloads', 0):,}")
    lines.append(f"- **Likes**: {data.get('likes', 0)}")
    if data.get("author"):
        lines.append(f"- **Author**: {data['author']}")
    if data.get("lastModified"):
        lines.append(f"- **Last modified**: {data['lastModified']}")

    tags = data.get("tags", [])
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags[:15])}")

    siblings = data.get("siblings", [])
    if siblings:
        file_names = [s.get("rfilename", "") for s in siblings[:30]]
        lines.append(f"\n**Files** ({len(siblings)} total): {', '.join(file_names)}")
        if len(siblings) > 30:
            lines.append(f"  ... and {len(siblings) - 30} more")

    # Fetch README / model card
    if include_readme:
        readme_content = await _fetch_readme(repo_id, "model")
        if readme_content:
            lines.append(f"\n---\n\n## Model Card\n\n{readme_content}")

    output = "\n".join(lines)
    if len(output) > 50000:
        output = output[:50000] + "\n\n...[truncated]"
    return output, True


async def _handle_search_datasets(
    query: str,
    task: str | None = None,
    sort: str = "trending",
    limit: int = 15,
    **kwargs,
) -> tuple[str, bool]:
    """Search Hugging Face Hub for datasets."""
    url = f"{HF_API}/api/datasets"

    params: dict[str, str | int] = {
        "search": query,
        "limit": min(limit, 50),
        "sort": sort,
        "direction": "-1",
    }
    if task:
        params["task_categories"] = task

    try:
        resp = await fetch_with_retry(
            url, headers=_headers(), params=params, timeout=30, max_retries=3
        )
    except RateLimitError:
        return "Hugging Face rate limit reached. Try again later or add HF_TOKEN.", False
    except Exception as e:
        log.warning(f"HF search datasets error: {e}")
        return f"Hugging Face API error: {str(e)[:200]}", False

    if resp.status_code != 200:
        return f"Hugging Face API error {resp.status_code}: {resp.text[:500]}", False

    datasets = resp.json()
    if not datasets:
        return f"No datasets found for: {query}", True

    lines = [f"Found {len(datasets)} datasets for '{query}':\n"]
    for d in datasets[:limit]:
        ds_id = d.get("id", "?")
        downloads = d.get("downloads", 0)
        likes = d.get("likes", 0)
        description = (d.get("description") or "")[:120]
        tags = d.get("tags", [])[:5]

        lines.append(f"**{ds_id}** ({downloads:,} downloads, {likes} likes)")
        if description:
            lines.append(f"  {description}")
        if tags:
            lines.append(f"  Tags: {', '.join(tags)}")
        lines.append(f"  https://huggingface.co/datasets/{ds_id}\n")

    return "\n".join(lines), True


async def _handle_dataset_info(
    repo_id: str, include_readme: bool = True, **kwargs
) -> tuple[str, bool]:
    """Get detailed info + dataset card for a Hugging Face dataset."""
    url = f"{HF_API}/api/datasets/{repo_id}"

    try:
        resp = await fetch_with_retry(url, headers=_headers(), timeout=30, max_retries=3)
    except RateLimitError:
        return "Hugging Face rate limit reached. Try again later or add HF_TOKEN.", False
    except Exception as e:
        log.warning(f"HF dataset info error: {e}")
        return f"Hugging Face API error: {str(e)[:200]}", False

    if resp.status_code == 404:
        return f"Dataset not found: {repo_id}", False
    if resp.status_code != 200:
        return f"Hugging Face API error {resp.status_code}: {resp.text[:500]}", False

    data = resp.json()

    lines = [f"# Dataset: {repo_id}\n"]
    lines.append(f"- **URL**: https://huggingface.co/datasets/{repo_id}")
    lines.append(f"- **Downloads**: {data.get('downloads', 0):,}")
    lines.append(f"- **Likes**: {data.get('likes', 0)}")
    if data.get("author"):
        lines.append(f"- **Author**: {data['author']}")
    if data.get("lastModified"):
        lines.append(f"- **Last modified**: {data['lastModified']}")

    tags = data.get("tags", [])
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags[:15])}")

    description = data.get("description", "")
    if description:
        lines.append(f"- **Description**: {description[:300]}")

    siblings = data.get("siblings", [])
    if siblings:
        file_names = [s.get("rfilename", "") for s in siblings[:30]]
        lines.append(f"\n**Files** ({len(siblings)} total): {', '.join(file_names)}")
        if len(siblings) > 30:
            lines.append(f"  ... and {len(siblings) - 30} more")

    # Fetch README / dataset card
    if include_readme:
        readme_content = await _fetch_readme(repo_id, "dataset")
        if readme_content:
            lines.append(f"\n---\n\n## Dataset Card\n\n{readme_content}")

    output = "\n".join(lines)
    if len(output) > 50000:
        output = output[:50000] + "\n\n...[truncated]"
    return output, True


async def _handle_read_file(
    repo_id: str,
    path: str,
    repo_type: str = "model",
    revision: str = "main",
    **kwargs,
) -> tuple[str, bool]:
    """Read a file from a Hugging Face repository."""
    # Build the resolve URL based on repo type
    if repo_type == "dataset":
        url = f"{HF_API}/datasets/{repo_id}/resolve/{revision}/{path}"
    elif repo_type == "space":
        url = f"{HF_API}/spaces/{repo_id}/resolve/{revision}/{path}"
    else:
        url = f"{HF_API}/{repo_id}/resolve/{revision}/{path}"

    try:
        resp = await fetch_with_retry(url, headers=_headers(), timeout=30, max_retries=3)
    except RateLimitError:
        return "Hugging Face rate limit reached. Try again later or add HF_TOKEN.", False
    except Exception as e:
        log.warning(f"HF read file error: {e}")
        return f"Hugging Face API error: {str(e)[:200]}", False

    if resp.status_code == 404:
        return f"File not found: {repo_id}/{path} (revision: {revision})", False
    if resp.status_code == 401:
        return (
            f"Access denied for {repo_id}/{path}. "
            "This may be a gated model — add HF_TOKEN with accepted access."
        ), False
    if resp.status_code == 403:
        return (
            f"Forbidden: {repo_id}/{path}. "
            "You may need to accept the model's license on huggingface.co first."
        ), False
    if resp.status_code != 200:
        return f"Hugging Face API error {resp.status_code}: {resp.text[:500]}", False

    content_type = resp.headers.get("content-type", "")

    # Binary files — just report metadata
    if "application/octet-stream" in content_type or path.endswith(
        (".bin", ".safetensors", ".gguf", ".pt", ".pth", ".h5", ".onnx", ".msgpack")
    ):
        size = len(resp.content)
        return (
            f"Binary file: {repo_id}/{path} ({size:,} bytes). "
            "Cannot display binary content. Use hf_model_info to see the file list."
        ), True

    # Text content
    try:
        text = resp.text
    except Exception:
        return f"Could not decode file: {repo_id}/{path}", False

    # Add line numbers for code-like files
    if path.endswith((".py", ".js", ".ts", ".yaml", ".yml", ".toml", ".sh", ".md", ".rst", ".txt")):
        lines = text.split("\n")
        numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
        output = "\n".join(numbered)
    else:
        output = text

    if len(output) > 50000:
        output = output[:50000] + "\n\n...[truncated]"

    return f"# {repo_id}/{path}\n\n{output}", True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_readme(repo_id: str, repo_type: str = "model") -> str | None:
    """Fetch the README.md from a Hugging Face repo. Returns None on failure."""
    if repo_type == "dataset":
        url = f"{HF_API}/datasets/{repo_id}/resolve/main/README.md"
    else:
        url = f"{HF_API}/{repo_id}/resolve/main/README.md"

    try:
        resp = await fetch_with_retry(url, headers=_headers(), timeout=30, max_retries=2)
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    content = resp.text
    # Strip YAML frontmatter (common in HF READMEs)
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3 :].strip()

    if len(content) > 30000:
        content = content[:30000] + "\n\n...[truncated]"

    return content
