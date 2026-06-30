#!/usr/bin/env python3
import os
import sys
import logging
import inspect
from typing import Any
from ruamel.yaml import YAML
from packaging.version import parse
import antora_utils as utils

ANTORA_FILE: str = "docs/antora.yml"

logger: logging.Logger = utils.setup_logger(__name__)

def get_beta_suffix(version: str) -> str:
    """
    Returns the BETA version from release version. E.g. returns `2` when
    version is `5.8.0-BETA-2`
    """
    parsed = parse(version)
    if parsed.pre and parsed.pre[0] == 'b':
        return f"BETA-{parsed.pre[1]}"
    return ""

def log_inputs(release_ver: str, rel_major_minor: str, master_version: str, master_major_minor: str,
               is_latest_stable_release: str, is_beta_release: str, is_rel_major_minor: str) -> None:
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
        is_beta_release:          {is_beta_release}
        is_rel_major_minor:       {is_rel_major_minor}
        is_latest_stable_release: {is_latest_stable_release}
    """))

def resolve_versions(target_version: str, rel_major_minor: str, master_major_minor: str, 
                     is_beta_release: bool, is_rel_major_minor: bool, is_main: bool, data: Any) -> utils.AntoraVersions:
    """
    Resolves the various versions to set in `antora.yml` in a single place via `AntoraVersions`
    class
    """
    antora_versions = utils.AntoraVersions()
    attrs = data['asciidoc']['attributes']

    if is_main:
        master_snapshot = f"{master_major_minor}-SNAPSHOT"
        antora_versions.version = f"{master_major_minor}-snapshot"
        antora_versions.display_version = master_snapshot
        antora_versions.minor_version = master_snapshot
        antora_versions.attr_version = master_snapshot
        antora_versions.os_version = target_version
        antora_versions.ee_version = target_version
        antora_versions.full_version = target_version
    elif is_beta_release:
        local_clean = target_version.upper().replace("-SNAPSHOT", "")
        beta_suffix = get_beta_suffix(local_clean)

        suffix_lower = beta_suffix.lower()
        suffix_upper = beta_suffix.upper()
        mm_lower = rel_major_minor.lower()
        mm_upper = rel_major_minor.upper()
        
        antora_versions.version = f"{mm_lower}-{suffix_lower}"
        antora_versions.display_version = f"{mm_upper}-{suffix_upper}"
        antora_versions.full_version = target_version
        
        antora_versions.minor_version = f"{mm_lower}-{suffix_lower}"
        antora_versions.attr_version = f"{mm_lower}-{suffix_lower}"
        antora_versions.os_version = attrs.get('os-version')
        antora_versions.ee_version = target_version
        antora_versions.pop_snapshot = False
    else:
        # Patch
        antora_versions.version = rel_major_minor
        antora_versions.display_version = rel_major_minor
        antora_versions.minor_version = rel_major_minor
        antora_versions.attr_version = rel_major_minor
        antora_versions.full_version = target_version
        antora_versions.ee_version = target_version

        if is_rel_major_minor:
            antora_versions.pop_prerelease = True
            antora_versions.pop_snapshot = True

        if not is_rel_major_minor:
            antora_versions.os_version = attrs.get('os-version')
        else:
            antora_versions.os_version = target_version

    return antora_versions

def process_antora(target_version: str, rel_major_minor: str, master_major_minor: str, 
                   is_beta_release: bool, is_rel_major_minor: bool, is_main: bool) -> None:
    """
    Resolves version via `resolve_versions()` and writes the updated versions directly
    to `docs/antora.yml`
    """
    yaml: YAML = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2) # required for '- ...' block
    yaml.width = 4096
    
    with open(ANTORA_FILE, 'r') as f:
        data = yaml.load(f)

    attrs = data['asciidoc']['attributes']

    antora_versions = resolve_versions(
        target_version=target_version,
        rel_major_minor=rel_major_minor,
        master_major_minor=master_major_minor,
        is_beta_release=is_beta_release,
        is_rel_major_minor=is_rel_major_minor,
        is_main=is_main,
        data=data
    )

    data['version'] = antora_versions.version
    data['display_version'] = antora_versions.display_version
    attrs['full-version'] = antora_versions.full_version
    attrs['os-version'] = antora_versions.os_version
    attrs['ee-version'] = antora_versions.ee_version

    if 'minor-version' in attrs or is_main:
        attrs['minor-version'] = antora_versions.minor_version
        
    if 'version' in attrs or is_main:
        attrs['version'] = antora_versions.attr_version

    if antora_versions.pop_prerelease:
        data.pop('prerelease', None)

    if antora_versions.pop_snapshot:
        attrs.pop('snapshot', None)

    with open(ANTORA_FILE, 'w') as f:
        yaml.dump(data, f)

    utils.print_yaml_content(data, yaml, ANTORA_FILE, logger)

def update_release(release_ver: str, rel_major_minor: str, master_major_minor: str, 
                   is_beta_release: bool, is_rel_major_minor: bool) -> None:
    """
    Handles `antora.yml` version updates for release branches (BETA and PATCH)
        1. checkouts new unique PR branch
        2. updates versions, commits and pushes changes to remote
        3. finally, creates PR
    """

    # For PATCH release, checkout v/branch directly. When release is MAJOR/MINOR or BETA,
    # use release branch instead, and v/branch is created from release branch during `promote`
    # phase. This is necessary to prevent premature docs 'live' publishing via v/branch (website
    # auto publishes from v/branch)
    if not is_rel_major_minor and not is_beta_release:
        target_base = f"v/{rel_major_minor}"
    else:
        target_base = release_ver

    update_branch: str = utils.checkout_branch("antora", target_base)
    
    process_antora(
        target_version=release_ver,
        rel_major_minor=rel_major_minor,
        master_major_minor=master_major_minor,
        is_beta_release=is_beta_release,
        is_rel_major_minor=is_rel_major_minor,
        is_main=False
    )
    
    utils.commit_changes(target_base, release_ver, ANTORA_FILE, update_branch)
    utils.create_github_pr(target_base, update_branch, release_ver)

def update_main(master_version: str, rel_major_minor: str,
                master_major_minor: str, is_rel_major_minor: bool) -> None:
    """
    Handles `antora.yml` version updates for `main` branch (i.e. MAJOR.MINOR release)
        1. checkouts new unique PR branch
        2. updates versions, commits and pushes changes to remote
        3. finally, creates PR
    """
    target_base: str = "main"
    update_branch: str = utils.checkout_branch("antora", target_base)
    
    process_antora(
        target_version=master_version,
        rel_major_minor=rel_major_minor,
        master_major_minor=master_major_minor,
        is_beta_release=False,
        is_rel_major_minor=is_rel_major_minor,
        is_main=True
    )
    
    utils.commit_changes(target_base, master_version, ANTORA_FILE, update_branch)
    utils.create_github_pr(target_base, update_branch, master_version)

def update(release_ver: str, rel_major_minor: str, master_version: str, master_major_minor: str,
           is_latest_stable_release: str, is_beta_release: str, is_rel_major_minor: str) -> None:
    """
    Entry point to update `antora.yml` versions for `main` and `release` branches
    """
    r_ver: str = release_ver
    mm_ver: str = rel_major_minor
    m_ver: str = master_version
    m_mm_ver: str = master_major_minor
    stable: bool = is_latest_stable_release == "true"
    beta: bool = is_beta_release == "true"
    maj_min: bool = is_rel_major_minor == "true" and not beta

    log_inputs(r_ver, mm_ver, m_ver, m_mm_ver, is_latest_stable_release, is_beta_release, is_rel_major_minor)

    if maj_min and stable:
        update_main(
            master_version=m_ver,
            rel_major_minor=mm_ver,
            master_major_minor=m_mm_ver,
            is_rel_major_minor=maj_min
        )

    update_release(
        release_ver=r_ver,
        rel_major_minor=mm_ver,
        master_major_minor=m_mm_ver,
        is_beta_release=beta,
        is_rel_major_minor=maj_min
    )

def merge_pull_requests(is_beta_release: str, is_rel_major_minor: str, release_version: str,
                          master_version: str, rel_major_minor: str) -> None:
    """
    Merges `main` and `release` PRs creates above
    """
    beta: bool = is_beta_release == "true"
    maj_min: bool = is_rel_major_minor == "true" and not beta
    patch: bool = is_rel_major_minor == "false" and not beta

    if maj_min:
        utils.merge_github_pr("main", master_version)

    if patch:
        base_branch = f"v/{rel_major_minor}"
    else:
        base_branch = release_version

    utils.merge_github_pr(base_branch, release_version)

def create_v_branch(is_beta_release: str, release_version: str, rel_major_minor: str) -> None:
    """
    Creates `v/branch` from release branch (e.g. `5.8.0` -> `v/5.8` or `5.8.0-BETA-1` -> `5.8-BETA-1`)
    Once v/branch is created, it automatically appears in docs website. The `release` branch manually delete
    during post-release tasks
    """
    v_branch_name = f"v/{rel_major_minor}"

    if is_beta_release == "true":
        beta_suffix = get_beta_suffix(release_version)
        v_branch_name = f"v/{rel_major_minor}-{beta_suffix}"

    utils.git_checkout_remote(v_branch_name, release_version)
    utils.git_push_remote(v_branch_name)
