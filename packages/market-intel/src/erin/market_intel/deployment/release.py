"""Release Management - Version management and release automation."""

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
import semver

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ReleaseStatus(str, Enum):
    DRAFT = "DRAFT"
    PRE_RELEASE = "PRE_RELEASE"
    RELEASED = "RELEASED"
    DEPRECATED = "DEPRECATED"
    ROLLED_BACK = "ROLLED_BACK"


class ReleaseType(str, Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    PATCH = "PATCH"
    HOTFIX = "HOTFIX"
    PRE_RELEASE = "PRE_RELEASE"


@dataclass
class VersionInfo:
    major: int = 0
    minor: int = 0
    patch: int = 0
    pre_release: str = ""
    build_metadata: str = ""
    
    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            version += f"-{self.pre_release}"
        if self.build_metadata:
            version += f"+{self.build_metadata}"
        return version
    
    @classmethod
    def parse(cls, version_str: str) -> 'VersionInfo':
        """Parse version string into VersionInfo."""
        # Parse semantic version
        match = re.match(
            r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z\-\.]+))?(?:\+([0-9A-Za-z\-\.]+))?$',
            version_str
        )
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
        
        major, minor, patch, pre_release, build_metadata = match.groups()
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            pre_release=pre_release or "",
            build_metadata=build_metadata or "",
        )
    
    def bump_major(self) -> 'VersionInfo':
        return VersionInfo(self.major + 1, 0, 0)
    
    def bump_minor(self) -> 'VersionInfo':
        return VersionInfo(self.major, self.minor + 1, 0)
    
    def bump_patch(self) -> 'VersionInfo':
        return VersionInfo(self.major, self.minor, self.patch + 1)
    
    def set_pre_release(self, pre_release: str) -> 'VersionInfo':
        return VersionInfo(self.major, self.minor, self.patch, pre_release)
    
    def set_build_metadata(self, build_metadata: str) -> 'VersionInfo':
        return VersionInfo(self.major, self.minor, self.patch, self.pre_release, build_metadata)


@dataclass
class BuildInfo:
    version: str = ""
    git_commit: str = ""
    git_branch: str = ""
    build_timestamp: str = ""
    build_number: str = ""
    builder: str = ""
    platform: str = ""
    go_version: str = ""
    rust_version: str = ""
    python_version: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "build_timestamp": self.build_timestamp,
            "build_number": self.build_number,
            "builder": self.builder,
            "platform": self.platform,
            "go_version": self.go_version,
            "rust_version": self.rust_version,
            "python_version": self.python_version,
        }


@dataclass
class ReleaseNotes:
    version: str = ""
    release_date: str = ""
    release_type: ReleaseType = ReleaseType.PATCH
    highlights: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    bug_fixes: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    security_fixes: List[str] = field(default_factory=list)
    deprecated: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    upgrade_notes: List[str] = field(default_factory=list)
    contributors: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        md = f"# Release {self.version}\n\n"
        md += f"**Release Date:** {self.release_date}\n"
        md += f"**Release Type:** {self.release_type.value}\n\n"
        
        if self.highlights:
            md += "## Highlights\n"
            for h in self.highlights:
                md += f"- {h}\n"
            md += "\n"
        
        if self.features:
            md += "## New Features\n"
            for f in self.features:
                md += f"- {f}\n"
            md += "\n"
        
        if self.improvements:
            md += "## Improvements\n"
            for i in self.improvements:
                md += f"- {i}\n"
            md += "\n"
        
        if self.bug_fixes:
            md += "## Bug Fixes\n"
            for b in self.bug_fixes:
                md += f"- {b}\n"
            md += "\n"
        
        if self.security_fixes:
            md += "## Security Fixes\n"
            for s in self.security_fixes:
                md += f"- {s}\n"
            md += "\n"
        
        if self.breaking_changes:
            md += "## Breaking Changes\n"
            for b in self.breaking_changes:
                md += f"- {b}\n"
            md += "\n"
        
        if self.deprecated:
            md += "## Deprecated\n"
            for d in self.deprecated:
                md += f"- {d}\n"
            md += "\n"
        
        if self.known_issues:
            md += "## Known Issues\n"
            for k in self.known_issues:
                md += f"- {k}\n"
            md += "\n"
        
        if self.upgrade_notes:
            md += "## Upgrade Notes\n"
            for u in self.upgrade_notes:
                md += f"- {u}\n"
            md += "\n"
        
        if self.contributors:
            md += "## Contributors\n"
            for c in self.contributors:
                md += f"- {c}\n"
            md += "\n"
        
        return md


