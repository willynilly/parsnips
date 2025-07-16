import subprocess
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator

from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class GitRemoteUrl(ParsnipsBaseModel):
    repo_path: Path = Field(default_factory=lambda: Path("."))
    url: Optional[str] = None

    @classmethod
    def from_repo(cls, repo_path: Path | None = None):
        if repo_path is None:
            repo_path = Path(".")
        try:
            raw_url = subprocess.check_output(
                ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
                text=True
            ).strip()
            url = cls.normalize_git_url(raw_url)
            return cls(repo_path=repo_path, url=url)
        except subprocess.CalledProcessError:
            return cls(repo_path=repo_path, url=None)

    @staticmethod
    def normalize_git_url(url: str) -> str:
        if url.startswith("git@"):
            url = url.replace(":", "/", 1).replace("git@", "https://")
        return url

    @field_validator("repo_path", mode="before")
    @classmethod
    def convert_str_to_path(cls, v):
        return Path(v) if not isinstance(v, Path) else v
