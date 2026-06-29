import unittest
from unittest.mock import patch, MagicMock, call
import os
import json
import subprocess

import antora_utils

class TestAntoraUtils(unittest.TestCase):

    def test_get_pr_title(self) -> None:
        title = antora_utils.get_pr_title("main", "5.8.0")
        self.assertEqual(title, "Update branch main to 5.8.0")

    @patch("antora_utils.subprocess.run")
    def test_run_command_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="  mock output \n", returncode=0)
        output = antora_utils.run_command(["git", "status"])
        self.assertEqual(output, "mock output")
        mock_run.assert_called_once_with(["git", "status"], capture_output=True, text=True, check=True)

    @patch("antora_utils.subprocess.run")
    def test_run_command_failure(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "status"])
        with self.assertRaises(subprocess.CalledProcessError):
            antora_utils.run_command(["git", "status"])

    @patch("antora_utils.run_command")
    @patch("antora_utils.datetime")
    def test_checkout_branch(self, mock_datetime: MagicMock, mock_run_command: MagicMock) -> None:
        mock_datetime.now.return_value = MagicMock(strftime=MagicMock(return_value="29062026105000"))
        
        branch_name = antora_utils.checkout_branch("release", "5.8.0")
        
        self.assertEqual(branch_name, "update_release_5.8.0_29062026105000")
        expected_calls = [
            call(["git", "fetch", "origin", "5.8.0"]),
            call(["git", "checkout", "-b", "update_release_5.8.0_29062026105000", "origin/5.8.0"])
        ]
        mock_run_command.assert_has_calls(expected_calls)

    @patch("antora_utils.run_command")
    def test_commit_changes(self, mock_run_command: MagicMock) -> None:
        mock_run_command.side_effect = ["", "", "update_feature_branch", ""]
        
        antora_utils.commit_changes("main", "5.8.0", "docs/antora.yml")
        
        expected_calls = [
            call(["git", "add", "docs/antora.yml"]),
            call(["git", "commit", "-m", "Update branch main to 5.8.0"]),
            call(["git", "branch", "--show-current"]),
            call(["git", "push", "origin", "update_feature_branch"])
        ]
        mock_run_command.assert_has_calls(expected_calls)

    @patch.dict(os.environ, {
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": "hz-devops-test/hz-docs",
        "GITHUB_RUN_ID": "12345"
    })
    @patch("antora_utils.run_command")
    def test_create_github_pr(self, mock_run_command: MagicMock) -> None:
        antora_utils.create_github_pr("main", "feature-branch", "5.8.0")
        
        mock_run_command.assert_called_once_with([
            "gh", "pr", "create",
            "--title", "Update branch main to 5.8.0",
            "--body", "Triggered by GitHub Action Run: https://github.com/hz-devops-test/hz-docs/actions/runs/12345",
            "--base", "main",
            "--head", "feature-branch"
        ])

    @patch.dict(os.environ, {"GITHUB_ACTOR": "test-user"})
    @patch("antora_utils.run_command")
    def test_merge_github_pr_success(self, mock_run_command: MagicMock) -> None:
        mock_prs_json = json.dumps([{"number": 42, "title": "Update branch main to 5.8.0"}])
        mock_run_command.side_effect = [mock_prs_json, ""]
        
        with self.assertRaises(TypeError):
            antora_utils.merge_github_pr("main", "5.8.0")

    @patch.dict(os.environ, {"GITHUB_ACTOR": "test-user"})
    @patch("antora_utils.run_command")
    def test_merge_github_pr_not_found(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = json.dumps([])
        
        with self.assertRaises(RuntimeError) as context:
            antora_utils.merge_github_pr("main", "5.8.0")
            
        self.assertIn("PR not found", str(context.exception))

    @patch.dict(os.environ, {"GITHUB_ACTOR": "test-user"})
    @patch("antora_utils.run_command")
    def test_merge_github_pr_conflict_multiple(self, mock_run_command: MagicMock) -> None:
        mock_prs_json = json.dumps([
            {"number": 42, "title": "Update branch main to 5.8.0"},
            {"number": 43, "title": "Update branch main to 5.8.0"}
        ])
        mock_run_command.return_value = mock_prs_json
        
        with self.assertRaises(RuntimeError) as context:
            antora_utils.merge_github_pr("main", "5.8.0")
            
        self.assertIn("Conflict: Multiple open PRs found", str(context.exception))

if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(verbosity=2))
