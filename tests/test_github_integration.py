"""
TechSpecAnalyser — GitHub Integration & Fetcher Test Suite.
Tests URL parsing, file eligibility filtering, rate limits, and per-file isolation.
"""
from unittest.mock import MagicMock
import pytest

from integrations.github_client import GitHubClient
from integrations.github_fetcher import GitHubFetcher


def test_parse_repo_url():
    assert GitHubClient.parse_repo_url("https://github.com/torvalds/linux") == ("torvalds", "linux")
    assert GitHubClient.parse_repo_url("https://github.com/facebook/react.git") == ("facebook", "react")
    assert GitHubClient.parse_repo_url("octocat/Spoon-Knife") == ("octocat", "Spoon-Knife")

    with pytest.raises(ValueError):
        GitHubClient.parse_repo_url("invalid-url-with-no-slash")


def test_file_eligibility_filtering():
    fetcher = GitHubFetcher(max_file_bytes=200 * 1024)

    # Valid source files
    assert fetcher.is_eligible_file("src/app.py", 1024) is True
    assert fetcher.is_eligible_file("components/Header.tsx", 5000) is True
    assert fetcher.is_eligible_file("main.cpp", 12000) is True

    # Ignored directories
    assert fetcher.is_eligible_file("node_modules/lodash/index.js", 1000) is False
    assert fetcher.is_eligible_file(".venv/lib/site-packages/pkg.py", 1000) is False
    assert fetcher.is_eligible_file(".git/HEAD", 50) is False
    assert fetcher.is_eligible_file("dist/bundle.js", 20000) is False

    # Ignored binary extensions
    assert fetcher.is_eligible_file("assets/image.png", 5000) is False
    assert fetcher.is_eligible_file("bin/app.exe", 50000) is False
    assert fetcher.is_eligible_file("package-lock.json", 1000) is False

    # Oversized file (> 200 KB)
    assert fetcher.is_eligible_file("big_data.py", 300 * 1024) is False


def test_per_file_failure_isolation():
    mock_client = MagicMock(spec=GitHubClient)
    mock_client.get_repo.return_value = {"default_branch": "main"}
    mock_client.get_commits.return_value = [{"sha": "abc1234567", "commit": {"message": "Initial", "tree": {"sha": "tree99"}}}]
    mock_client.get_tree.return_value = {
        "tree": [
            {"path": "good.py", "type": "blob", "size": 100, "sha": "sha_good"},
            {"path": "bad.py", "type": "blob", "size": 100, "sha": "sha_bad"},
        ]
    }

    def mock_get_blob(owner, repo, sha):
        if sha == "sha_bad":
            raise RuntimeError("Network timeout downloading file blob")
        return "print('Hello world')\n"

    mock_client.get_blob_content.side_effect = mock_get_blob

    fetcher = GitHubFetcher(client=mock_client)
    downloaded, meta = fetcher.fetch_repository_files("owner", "repo")

    # Confirms good.py was successfully downloaded despite bad.py failing
    assert len(downloaded) == 1
    assert downloaded[0]["path"] == "good.py"
    assert len(meta["failed_files"]) == 1
    assert meta["failed_files"][0]["path"] == "bad.py"
