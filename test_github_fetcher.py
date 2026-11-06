import unittest
from unittest.mock import patch

from github_fetcher import GitHubFetchError, _is_supported_source, fetch_public_repository, parse_github_url


class ParseUrlTests(unittest.TestCase):
    def test_plain_url(self):
        self.assertEqual(parse_github_url("https://github.com/o/r"), ("o", "r", None))

    def test_dot_git_suffix(self):
        self.assertEqual(parse_github_url("https://github.com/o/r.git"), ("o", "r", None))

    def test_simple_branch(self):
        self.assertEqual(parse_github_url("https://github.com/o/r/tree/main"), ("o", "r", "main"))

    def test_branch_with_slash_and_folder(self):
        def fake_get(url):
            if url.endswith("/feature/new-ui"):
                return {"ref": "x"}
            raise GitHubFetchError("nope")
        with patch("github_fetcher._github_get", side_effect=fake_get):
            self.assertEqual(parse_github_url("https://github.com/o/r/tree/feature/new-ui/src"),
                             ("o", "r", "feature/new-ui"))

    def test_rejects_other_hosts_and_short_urls(self):
        for bad in ("https://example.com/o/r", "https://github.com/o", "", "ftp://github.com/o/r"):
            with self.assertRaises(GitHubFetchError):
                parse_github_url(bad)


class FilterTests(unittest.TestCase):
    def test_filters(self):
        self.assertTrue(_is_supported_source("src/app.py"))
        self.assertFalse(_is_supported_source("README.md"))
        self.assertFalse(_is_supported_source("node_modules/x/index.js"))
        self.assertFalse(_is_supported_source(".github/scripts/run.py"))


class FetchTests(unittest.TestCase):
    TREE = {"tree": [
        {"type": "blob", "path": "main.py", "size": 100},
        {"type": "blob", "path": "README.md", "size": 100},
        {"type": "blob", "path": "large.py", "size": 300 * 1024},
        {"type": "blob", "path": "app.js", "size": 100},
        {"type": "blob", "path": "pkg/deep/util.py", "size": 100},
    ], "truncated": False}

    def _get(self, url):
        if "/git/trees/" in url:
            return self.TREE
        return {"name": "p", "full_name": "o/p", "default_branch": "main", "private": False}

    def test_caps_filters_and_orders(self):
        with patch("github_fetcher._github_get", side_effect=self._get), \
                patch("github_fetcher._fetch_file", return_value="print('ok')"):
            result = fetch_public_repository("https://github.com/o/p", max_files=2)
        self.assertEqual([f["path"] for f in result["files"]], ["main.py", "pkg/deep/util.py"])  # .py first, shallow first
        self.assertEqual(result["unsupported_files_skipped"], 1)
        self.assertEqual(result["oversized_files_skipped"], 1)
        self.assertEqual(result["file_limit_skipped"], 1)
        self.assertTrue(result["files_limited"])

    def test_one_download_failure_is_isolated(self):
        def fetch(owner, repo, branch, path):
            if path == "main.py":
                raise GitHubFetchError("Download failed")
            return "x = 1"
        with patch("github_fetcher._github_get", side_effect=self._get), \
                patch("github_fetcher._fetch_file", side_effect=fetch):
            result = fetch_public_repository("https://github.com/o/p")
        self.assertEqual(len(result["fetch_errors"]), 1)
        self.assertGreaterEqual(len(result["files"]), 1)

    def test_private_repo_rejected(self):
        with patch("github_fetcher._github_get", return_value={"private": True}):
            with self.assertRaises(GitHubFetchError):
                fetch_public_repository("https://github.com/o/p")


if __name__ == "__main__":
    unittest.main()