@dataclass
class ReleaseInfo:
    version: str = ""
    status: ReleaseStatus = ReleaseStatus.DRAFT
    release_type: ReleaseType = ReleaseType.PATCH
    release_date: str = ""
    notes: ReleaseNotes = field(default_factory=ReleaseNotes)
    build_info: BuildInfo = field(default_factory=BuildInfo)
    artifacts: List[str] = field(default_factory=list)
    checksums: Dict[str, str] = field(default_factory=dict)
    signed: bool = False
    signature: str = ""
    approved_by: List[str] = field(default_factory=list)
    approved_at: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "status": self.status.value,
            "release_type": self.release_type.value,
            "release_date": self.release_date,
            "notes": {
                "highlights": self.notes.highlights,
                "features": self.notes.features,
                "improvements": self.notes.improvements,
                "bug_fixes": self.notes.bug_fixes,
                "breaking_changes": self.notes.breaking_changes,
                "security_fixes": self.notes.security_fixes,
                "deprecated": self.notes.deprecated,
                "known_issues": self.notes.known_issues,
                "upgrade_notes": self.notes.upgrade_notes,
                "contributors": self.notes.contributors,
            },
            "build_info": self.build_info.to_dict(),
            "artifacts": self.artifacts,
            "checksums": self.checksums,
            "signed": self.signed,
            "signature": self.signature,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
        }


