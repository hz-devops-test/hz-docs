#!/usr/bin/env python3
import os
import sys
import logging
import inspect
from typing import Any
from ruamel.yaml import YAML
import antora_utils as utils

ANTORA_FILE: str = "docs/antora.yml"

logger: logging.Logger = utils.setup_logger(__name__)

def resolve_versions(target_version: str, rel_major_minor: str, master_major_minor: str, 
                     is_beta_release: bool, is_rel_major_minor: bool, is_main: bool, data: Any) -> utils.AntoraVersions:
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
        return antora_versions

    if is_beta_release:
        local_clean = target_version.upper().replace("-SNAPSHOT", "")
        beta_suffix = local_clean.replace(f"{rel_major_minor.upper()}.0-", "")
        
        antora_versions.version = f"{rel_major_minor.lower()}-{beta_suffix.lower()}-snapshot"
        antora_versions.display_version = f"{rel_major_minor.upper()}-{beta_suffix.upper()}-SNAPSHOT"
        antora_versions.full_version = f"{local_clean}-SNAPSHOT"
        
        antora_versions.minor_version = attrs.get('minor-version')
        antora_versions.attr_version = attrs.get('version')
        antora_versions.os_version = attrs.get('os-version')
        antora_versions.ee_version = attrs.get('ee-version')
        antora_versions.pop_snapshot = False
    else:
        antora_versions.version = rel_major_minor.lower()
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
    
    yaml: YAML = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
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

def update_main(release_ver: str, master_version: str, rel_major_minor: str, master_major_minor: str,
                is_latest_stable_release: bool, is_rel_major_minor: bool) -> None:
    if not is_rel_major_minor or not is_latest_stable_release:
        return

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

def log_inputs(release_ver: str, rel_major_minor: str, master_version: str, master_major_minor: str,
               is_latest_stable_release: str, is_beta_release: str, is_rel_major_minor: str) -> None:
    logger.debug(inspect.cleandoc(f"""
        update_antora Inputs:
        ---------------------
        release_ver:              {release_ver}
        rel_major_minor:          {rel_major_minor}
        master_version:           {master_version}
        master_major_minor:       {master_major_minor}
        is_latest_stable_release: {is_latest_stable_release}
        is_beta_release:          {is_beta_release}
        is_rel_major_minor:          {is_rel_major_minor}
    """))

def update(release_ver: str, rel_major_minor: str, master_version: str, master_major_minor: str,
           is_latest_stable_release: str, is_beta_release: str, is_rel_major_minor: str) -> None:
    
    r_ver: str = release_ver
    mm_ver: str = rel_major_minor
    m_ver: str = master_version
    m_mm_ver: str = master_major_minor
    stable: bool = is_latest_stable_release.lower() == "true"
    beta: bool = is_beta_release.lower() == "true"
    maj_min: bool = is_rel_major_minor.lower() == "true"

    log_inputs(r_ver, mm_ver, m_ver, m_mm_ver, is_latest_stable_release, is_beta_release, is_rel_major_minor)

    if maj_min and not beta:
        update_main(
            release_ver=r_ver,
            master_version=m_ver,
            rel_major_minor=mm_ver,
            master_major_minor=m_mm_ver,
            is_latest_stable_release=stable,
            is_rel_major_minor=maj_min
        )

    update_release(
        release_ver=r_ver,
        rel_major_minor=mm_ver,
        master_major_minor=m_mm_ver,
        is_beta_release=beta,
        is_rel_major_minor=maj_min
    )
