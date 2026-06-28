#!/usr/bin/env python3
import os

# ==============================================================================
# TEST CONFIGURATION BLOCK (Modify these to test different combinations)
# ==============================================================================
RELEASE_VER = "5.8.0"
MASTER_VERSION = "5.9.0-SNAPSHOT"
MAJOR_MINOR_VER = "5.8"
IS_NEXT_RELEASE_MAJOR = "true"
IS_LATEST_STABLE_RELEASE = "true"
IS_BETA_RELEASE = "false"
IS_MAJOR_MINOR = "true"

# Mocking GitHub Action environment variables required by the script
os.environ["GITHUB_SERVER_URL"] = "https://github.com"
os.environ["GITHUB_REPOSITORY"] = "hazelcast/hz-docs"
os.environ["GITHUB_RUN_ID"] = "12345678"
# ==============================================================================

print("======================================================================")
print("STARTING LOCAL ANTORA VERSION TRANSFORMATION TEST PASS (PURE PYTHON)")
print("======================================================================")

# Import our functional script targets
import antora_utils as utils
import antora_updater as functions

# Override the reference to look at our local test directory paths instead of production variables
functions.ANTORA_FILE = "docs/antora.yml"

# Local overrides for Git and GH CLI commands to prevent remote tracking updates
def mock_run_command(command: list) -> str:
    cmd_str = " ".join(command)
    if "fetch" in command or "push" in command:
        print(f"\033[33m[MOCK GIT]\033[0m Would execute: git {cmd_str.replace('git ', '')}")
        return ""
    elif "gh" in command:
        print(f"\033[32m[MOCK GH CLI]\033[0m Would execute: gh {cmd_str.replace('gh ', '')}")
        return ""
    else:
        # Pass normal commands like branch name checks directly to the OS subprocess engine
        import subprocess
        res = subprocess.run(command, capture_output=True, text=True)
        return res.stdout.strip()

# Apply the functional monkeypatches to our imported utilities module layer
utils.run_command = mock_run_command

# Execute core logic runner using parameters strings matching your orchestration calls
functions.update(
    RELEASE_VER,
    MASTER_VERSION,
    MAJOR_MINOR_VER,
    IS_LATEST_STABLE_RELEASE,
    IS_BETA_RELEASE,
    IS_MAJOR_MINOR
)

print("======================================================================")
print("TEST COMPLETION PASS. Review your local docs/antora.yml transformations!")
print("======================================================================")
