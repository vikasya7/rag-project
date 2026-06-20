"""Walks a repo directory and returns paths to source files worth indexing."""

from pathlib import Path


SUPPORTED_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py"}

IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", ".next",
    "venv", "__pycache__", ".turbo", "env", ".venv",
}

def walk_repo(root_dir: str) -> list[str]:
    files: list[str] = []
    root = Path(root_dir)

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix in SUPPORTED_EXTENSIONS:
            files.append(str(path))

    return files