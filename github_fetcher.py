"""Fetch bounded source-code snapshots from public GitHub repositories (no token needed)."""

import base64
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
MAX_FILES = 30
MAX_FILE_BYTES = 200 * 1024
REQUEST_TIMEOUT_SECONDS = 15

SUPPORTED_EXTENSIONS = {
    ".py": "Python", ".java": "Java",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".h": "C++",
    ".js": "JavaScript", ".jsx": "JSX", ".ts": "TypeScript", ".tsx": "TSX",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
}
EXCLUDED_DIRECTORIES = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules", "vendor", "vendors",
    "dist", "build", "target", "site-packages", "coverage", ".next", ".idea", ".vscode",
}


class GitHubFetchError(Exception):
    """An expected input, repository, or GitHub API error."""


def parse_github_url(repository_url: str) -> tuple[str, str, str | None]:
    """Return owner, repository and an optional branch from a GitHub URL."""
    if not isinstance(repository_url, str) or not repository_url.strip():
        raise GitHubFetchError("Enter a public GitHub repository URL.")
    parsed = urlparse(repository_url.strip())
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("github.com", "www.github.com"):
        raise GitHubFetchError("Use a URL in the form https://github.com/owner/repository.")
    if parsed.username or parsed.password:
        raise GitHubFetchError("Credentials are not allowed in the repository URL.")

    parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise GitHubFetchError("The URL must include both an owner and repository name.")
    owner, repository = parts[0], parts[1]
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository or owner in (".", "..") or repository in (".", ".."):
        raise GitHubFetchError("The GitHub repository URL is invalid.")

    branch = None
    if len(parts) >= 4 and parts[2] in ("tree", "blob"):
        branch = _resolve_url_branch(owner, repository, parts[3:])
    return owner, repository, branch


def _resolve_url_branch(owner: str, repository: str, path_parts: list[str]) -> str:
    """GitHub URLs do not separate branch from path; pick the longest existing branch."""
    if len(path_parts) == 1:
        return path_parts[0]
    for length in range(len(path_parts), 0, -1):
        candidate = "/".join(path_parts[:length])
        endpoint = "{}/repos/{}/{}/git/ref/heads/{}".format(
            API_ROOT, quote(owner, safe=""), quote(repository, safe=""), quote(candidate, safe="/"))
        try:
            _github_get(endpoint)
        except GitHubFetchError:
            continue
        return candidate
    return "/".join(path_parts)


def _github_get(url: str) -> dict[str, Any]:
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AI-Code-Reviewer",
    })
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(body).get("message", "")
        except (ValueError, AttributeError):
            message = ""
        if exc.code == 403 and ("rate limit" in message.lower() or exc.headers.get("X-RateLimit-Remaining") == "0"):
            raise GitHubFetchError("GitHub API rate limit reached (60 requests/hour without a token). Wait and try again.") from exc
        if exc.code == 404:
            raise GitHubFetchError("Repository or branch not found, or the repository is not public.") from exc
        raise GitHubFetchError("GitHub API request failed (HTTP {}). {}".format(exc.code, message or "Please try again.")) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise GitHubFetchError("Could not connect to GitHub: {}".format(exc)) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise GitHubFetchError("GitHub returned an unreadable API response.") from exc


def _is_supported_source(path: str) -> bool:
    components = path.replace("\\", "/").split("/")
    if any(c.lower() in EXCLUDED_DIRECTORIES for c in components[:-1]):
        return False
    if any(c.startswith(".") for c in components[:-1]):
        return False
    return os.path.splitext(components[-1])[1].lower() in SUPPORTED_EXTENSIONS


def _fetch_file(owner: str, repository: str, branch: str, path: str) -> str:
    endpoint = "{}/repos/{}/{}/contents/{}?ref={}".format(
        API_ROOT, quote(owner, safe=""), quote(repository, safe=""), quote(path, safe="/"), quote(branch, safe=""))
    payload = _github_get(endpoint)
    if payload.get("type") != "file" or payload.get("encoding") != "base64":
        raise GitHubFetchError("GitHub did not return a readable text file.")
    try:
        content = base64.b64decode(payload.get("content", "")).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise GitHubFetchError("The file is binary or is not valid UTF-8 text.") from exc
    if "\x00" in content:
        raise GitHubFetchError("The file appears to be binary and was skipped.")
    return content


def fetch_public_repository(repository_url: str, max_files: int | None = None) -> dict[str, Any]:
    """Fetch repository metadata and a capped set of supported source files.

    ``max_files`` lowers the cap (never raises it above MAX_FILES), which also
    saves GitHub API requests. One failing file never stops the others.
    """
    cap = min(max_files, MAX_FILES) if max_files else MAX_FILES
    owner, repository, url_branch = parse_github_url(repository_url)
    metadata = _github_get("{}/repos/{}/{}".format(API_ROOT, quote(owner, safe=""), quote(repository, safe="")))
    if metadata.get("private"):
        raise GitHubFetchError("Only public repositories can be reviewed.")

    default_branch = metadata.get("default_branch")
    branch = url_branch or default_branch
    if not branch:
        raise GitHubFetchError("GitHub did not provide a default branch for this repository.")

    tree_data = _github_get("{}/repos/{}/{}/git/trees/{}?recursive=1".format(
        API_ROOT, quote(owner, safe=""), quote(repository, safe=""), quote(branch, safe="")))
    blobs = [i for i in tree_data.get("tree", []) if i.get("type") == "blob"]
    supported = [i for i in blobs if _is_supported_source(i.get("path", ""))]
    oversized = [i for i in supported if not isinstance(i.get("size"), int) or i["size"] > MAX_FILE_BYTES]
    candidates = [i for i in supported if i not in oversized]
    # Python first, then shallow paths: usually the most informative files.
    candidates.sort(key=lambda i: (not i["path"].endswith(".py"), i["path"].count("/"), i["path"]))

    files, fetch_errors = [], []
    selected = candidates[:cap]
    for item in selected:
        path = item["path"]
        try:
            content = _fetch_file(owner, repository, branch, path)
            if len(content.encode("utf-8")) > MAX_FILE_BYTES:
                oversized.append({"path": path})
                continue
            files.append({
                "path": path,
                "language": SUPPORTED_EXTENSIONS[os.path.splitext(path)[1].lower()],
                "content": content,
                "size": item["size"],
            })
        except GitHubFetchError as exc:
            fetch_errors.append({"path": path, "error": str(exc)})

    return {
        "owner": owner,
        "name": metadata.get("name", repository),
        "full_name": metadata.get("full_name", "{}/{}".format(owner, repository)),
        "description": metadata.get("description") or "",
        "html_url": metadata.get("html_url", "https://github.com/{}/{}".format(owner, repository)),
        "branch": branch,
        "default_branch": default_branch,
        "source_files_detected": len(candidates),
        "unsupported_files_skipped": len(blobs) - len(supported),
        "oversized_files_skipped": len(oversized),
        "file_limit_skipped": len(candidates) - len(selected),
        "files_fetched_successfully": len(files),
        "files_fetched_failed": len(fetch_errors),
        "files": files,
        "files_limited": len(candidates) > cap,
        "tree_truncated": bool(tree_data.get("truncated")),
        "fetch_errors": fetch_errors,
    }
