"""Compute Node Manager — registry, validation, and lifecycle."""

from pathlib import Path


class ComputeManager:
    """High-level operations for compute node management."""

    def __init__(self, key_manager):
        self.key_manager = key_manager

    def validate_node_config(self, node_type: str, config: dict) -> tuple[bool, str]:
        """Validate a compute node configuration. Pure check, no side effects."""
        if node_type == "ssh":
            return self._validate_ssh_config(config)
        elif node_type == "local":
            return self._validate_local_config(config)
        elif node_type == "modal":
            return self._validate_modal_config(config)
        else:
            return False, f"Unknown node type: {node_type}"

    def _validate_ssh_config(self, config: dict) -> tuple[bool, str]:
        required = ["host", "username"]
        for field in required:
            if not config.get(field):
                return False, f"SSH config requires '{field}'"

        key_filename = config.get("key_filename")
        if key_filename and not self.key_manager.key_exists(key_filename):
            return False, f"SSH key not found: {key_filename}"

        return True, ""

    def _validate_local_config(self, config: dict) -> tuple[bool, str]:
        workdir = config.get("workdir", "")
        if workdir:
            path = Path(workdir).expanduser()
            # Only validate — don't create directories as a side effect
            if path.exists() and not path.is_dir():
                return False, f"Path exists but is not a directory: {path}"
        return True, ""

    def _validate_modal_config(self, config: dict) -> tuple[bool, str]:
        return True, ""
