"""SSH Key Asset Manager — handles .keys/ directory lifecycle."""

import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa


class KeyManager:
    """Manages SSH private keys stored in a dedicated directory."""

    def __init__(self, keys_dir: str | Path = None):
        self.keys_dir = (
            Path(keys_dir) if keys_dir else Path(__file__).parent.parent.parent.parent / ".keys"
        )
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure .keys/ directory exists with correct permissions."""
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        # Set directory permissions to 0o700 (owner read/write/execute only)
        os.chmod(self.keys_dir, 0o700)

    def list_keys(self) -> list[dict]:
        """List all key files (metadata only, no private content)."""
        keys = []
        for path in sorted(self.keys_dir.glob("id_*")):
            if path.suffix == ".pub":
                continue
            pub_path = path.with_suffix(path.suffix + ".pub")
            keys.append(
                {
                    "filename": path.name,
                    "has_public": pub_path.exists(),
                    "size_bytes": path.stat().st_size,
                }
            )
        return keys

    def key_exists(self, filename: str) -> bool:
        """Check if a key file exists."""
        return (self.keys_dir / filename).exists()

    def get_key_path(self, filename: str) -> Path:
        """Get the absolute path to a key file."""
        return self.keys_dir / filename

    def write_key(self, filename: str, private_key_pem: str | bytes) -> Path:
        """Write a private key to disk with restrictive permissions."""
        key_path = self.keys_dir / filename
        if isinstance(private_key_pem, str):
            private_key_pem = private_key_pem.encode("utf-8")

        key_path.write_bytes(private_key_pem)
        # Set file permissions to 0o600 (owner read/write only)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
        return key_path

    def read_key(self, filename: str) -> str:
        """Read a private key from disk. Use sparingly."""
        key_path = self.keys_dir / filename
        if not key_path.exists():
            raise FileNotFoundError(f"Key not found: {filename}")
        return key_path.read_text("utf-8")

    def delete_key(self, filename: str) -> bool:
        """Delete a key pair from disk."""
        key_path = self.keys_dir / filename
        pub_path = key_path.with_suffix(key_path.suffix + ".pub")
        deleted = False
        if key_path.exists():
            key_path.unlink()
            deleted = True
        if pub_path.exists():
            pub_path.unlink()
            deleted = True
        return deleted

    def generate_key_pair(
        self, filename: str, algorithm: str = "ed25519", comment: str = ""
    ) -> tuple[Path, Path]:
        """Generate a new SSH key pair and write to disk."""
        key_path = self.keys_dir / filename
        pub_path = key_path.with_suffix(key_path.suffix + ".pub")

        if algorithm == "ed25519":
            private_key = ed25519.Ed25519PrivateKey.generate()
            private_pem = private_key.private_bytes(
                encoding=crypto_serialization.Encoding.PEM,
                format=crypto_serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=crypto_serialization.NoEncryption(),
            )
            public_bytes = private_key.public_key().public_bytes(
                encoding=crypto_serialization.Encoding.OpenSSH,
                format=crypto_serialization.PublicFormat.OpenSSH,
            )
        elif algorithm == "rsa":
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
            private_pem = private_key.private_bytes(
                encoding=crypto_serialization.Encoding.PEM,
                format=crypto_serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=crypto_serialization.NoEncryption(),
            )
            public_bytes = private_key.public_key().public_bytes(
                encoding=crypto_serialization.Encoding.OpenSSH,
                format=crypto_serialization.PublicFormat.OpenSSH,
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}. Use 'ed25519' or 'rsa'.")

        # Write private key with 0o600
        key_path.write_bytes(private_pem)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

        # Write public key with 0o644
        pub_pem = public_bytes + (f" {comment}".encode() if comment else b"")
        pub_path.write_bytes(pub_pem)
        os.chmod(pub_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

        return key_path, pub_path

    def validate_key(self, private_key_pem: str | bytes) -> dict:
        """Validate an SSH private key and return metadata."""
        if isinstance(private_key_pem, str):
            private_key_pem = private_key_pem.encode("utf-8")

        # Try to load as OpenSSH format
        try:
            key = crypto_serialization.load_ssh_private_key(private_key_pem, password=None)
        except Exception:
            # Try PEM format
            try:
                key = crypto_serialization.load_pem_private_key(private_key_pem, password=None)
            except Exception as e:
                raise ValueError(f"Invalid private key: {e}")

        # Determine algorithm
        key_type = type(key).__name__.lower()
        if "ed25519" in key_type:
            algorithm = "ssh-ed25519"
        elif "rsa" in key_type:
            algorithm = "ssh-rsa"
        else:
            algorithm = key_type

        # Generate public key for fingerprint
        public_key = key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=crypto_serialization.Encoding.OpenSSH,
            format=crypto_serialization.PublicFormat.OpenSSH,
        )

        # Compute SHA256 fingerprint matching ssh-keygen format:
        # The fingerprint is the SHA256 of the raw key blob (base64-decoded
        # portion of the OpenSSH public key line), base64-encoded.
        import base64
        import hashlib

        pub_line = public_bytes.decode("utf-8").strip()
        # OpenSSH format: "ssh-ed25519 AAAA... comment"
        parts = pub_line.split()
        if len(parts) >= 2:
            key_blob = base64.b64decode(parts[1])
        else:
            key_blob = public_bytes
        raw_hash = hashlib.sha256(key_blob).digest()
        fingerprint = base64.b64encode(raw_hash).decode("ascii").rstrip("=")

        return {
            "algorithm": algorithm,
            "fingerprint": f"SHA256:{fingerprint}",
            "public_key": pub_line,
        }
