import os
import sys
import json
import logging
import subprocess
import inspect
from datetime import datetime
from typing import Any, Optional
from ruamel.yaml import YAML

class AntoraVersions:
    def __init__(self) -> None:
        self.version: str = ""
        self.display_version: str = ""
        self.full_version: str = ""
        self.os_version: Optional[str] = None
        self.ee_version: Optional[str] = None
        self.minor_version: Optional[str] = None
        self.attr_version: Optional[str] = None
        self.pop_prerelease: bool = False
        self.pop_snapshot: bool = False

def run_command(
    command:list
) -> str:
    """
    Runs single command. Emits full command if debug is enabled
    """
    logger.debug(f"Executing command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else str(e)
        raise RuntimeError(f"Command failed: {command}\nError: {error_message}")

def get_pr_title(
    base_branch:str,
    version:str
) -> str:
    """
    Returns PR title with base/target branch and version
    """
    return f"Update branch {base_branch} to {version}"

def git_checkout_remote(
    local_branch:str,
    remote_branch:str
) -> None:
    """
    Performs repo `fetch` and `checkout` using `git` cli
    """
    run_command([
        "git", "fetch",
        "origin", remote_branch
    ])
    run_command([
        "git", "checkout",
        "-b", local_branch,
        f"origin/{remote_branch}"
    ])

def checkout_branch(
    prefix:str,
    branch:str
) -> str:
    """
    Checks out unique PR branch from remote using `git` cli
    """
    timestamp = datetime.now().strftime("%d%m%Y%H%M%S")
    update_branch = f"update_{prefix}_{branch}_{timestamp}"
    git_checkout_remote(update_branch, branch)
    return update_branch

def git_push_remote(
    branch_name:str
) -> None:
    """
    Remote pushes supplied branch using `git` cli
    """
    run_command([
        "git", "push",
        "origin",
        branch_name
    ])

def commit_changes(
    base_branch:str,
    version:str,
    file_path:str,
    active_branch:str
) -> None:
    """
    Adds/commits local changes and remote pushes `base_branch` using `git` cli
    """
    run_command([
        "git", "add",
        file_path
    ])
    run_command([
        "git", "commit",
        "--message", f"Update branch {base_branch} to {version}"
    ])
    git_push_remote(active_branch)

def create_github_pr(
    base_branch:str,
    head_branch:str,
    version:str
) -> None:
    """
    Creates GitHub PR using `gh` cli. Adds link to the current build run ID in the PR body
    """
    title = get_pr_title(base_branch, version)
    server_url = os.environ["GITHUB_SERVER_URL"]
    repository = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]
    github_run_url = f"{server_url}/{repository}/actions/runs/{run_id}"
    body = f"Triggered by GitHub Action Run: {github_run_url}"
    run_command([
        "gh", "pr", "create",
        "--title", title,
        "--body", body,
        "--base", base_branch,
        "--head", head_branch
    ])

def merge_github_pr(
    base_branch:str,
    version:str
) -> None:
    """
    Merges pre-existing `Open` GitHub PR using `gh` cli. It searches for the PR and
    `squash` merges the PR. It will error out if more than one PR is found (only one is expected
    for any given release)
    """
    target_title = get_pr_title(base_branch, version)
    pr_list_output = run_command([
        "gh", "search", "prs",
        "--state", "open",
        "--base", base_branch,
        "--match", "title", f'"{target_title}"',
        "--json", "number,title"
    ])
    try:
        prs = json.loads(pr_list_output)
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON: {e}")
    exact_matches = [pr for pr in prs if pr.get("title") == target_title]
    if not exact_matches:
        raise RuntimeError(f"PR not found: '{target_title}' (Base: {base_branch})")
    elif len(exact_matches) > 1:
        pr_numbers = [pr["number"] for pr in exact_matches]
        raise RuntimeError(f"Conflict: Multiple open PRs found with title '{target_title}'. PRs: {pr_numbers}")
    matching_pr = exact_matches[0]
    pr_number = matching_pr["number"]
    try:
        run_command([
            "gh", "pr", "merge", str(pr_number),
            "--squash",
            "--admin",
            "--delete-branch"
        ])
    except Exception as e:
        raise RuntimeError(f"Failed to merge PR #{pr_number}: {e}")

def print_yaml_content(
    data:Any,
    yaml_processor:YAML,
    file_path:str,
    pipe_logger:logging.Logger
) -> None:
    """
    Debug prints `antora.yml` versions after update
    """
    if pipe_logger.isEnabledFor(logging.DEBUG):
        pipe_logger.debug(f"Updated content of {file_path}:")
        yaml_processor.dump(data, sys.stdout)

def setup_logger(
    name:str=__name__
) -> logging.Logger:
    """
    Setups logger. Debug logging level is set if user eneables via GitHub UI
    """
    if os.environ.get("RUNNER_DEBUG") == "1":
        current_level = logging.DEBUG
    else:
        current_level = logging.INFO
    logging.basicConfig(
        level=current_level,
        format="\033[36m[DEBUG]\033[0m %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(name)

import inspect

def log_inputs(
    release_ver:str="0.0.0",
    rel_major_minor:str="0.0",
    master_version:str="0.0.0",
    master_major_minor:str="0.0",
    mc_version:str="0.0.0",
    mc_major_minor:str="0.0",
    is_latest_stable_release:bool=False,
    is_beta_release:bool=False,
    is_rel_major_minor:bool=False,
    is_patch:bool=False
) -> None:
    """
    Helper function to log script inputs when debugging
    """
    logger.debug(inspect.cleandoc(f"""
        update_antora Inputs:
        ---------------------
        release_ver:              {release_ver}
        rel_major_minor:          {rel_major_minor}
        master_version:           {master_version}
        master_major_minor:       {master_major_minor}
        mc_version:               {mc_version}
        mc_major_minor:           {mc_major_minor}
        is_beta_release:          {is_beta_release}
        is_rel_major_minor:       {is_rel_major_minor}
        is_latest_stable_release: {is_latest_stable_release}
        is_patch:                 {is_patch}
    """))

"""
Logger instance for this module
"""
logger = setup_logger()
