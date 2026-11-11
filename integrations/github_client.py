"""
TechSpecAnalyser — GitHub REST API Client.
Communicates with GitHub API with optional Personal Access Token authentication,
rate limit inspection, branch/commit resolution, tree retrieval, and commit comparison.
"""
import base64
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import GITHUB_API_BASE, get_github_token


class GitHubClient:
    """Wrapper for GitHub REST API v3."""

    def __init__(self, token: Optional[str] = None):
        self.token = get_github_token(token)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TechSpecAnalyser-Platform/2.0",
        })
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"

    @staticmethod
    def parse_repo_url(url_or_slug: str) -> Tuple[str, str]:
        """
        Extracts (owner, repo) from GitHub URL or slug.
        Accepts: https://github.com/owner/repo, github.com/owner/repo, owner/repo.
        """
        raw = url_or_slug.strip().rstrip("/")
        # Remove trailing .git
        if raw.endswith(".git"):
            raw = raw[:-4]

        # Match https?://github.com/owner/repo
        match = re.search(r"github\.com[/:]([\w\.-]+)/([\w\.-]+)", raw)
        if match:
            return match.group(1), match.group(2)

        # Match owner/repo
        parts = raw.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

        raise ValueError(f"Invalid GitHub repository identifier: `{url_or_slug}`. Expected format: `owner/repo` or full URL.")

    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetches repository metadata."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        resp = self.session.get(url, timeout=10)
        self._check_response(resp)
        return resp.json()

    def get_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Lists repository branches."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches"
        resp = self.session.get(url, params={"per_page": 30}, timeout=10)
        self._check_response(resp)
        return resp.json()

    def get_commits(self, owner: str, repo: str, branch: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists recent commits for a branch."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
        params = {"per_page": 20}
        if branch:
            params["sha"] = branch
        resp = self.session.get(url, params=params, timeout=10)
        self._check_response(resp)
        return resp.json()

    def get_commit(self, owner: str, repo: str, commit_sha: str) -> Dict[str, Any]:
        """Gets detailed commit info including modified files."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{commit_sha}"
        resp = self.session.get(url, timeout=10)
        self._check_response(resp)
        return resp.json()

    def compare_commits(self, owner: str, repo: str, base: str, head: str) -> Dict[str, Any]:
        """Compares two commits or branches to identify changed files."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/compare/{base}...{head}"
        resp = self.session.get(url, timeout=12)
        self._check_response(resp)
        return resp.json()

    def get_tree(self, owner: str, repo: str, tree_sha: str, recursive: bool = True) -> Dict[str, Any]:
        """Gets git tree recursively."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{tree_sha}"
        params = {"recursive": "1"} if recursive else {}
        resp = self.session.get(url, params=params, timeout=15)
        self._check_response(resp)
        return resp.json()

    def get_blob_content(self, owner: str, repo: str, file_sha: str) -> str:
        """Retrieves and decodes raw text from blob SHA."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/blobs/{file_sha}"
        resp = self.session.get(url, timeout=10)
        self._check_response(resp)
        data = resp.json()
        encoding = data.get("encoding", "base64")
        raw_content = data.get("content", "")
        if encoding == "base64":
            return base64.b64decode(raw_content).decode("utf-8", errors="replace")
        return raw_content

    def get_rate_limit(self) -> Dict[str, Any]:
        """Checks rate limit status."""
        url = f"{GITHUB_API_BASE}/rate_limit"
        try:
            resp = self.session.get(url, timeout=5)
            return resp.json()
        except Exception:
            return {"rate": {"limit": 60, "remaining": 60, "reset": 0}}

    def _check_response(self, resp: requests.Response) -> None:
        if resp.status_code == 401:
            raise PermissionError("GitHub API authorization failed. Check your GitHub Personal Access Token.")
        elif resp.status_code == 403:
            rem = resp.headers.get("X-RateLimit-Remaining", "0")
            if rem == "0":
                raise PermissionError("GitHub API rate limit exceeded. Provide a Personal Access Token in the sidebar to increase your hourly quota.")
            raise PermissionError(f"GitHub access forbidden (403): {resp.text}")
        elif resp.status_code == 404:
            raise FileNotFoundError("GitHub repository, branch, or file not found. If this repository is private, provide a GitHub Personal Access Token.")
        elif not resp.ok:
            raise RuntimeError(f"GitHub API error ({resp.status_code}): {resp.text[:200]}")
