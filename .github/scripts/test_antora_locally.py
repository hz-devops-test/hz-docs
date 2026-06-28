#!/usr/bin/env python3
import os
import sys
import inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import antora_updater as antora

def run_local_simulation() -> None:
    print(inspect.cleandoc("""
        ========================================
        Starting Antora Update Local Simulation
        ========================================
    """))

    os.environ["RUNNER_DEBUG"] = "1"

    # MAJOR.MINOR MAIN
    # RELEASE_VER = "5.8.0"
    # REL_MAJOR_MINOR_VER = "5.9"
    # MASTER_VERSION = "5.9.0-SNAPSHOT"
    # MASTER_MAJOR_MINOR_VER = "5.9"
    # IS_LATEST_STABLE_RELEASE = "true"
    # IS_BETA_RELEASE = "false"
    # IS_REL_MAJOR_MINOR = "true"

    # MAJOR.MINOR RELEASE
    # RELEASE_VER = "5.8.0"
    # REL_MAJOR_MINOR_VER = "5.9"
    # MASTER_VERSION = "5.9.0-SNAPSHOT"
    # MASTER_MAJOR_MINOR_VER = "5.9"
    # IS_LATEST_STABLE_RELEASE = "true"
    # IS_BETA_RELEASE = "false"
    # IS_REL_MAJOR_MINOR = "true"

    # BETA
    # RELEASE_VER = "5.8.0-BETA-1"
    # REL_MAJOR_MINOR_VER = "5.8"
    # MASTER_VERSION = "5.8.0-SNAPSHOT"
    # MASTER_MAJOR_MINOR_VER = "5.8"
    # IS_LATEST_STABLE_RELEASE = "false"
    # IS_BETA_RELEASE = "true"
    # IS_REL_MAJOR_MINOR = "true"

    # PATCH LATEST
    # RELEASE_VER = "5.8.1"
    # REL_MAJOR_MINOR_VER = "5.8"
    # MASTER_VERSION = "5.9.0-SNAPSHOT"
    # MASTER_MAJOR_MINOR_VER = "5.9"
    # IS_LATEST_STABLE_RELEASE = "true"
    # IS_BETA_RELEASE = "false"
    # IS_REL_MAJOR_MINOR = "false"

    # PATCH NOT LATEST
    # RELEASE_VER = "5.8.1"
    # REL_MAJOR_MINOR_VER = "5.8"
    # MASTER_VERSION = "5.9.0-SNAPSHOT"
    # MASTER_MAJOR_MINOR_VER = "5.9"
    # IS_LATEST_STABLE_RELEASE = "false"
    # IS_BETA_RELEASE = "false"
    # IS_REL_MAJOR_MINOR = "false"

    try:
        antora.update(
            release_ver=RELEASE_VER,
            rel_major_minor_ver=REL_MAJOR_MINOR_VER,
            master_version=MASTER_VERSION,
            master_major_minor_ver=MASTER_MAJOR_MINOR_VER,
            is_latest_stable_release=IS_LATEST_STABLE_RELEASE,
            is_beta_release=IS_BETA_RELEASE,
            is_rel_major_minor=IS_REL_MAJOR_MINOR
        )
        print(inspect.cleandoc("""
            ========================================
            Simulation Complete: Check docs/antora.yml
            ========================================
        """))
    except Exception as e:
        print(f"\nSimulation Failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_local_simulation()
