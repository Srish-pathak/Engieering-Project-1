"""
TechSpecAnalyser — GitHub Repository Fetcher & Filter Engine.
Enforces safeguards: max file limits, max file sizes, directory exclusion,
and per-file failure isolation.
"""
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import (
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_REPO_FILES,
    EXTENSION_TO_LANGUAGE,
    IGNORED_DIRECTORIES,
    IGNORED_EXTENSIONS,
    detect_language,
)
from integrations.github_client import GitHubClient


class GitHubFetcher:
    """Safely retrieves and filters supported repository source files."""

    def __init__(
        self,
        client: Optional[GitHubClient] = None,
        max_files: int = DEFAULT_MAX_REPO_FILES,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ):
        self.client = client or GitHubClient()
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes

    def is_eligible_file(self, path: str, size: Optional[int] = None) -> bool:
        """Determines if a repository path should be reviewed."""
        # 1. Size check
        if size is not None and size > self.max_file_bytes:
            return False

        # 2. Path components check for ignored directories
        p = Path(path)
        parts = set(p.parts)
        if any(ignored in parts for ignored in IGNORED_DIRECTORIES):
            return False

        # 3. Check for hidden folders/files
        if any(part.startswith(".") for part in p.parts[:-1]):
            return False

        # 4. Check extension
        ext = p.suffix.lower()
        if ext in IGNORED_EXTENSIONS:
            return False

        return ext in EXTENSION_TO_LANGUAGE

    def fetch_repository_files(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        progress_cb: Optional[Callable[[str, float], None]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches repository tree and downloads eligible source files.
        Returns (downloaded_files, fetch_metadata).
        """
        cb = progress_cb or (lambda msg, pct: None)
        cb("Fetching repository metadata...", 0.1)

        repo_meta = self.client.get_repo(owner, repo)
        target_branch = branch or repo_meta.get("default_branch", "main")

        cb(f"Resolving branch '{target_branch}' tree...", 0.2)
        commits = self.client.get_commits(owner, repo, branch=target_branch)
        if not commits:
            raise ValueError(f"No commits found on branch '{target_branch}'.")

        head_commit = commits[0]
        tree_sha = head_commit["commit"]["tree"]["sha"]

        cb("Retrieving git tree...", 0.3)
        tree_data = self.client.get_tree(owner, repo, tree_sha, recursive=True)
        raw_entries = tree_data.get("tree", [])

        # Filter candidate files
        candidates = []
        for entry in raw_entries:
            if entry.get("type") == "blob":
                path = entry.get("path", "")
                size = entry.get("size", 0)
                if self.is_eligible_file(path, size):
                    candidates.append(entry)

        # Truncate to maximum limit
        selected_entries = candidates[: self.max_files]
        total_selected = len(selected_entries)

        downloaded_files: List[Dict[str, Any]] = []
        failed_files: List[Dict[str, str]] = []

        for idx, entry in enumerate(selected_entries, 1):
            path = entry["path"]
            sha = entry["sha"]
            pct = 0.3 + 0.6 * (idx / max(total_selected, 1))
            cb(f"Downloading [{idx}/{total_selected}]: {path}", pct)

            try:
                content = self.client.get_blob_content(owner, repo, sha)
                downloaded_files.append({
                    "path": path,
                    "content": content,
                    "sha": sha,
                    "size": entry.get("size", len(content)),
                    "language": detect_language(path),
                })
            except Exception as e:
                # Per-file failure isolation
                failed_files.append({"path": path, "error": str(e)})

        cb("Download complete.", 1.0)

        metadata = {
            "owner": owner,
            "repo": repo,
            "branch": target_branch,
            "head_commit_sha": head_commit["sha"][:7],
            "commit_message": head_commit["commit"]["message"].splitlines()[0],
            "total_tree_files": len(raw_entries),
            "eligible_files_count": len(candidates),
            "downloaded_count": len(downloaded_files),
            "failed_files": failed_files,
        }

        return downloaded_files, metadata

    def fetch_changed_files_between_commits(
        self,
        owner: str,
        repo: str,
        base_sha: str,
        head_sha: str,
    ) -> List[Dict[str, Any]]:
        """Compares two commits and downloads only modified/added eligible files."""
        diff_data = self.client.compare_commits(owner, repo, base_sha, head_sha)
        changed_entries = diff_data.get("files", [])

        downloaded = []
        for item in changed_entries:
            filename = item.get("filename", "")
            status = item.get("status", "")  # modified, added, removed
            if status != "removed" and self.is_eligible_file(filename):
                try:
                    # Fetch blob
                    sha = item.get("sha")
                    if sha:
                        content = self.client.get_blob_content(owner, repo, sha)
                        downloaded.append({
                            "path": filename,
                            "content": content,
                            "language": detect_language(filename),
                            "status": status,
                            "additions": item.get("additions", 0),
                            "deletions": item.get("deletions", 0),
                        })
                except Exception:
                    continue
        return downloaded