class ReleaseManager:
    """Manages release process and versioning."""
    
    def __init__(self, repo_path: str = ".", config_path: str = "release_config.yaml"):
        self.repo_path = Path(repo_path)
        self.config_path = Path(config_path)
        self._current_version: Optional[VersionInfo] = None
        self._releases: List[ReleaseInfo] = []
        self._load_config()
    
    def _load_config(self):
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
                if config and "current_version" in config:
                    self._current_version = VersionInfo.parse(config["current_version"])
    
    def get_current_version(self) -> VersionInfo:
        if self._current_version is None:
            # Try to get from git tags
            try:
                result = subprocess.run(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                tag = result.stdout.strip()
                if tag.startswith("v"):
                    tag = tag[1:]
                self._current_version = VersionInfo.parse(tag)
            except subprocess.CalledProcessError:
                self._current_version = VersionInfo(0, 1, 0)
        return self._current_version
    
    def get_next_version(self, release_type: ReleaseType) -> VersionInfo:
        current = self.get_current_version()
        
        if release_type == ReleaseType.MAJOR:
            return current.bump_major()
        elif release_type == ReleaseType.MINOR:
            return current.bump_minor()
        elif release_type == ReleaseType.PATCH:
            return current.bump_patch()
        elif release_type == ReleaseType.HOTFIX:
            return current.bump_patch()
        elif release_type == ReleaseType.PRE_RELEASE:
            return VersionInfo(
                current.major, current.minor, current.patch,
                pre_release=f"rc.{datetime.utcnow().strftime('%Y%m%d')}"
            )
        return current
    
    def create_release(
        self,
        release_type: ReleaseType,
        notes: ReleaseNotes = None,
        dry_run: bool = False,
    ) -> ReleaseInfo:
        """Create a new release."""
        version = self.get_next_version(release_type)
        
        # Generate release notes if not provided
        if notes is None:
            notes = self.generate_release_notes(version)
        
        # Get build info
        build_info = self._collect_build_info()
        
        release = ReleaseInfo(
            version=str(version),
            status=ReleaseStatus.DRAFT,
            release_type=release_type,
            release_date=datetime.utcnow().isoformat(),
            notes=notes,
            build_info=build_info,
        )
        
        if not dry_run:
            # Create git tag
            tag_name = f"v{version}"
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
                cwd=self.repo_path,
                check=True
            )
            
            # Push tag
            subprocess.run(
                ["git", "push", "origin", tag_name],
                cwd=self.repo_path,
                check=True
            )
            
            release.status = ReleaseStatus.RELEASED
            self._releases.append(release)
            self._save_release(release)
        
        return release
    
    def generate_release_notes(self, version: VersionInfo) -> ReleaseNotes:
        """Generate release notes from git history."""
        current = self.get_current_version()
        notes = ReleaseNotes(
            version=str(version),
            release_date=datetime.utcnow().isoformat(),
            release_type=ReleaseType.PATCH,
        )
        
        # Get commits since last release
        try:
            last_tag = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            if last_tag.startswith("v"):
                last_tag = last_tag[1:]
            
            # Get commits since last tag
            commits = subprocess.run(
                ["git", "log", f"{last_tag}..HEAD", "--oneline", "--no-merges"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip().split("\n")
            
            # Categorize commits
            for commit in commits:
                commit_lower = commit.lower()
                if any(kw in commit_lower for kw in ["feat", "feature", "add"]):
                    notes.features.append(commit)
                elif any(kw in commit_lower for kw in ["fix", "bug", "patch"]):
                    notes.bug_fixes.append(commit)
                elif any(kw in commit_lower for kw in ["improve", "enhance", "optimize", "refactor"]):
                    notes.improvements.append(commit)
                elif any(kw in commit_lower for kw in ["break", "breaking"]):
                    notes.breaking_changes.append(commit)
                elif any(kw in commit_lower for kw in ["security", "vuln", "cve"]):
                    notes.security_fixes.append(commit)
                elif any(kw in commit_lower for kw in ["deprecat", "remove"]):
                    notes.deprecated.append(commit)
                else:
                    notes.improvements.append(commit)
        except subprocess.CalledProcessError:
            pass
        
        return notes
    
    def _collect_build_info(self) -> BuildInfo:
        """Collect build information."""
        build_info = BuildInfo()
        build_info.version = str(self.get_current_version())
        
        try:
            build_info.git_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path, capture_output=True, text=True, check=True
            ).stdout.strip()[:8]
        except:
            build_info.git_commit = "unknown"
        
        try:
            build_info.git_branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path, capture_output=True, text=True, check=True
            ).stdout.strip()
        except:
            build_info.git_branch = "unknown"
        
        build_info.build_timestamp = datetime.utcnow().isoformat()
        build_info.build_number = os.environ.get("BUILD_NUMBER", "local")
        build_info.builder = os.environ.get("BUILD_USER", "unknown")
        build_info.platform = f"{sys.platform}-{os.uname().machine}"
        build_info.python_version = sys.version.split()[0]
        
        try:
            build_info.go_version = subprocess.run(
                ["go", "version"], capture_output=True, text=True, check=True
            ).stdout.strip()
        except:
            pass
        
        try:
            build_info.rust_version = subprocess.run(
                ["rustc", "--version"], capture_output=True, text=True, check=True
            ).stdout.strip()
        except:
            pass
        
        return build_info
    
    def _save_release(self, release: ReleaseInfo):
        """Save release metadata."""
        releases_file = self.repo_path / ".erin" / "releases.json"
        releases_file.parent.mkdir(parents=True, exist_ok=True)
        
        releases = []
        if releases_file.exists():
            with open(releases_file) as f:
                releases = json.load(f)
        
        releases.append(release.to_dict())
        
        with open(releases_file, "w") as f:
            json.dump(releases, f, indent=2)
    
    def get_release_history(self) -> List[ReleaseInfo]:
        releases_file = self.repo_path / ".erin" / "releases.json"
        if releases_file.exists():
            with open(releases_file) as f:
                return json.load(f)
        return []
    
    def rollback_release(self, version: str) -> bool:
        """Rollback to a previous version."""
        # Find the release
        releases = self.get_release_history()
        target = None
        for r in releases:
            if r.version == version:
                target = r
                break
        
        if not target:
            return False
        
        # Checkout the tag
        tag_name = f"v{version}"
        subprocess.run(
            ["git", "checkout", tag_name],
            cwd=self.repo_path,
            check=True
        )
        
        # Update current version
        self._current_version = VersionInfo.parse(version)
        
        # Save
        self._save_current_version()
        
        return True
    
    def _save_current_version(self):
        config_file = Path(self.config_path)
        config = {}
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
        config["current_version"] = str(self.get_current_version())
        with open(config_file, "w") as f:
            yaml.dump(config, f)


def create_release_manager(repo_path: str = ".", config_path: str = "release_config.yaml") -> ReleaseManager:
    return ReleaseManager(repo_path, config_path)


def generate_release_notes(version: VersionInfo, commits: List[str]) -> ReleaseNotes:
    notes = ReleaseNotes(
        version=str(version),
        release_date=datetime.utcnow().isoformat(),
        release_type=ReleaseType.PATCH,
    )
    
    for commit in commits:
        commit_lower = commit.lower()
        if any(kw in commit_lower for kw in ["feat", "feature", "add"]):
            notes.features.append(commit)
        elif any(kw in commit_lower for kw in ["fix", "bug", "patch"]):
            notes.bug_fixes.append(commit)
        elif any(kw in commit_lower for kw in ["improve", "enhance", "optimize", "refactor"]):
            notes.improvements.append(commit)
        elif any(kw in commit_lower for kw in ["break", "breaking"]):
            notes.breaking_changes.append(commit)
        elif any(kw in commit_lower for kw in ["security", "vuln", "cve"]):
            notes.security_fixes.append(commit)
        elif any(kw in commit_lower for kw in ["deprecat", "remove"]):
            notes.deprecated.append(commit)
        else:
            notes.improvements.append(commit)
    
    return notes