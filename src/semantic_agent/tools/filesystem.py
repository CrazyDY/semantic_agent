"""Workspace-confined file-system tools."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


class FileSystemTools:
    """Perform ordinary file operations without allowing paths outside a workspace."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def _path(self, path: str) -> Path:
        candidate = (self.workspace_root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        if not candidate.is_relative_to(self.workspace_root):
            raise ValueError("Path must be inside the configured workspace")
        return candidate

    def read_file(self, path: str, encoding: str = "utf-8") -> dict[str, str]:
        target = self._path(path)
        if not target.is_file():
            raise ValueError(f"Not a file: {path}")
        return {"path": str(target.relative_to(self.workspace_root)), "content": target.read_text(encoding=encoding)}

    def write_file(self, path: str, content: str, append: bool = False, encoding: str = "utf-8") -> dict[str, Any]:
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a" if append else "w", encoding=encoding) as output:
            output.write(content)
        return {"path": str(target.relative_to(self.workspace_root)), "bytes_written": len(content.encode(encoding))}

    def list_files(self, path: str = ".", recursive: bool = False) -> dict[str, list[str]]:
        target = self._path(path)
        if not target.is_dir():
            raise ValueError(f"Not a directory: {path}")
        entries = target.rglob("*") if recursive else target.iterdir()
        return {
            "path": str(target.relative_to(self.workspace_root)) or ".",
            "entries": sorted(
                str(item.relative_to(self.workspace_root)) + ("/" if item.is_dir() else "")
                for item in entries
            ),
        }

    def create_directory(self, path: str) -> dict[str, str]:
        target = self._path(path)
        target.mkdir(parents=True, exist_ok=True)
        return {"path": str(target.relative_to(self.workspace_root))}

    def move_path(self, source: str, destination: str) -> dict[str, str]:
        source_path = self._path(source)
        destination_path = self._path(destination)
        if not source_path.exists():
            raise FileNotFoundError(source)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination_path))
        return {"source": source, "destination": str(destination_path.relative_to(self.workspace_root))}

    def copy_path(self, source: str, destination: str) -> dict[str, str]:
        source_path = self._path(source)
        destination_path = self._path(destination)
        if not source_path.exists():
            raise FileNotFoundError(source)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, destination_path)
        return {"source": source, "destination": str(destination_path.relative_to(self.workspace_root))}

    def delete_path(self, path: str, recursive: bool = False) -> dict[str, str]:
        target = self._path(path)
        if target == self.workspace_root:
            raise ValueError("The workspace root cannot be deleted")
        if not target.exists():
            raise FileNotFoundError(path)
        if target.is_dir():
            if not recursive:
                raise ValueError("Deleting a directory requires recursive=true")
            shutil.rmtree(target)
        else:
            target.unlink()
        return {"path": path}
