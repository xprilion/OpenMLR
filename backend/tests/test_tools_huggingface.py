"""Tests for Hugging Face Hub tools — tool specs, headers, and handler logic."""

from unittest.mock import MagicMock, patch

import pytest

from openmlr.tools.huggingface import (
    _fetch_readme,
    _handle_dataset_info,
    _handle_model_info,
    _handle_read_file,
    _handle_search_datasets,
    _handle_search_models,
    _headers,
    create_huggingface_tools,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


class TestCreateHuggingfaceTools:
    async def test_creates_all_tools(self):
        tools = create_huggingface_tools()
        names = [t.name for t in tools]
        assert "hf_search_models" in names
        assert "hf_model_info" in names
        assert "hf_search_datasets" in names
        assert "hf_dataset_info" in names
        assert "hf_read_file" in names
        assert len(tools) == 5

    async def test_all_tools_have_handlers(self):
        tools = create_huggingface_tools()
        for tool in tools:
            assert tool.handler is not None, f"{tool.name} has no handler"

    async def test_all_tools_have_descriptions(self):
        tools = create_huggingface_tools()
        for tool in tools:
            assert len(tool.description) > 10, f"{tool.name} description too short"

    async def test_all_tools_have_valid_parameters(self):
        tools = create_huggingface_tools()
        for tool in tools:
            assert tool.parameters["type"] == "object"
            assert "properties" in tool.parameters
            assert "required" in tool.parameters


class TestSearchModelsSpec:
    async def test_required_params(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_search_models"][0]
        assert "query" in tool.parameters["required"]

    async def test_optional_params(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_search_models"][0]
        props = tool.parameters["properties"]
        assert "pipeline_tag" in props
        assert "library" in props
        assert "sort" in props
        assert "limit" in props

    async def test_sort_enum(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_search_models"][0]
        sort_prop = tool.parameters["properties"]["sort"]
        assert "enum" in sort_prop
        assert "downloads" in sort_prop["enum"]
        assert "likes" in sort_prop["enum"]
        assert "trending" in sort_prop["enum"]


class TestModelInfoSpec:
    async def test_required_params(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_model_info"][0]
        assert "repo_id" in tool.parameters["required"]

    async def test_include_readme_param(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_model_info"][0]
        assert "include_readme" in tool.parameters["properties"]
        assert tool.parameters["properties"]["include_readme"]["type"] == "boolean"


class TestSearchDatasetsSpec:
    async def test_required_params(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_search_datasets"][0]
        assert "query" in tool.parameters["required"]

    async def test_task_filter_param(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_search_datasets"][0]
        assert "task" in tool.parameters["properties"]


class TestDatasetInfoSpec:
    async def test_required_params(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_dataset_info"][0]
        assert "repo_id" in tool.parameters["required"]


class TestReadFileSpec:
    async def test_required_params(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_read_file"][0]
        required = tool.parameters["required"]
        assert "repo_id" in required
        assert "path" in required

    async def test_repo_type_enum(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_read_file"][0]
        repo_type = tool.parameters["properties"]["repo_type"]
        assert "enum" in repo_type
        assert "model" in repo_type["enum"]
        assert "dataset" in repo_type["enum"]
        assert "space" in repo_type["enum"]

    async def test_revision_param(self):
        tools = create_huggingface_tools()
        tool = [t for t in tools if t.name == "hf_read_file"][0]
        assert "revision" in tool.parameters["properties"]


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------


class TestHeaders:
    async def test_headers_without_token(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        h = _headers()
        assert "Authorization" not in h

    async def test_headers_with_token(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_test123")
        h = _headers()
        assert h["Authorization"] == "Bearer hf_test123"

    async def test_headers_returns_dict(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        h = _headers()
        assert isinstance(h, dict)


# ---------------------------------------------------------------------------
# Handler tests (mocked HTTP)
# ---------------------------------------------------------------------------


def _mock_response(status_code=200, json_data=None, text="", headers=None):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.headers = headers or {}
    resp.content = text.encode() if isinstance(text, str) else b""
    return resp


class TestHandleSearchModels:
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_successful_search(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            json_data=[
                {
                    "modelId": "meta-llama/Llama-3-8B",
                    "downloads": 1000000,
                    "likes": 500,
                    "pipeline_tag": "text-generation",
                    "tags": ["transformers", "safetensors", "pytorch"],
                },
                {
                    "modelId": "mistralai/Mistral-7B-v0.1",
                    "downloads": 500000,
                    "likes": 300,
                    "pipeline_tag": "text-generation",
                    "tags": ["transformers"],
                },
            ]
        )
        result, success = await _handle_search_models("llama")
        assert success is True
        assert "meta-llama/Llama-3-8B" in result
        assert "mistralai/Mistral-7B-v0.1" in result
        assert "1,000,000 downloads" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_empty_results(self, mock_fetch):
        mock_fetch.return_value = _mock_response(json_data=[])
        result, success = await _handle_search_models("nonexistent_model_xyz")
        assert success is True
        assert "No models found" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_api_error(self, mock_fetch):
        mock_fetch.return_value = _mock_response(status_code=500, text="Internal Server Error")
        result, success = await _handle_search_models("test")
        assert success is False
        assert "error" in result.lower()

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_rate_limit(self, mock_fetch):
        from openmlr.tools.http_utils import RateLimitError

        mock_fetch.side_effect = RateLimitError()
        result, success = await _handle_search_models("test")
        assert success is False
        assert "rate limit" in result.lower()

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_network_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection refused")
        result, success = await _handle_search_models("test")
        assert success is False
        assert "error" in result.lower()

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_passes_pipeline_tag(self, mock_fetch):
        mock_fetch.return_value = _mock_response(json_data=[])
        await _handle_search_models("llama", pipeline_tag="text-generation")
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["params"]["pipeline_tag"] == "text-generation"

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_passes_library_filter(self, mock_fetch):
        mock_fetch.return_value = _mock_response(json_data=[])
        await _handle_search_models("llama", library="transformers")
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["params"]["library"] == "transformers"

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_respects_limit(self, mock_fetch):
        mock_fetch.return_value = _mock_response(json_data=[])
        await _handle_search_models("llama", limit=5)
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["params"]["limit"] == 5

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_limit_capped_at_50(self, mock_fetch):
        mock_fetch.return_value = _mock_response(json_data=[])
        await _handle_search_models("llama", limit=100)
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["params"]["limit"] == 50


class TestHandleModelInfo:
    @patch("openmlr.tools.huggingface._fetch_readme")
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_successful_info(self, mock_fetch, mock_readme):
        mock_fetch.return_value = _mock_response(
            json_data={
                "modelId": "meta-llama/Llama-3-8B",
                "pipeline_tag": "text-generation",
                "library_name": "transformers",
                "downloads": 1000000,
                "likes": 500,
                "author": "meta-llama",
                "lastModified": "2024-01-15T00:00:00Z",
                "tags": ["transformers", "safetensors", "text-generation"],
                "siblings": [
                    {"rfilename": "config.json"},
                    {"rfilename": "model.safetensors"},
                ],
            }
        )
        mock_readme.return_value = "This is a model card."
        result, success = await _handle_model_info("meta-llama/Llama-3-8B")
        assert success is True
        assert "meta-llama/Llama-3-8B" in result
        assert "text-generation" in result
        assert "transformers" in result
        assert "1,000,000" in result
        assert "config.json" in result
        assert "This is a model card." in result

    @patch("openmlr.tools.huggingface._fetch_readme")
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_not_found(self, mock_fetch, mock_readme):
        mock_fetch.return_value = _mock_response(status_code=404)
        result, success = await _handle_model_info("nonexistent/model")
        assert success is False
        assert "not found" in result.lower()

    @patch("openmlr.tools.huggingface._fetch_readme")
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_skip_readme(self, mock_fetch, mock_readme):
        mock_fetch.return_value = _mock_response(
            json_data={"modelId": "test/model", "downloads": 0, "likes": 0, "tags": []}
        )
        await _handle_model_info("test/model", include_readme=False)
        mock_readme.assert_not_called()

    @patch("openmlr.tools.huggingface._fetch_readme")
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_rate_limit(self, mock_fetch, mock_readme):
        from openmlr.tools.http_utils import RateLimitError

        mock_fetch.side_effect = RateLimitError()
        result, success = await _handle_model_info("test/model")
        assert success is False
        assert "rate limit" in result.lower()

    @patch("openmlr.tools.huggingface._fetch_readme")
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_truncates_long_output(self, mock_fetch, mock_readme):
        mock_fetch.return_value = _mock_response(
            json_data={"modelId": "test/model", "downloads": 0, "likes": 0, "tags": []}
        )
        mock_readme.return_value = "x" * 60000
        result, success = await _handle_model_info("test/model")
        assert success is True
        assert len(result) <= 50100  # 50000 + "[truncated]" overhead
        assert "truncated" in result.lower()


class TestHandleSearchDatasets:
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_successful_search(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            json_data=[
                {
                    "id": "tatsu-lab/alpaca",
                    "downloads": 200000,
                    "likes": 150,
                    "description": "A dataset for instruction tuning",
                    "tags": ["text-generation", "instruction-following"],
                },
            ]
        )
        result, success = await _handle_search_datasets("alpaca")
        assert success is True
        assert "tatsu-lab/alpaca" in result
        assert "200,000 downloads" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_empty_results(self, mock_fetch):
        mock_fetch.return_value = _mock_response(json_data=[])
        result, success = await _handle_search_datasets("nonexistent_dataset")
        assert success is True
        assert "No datasets found" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_passes_task_filter(self, mock_fetch):
        mock_fetch.return_value = _mock_response(json_data=[])
        await _handle_search_datasets("test", task="text-classification")
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["params"]["task_categories"] == "text-classification"


class TestHandleDatasetInfo:
    @patch("openmlr.tools.huggingface._fetch_readme")
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_successful_info(self, mock_fetch, mock_readme):
        mock_fetch.return_value = _mock_response(
            json_data={
                "id": "tatsu-lab/alpaca",
                "downloads": 200000,
                "likes": 150,
                "author": "tatsu-lab",
                "tags": ["text-generation"],
                "description": "Instruction tuning dataset",
                "siblings": [{"rfilename": "data.json"}],
            }
        )
        mock_readme.return_value = "Dataset card content."
        result, success = await _handle_dataset_info("tatsu-lab/alpaca")
        assert success is True
        assert "tatsu-lab/alpaca" in result
        assert "200,000" in result
        assert "Dataset card content." in result

    @patch("openmlr.tools.huggingface._fetch_readme")
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_not_found(self, mock_fetch, mock_readme):
        mock_fetch.return_value = _mock_response(status_code=404)
        result, success = await _handle_dataset_info("nonexistent/dataset")
        assert success is False
        assert "not found" in result.lower()


class TestHandleReadFile:
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_read_json_file(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            text='{"hidden_size": 4096}',
            headers={"content-type": "application/json"},
        )
        result, success = await _handle_read_file("meta-llama/Llama-3-8B", "config.json")
        assert success is True
        assert "hidden_size" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_read_python_file_with_line_numbers(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            text="import torch\nprint('hello')",
            headers={"content-type": "text/plain"},
        )
        result, success = await _handle_read_file("test/repo", "train.py")
        assert success is True
        assert "1: import torch" in result
        assert "2: print('hello')" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_binary_file_detection(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            text="",
            headers={"content-type": "application/octet-stream"},
        )
        result, success = await _handle_read_file("test/repo", "model.safetensors")
        assert success is True
        assert "Binary file" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_binary_extension_detection(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            text="",
            headers={"content-type": "text/plain"},
        )
        result, success = await _handle_read_file("test/repo", "weights.bin")
        assert success is True
        assert "Binary file" in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_file_not_found(self, mock_fetch):
        mock_fetch.return_value = _mock_response(status_code=404)
        result, success = await _handle_read_file("test/repo", "missing.txt")
        assert success is False
        assert "not found" in result.lower()

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_gated_model_401(self, mock_fetch):
        mock_fetch.return_value = _mock_response(status_code=401)
        result, success = await _handle_read_file("gated/model", "config.json")
        assert success is False
        assert "Access denied" in result or "gated" in result.lower()

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_forbidden_403(self, mock_fetch):
        mock_fetch.return_value = _mock_response(status_code=403)
        result, success = await _handle_read_file("gated/model", "config.json")
        assert success is False
        assert "Forbidden" in result or "license" in result.lower()

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_model_url_format(self, mock_fetch):
        mock_fetch.return_value = _mock_response(text="{}", headers={})
        await _handle_read_file("org/model", "config.json", repo_type="model")
        url = mock_fetch.call_args.args[0]
        assert url == "https://huggingface.co/org/model/resolve/main/config.json"

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_dataset_url_format(self, mock_fetch):
        mock_fetch.return_value = _mock_response(text="{}", headers={})
        await _handle_read_file("org/dataset", "data.json", repo_type="dataset")
        url = mock_fetch.call_args.args[0]
        assert url == "https://huggingface.co/datasets/org/dataset/resolve/main/data.json"

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_space_url_format(self, mock_fetch):
        mock_fetch.return_value = _mock_response(text="{}", headers={})
        await _handle_read_file("org/space", "app.py", repo_type="space")
        url = mock_fetch.call_args.args[0]
        assert url == "https://huggingface.co/spaces/org/space/resolve/main/app.py"

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_custom_revision(self, mock_fetch):
        mock_fetch.return_value = _mock_response(text="{}", headers={})
        await _handle_read_file("org/model", "config.json", revision="v2.0")
        url = mock_fetch.call_args.args[0]
        assert "/resolve/v2.0/" in url

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_truncates_long_content(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            text="x" * 60000,
            headers={"content-type": "text/plain"},
        )
        result, success = await _handle_read_file("test/repo", "big.json")
        assert success is True
        assert len(result) <= 50100
        assert "truncated" in result.lower()

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_rate_limit(self, mock_fetch):
        from openmlr.tools.http_utils import RateLimitError

        mock_fetch.side_effect = RateLimitError()
        result, success = await _handle_read_file("test/repo", "file.txt")
        assert success is False
        assert "rate limit" in result.lower()


# ---------------------------------------------------------------------------
# Helper: _fetch_readme
# ---------------------------------------------------------------------------


class TestFetchReadme:
    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_fetches_model_readme(self, mock_fetch):
        mock_fetch.return_value = _mock_response(text="# My Model\n\nThis is a model.")
        result = await _fetch_readme("org/model", "model")
        assert result == "# My Model\n\nThis is a model."
        url = mock_fetch.call_args.args[0]
        assert url == "https://huggingface.co/org/model/resolve/main/README.md"

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_fetches_dataset_readme(self, mock_fetch):
        mock_fetch.return_value = _mock_response(text="# My Dataset")
        await _fetch_readme("org/dataset", "dataset")
        url = mock_fetch.call_args.args[0]
        assert url == "https://huggingface.co/datasets/org/dataset/resolve/main/README.md"

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_strips_yaml_frontmatter(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            text="---\nlanguage: en\ntags:\n- llm\n---\n# Model Card\n\nContent here."
        )
        result = await _fetch_readme("org/model", "model")
        assert result.startswith("# Model Card")
        assert "language: en" not in result

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_returns_none_on_404(self, mock_fetch):
        mock_fetch.return_value = _mock_response(status_code=404)
        result = await _fetch_readme("org/model", "model")
        assert result is None

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_returns_none_on_exception(self, mock_fetch):
        mock_fetch.side_effect = Exception("Network error")
        result = await _fetch_readme("org/model", "model")
        assert result is None

    @patch("openmlr.tools.huggingface.fetch_with_retry")
    async def test_truncates_long_readme(self, mock_fetch):
        mock_fetch.return_value = _mock_response(text="x" * 40000)
        result = await _fetch_readme("org/model", "model")
        assert len(result) <= 30100
        assert "truncated" in result.lower()
