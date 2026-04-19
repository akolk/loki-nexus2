import logging
import os
from typing import Optional

from pydantic_ai_skills import SkillsToolset, LocalSkillScriptExecutor, discover_skills, GitSkillsRegistry

logger = logging.getLogger(__name__)


class SkillsManager:
    """Manages skills loading from local directory or Git registry."""

    def __init__(self, skills_dir: str = "/app/backend/skills", refresh_interval: int = 300):
        self.skills_dir = skills_dir
        self.refresh_interval = refresh_interval
        self._toolset: Optional[SkillsToolset] = None
        self._enabled = False

        self._load_skills()

    def _load_skills(self) -> None:
        """Load skills from registry or local directory."""
        skills_registry_url = os.environ.get("SKILLS_REGISTRY")

        if skills_registry_url:
            logger.info(f"Loading skills from registry: {skills_registry_url}")
            self._load_from_registry(skills_registry_url)
        elif os.path.exists(self.skills_dir):
            logger.info(f"Skills directory found: {self.skills_dir}")
            self._load_from_directory()
        else:
            logger.info("No skills registry configured and local skills directory not found, skipping skills")

    def _load_from_registry(self, registry_url: str) -> None:
        """Load skills from a Git registry."""
        try:
            if registry_url.startswith("http://") or registry_url.startswith("https://") or registry_url.startswith("git@"):
                git_registry = GitSkillsRegistry(repo_url=registry_url)
                skills = git_registry.get_skills()
            else:
                skills = discover_skills(
                    path=registry_url,
                    validate=True,
                    max_depth=3,
                    script_executor=LocalSkillScriptExecutor()
                )

            if skills:
                self._toolset = SkillsToolset(skills=skills)
                logger.info(f"Loaded {len(skills)} skills from registry")
                self._enabled = True
            else:
                logger.warning("No skills found in registry")
        except Exception as e:
            logger.error(f"Failed to load skills from registry: {e}")

    def _load_from_directory(self) -> None:
        """Load skills from local directory."""
        skills = discover_skills(
            path=self.skills_dir,
            validate=True,
            max_depth=3,
            script_executor=LocalSkillScriptExecutor()
        )

        if skills:
            self._toolset = SkillsToolset(skills=skills)
            logger.info(f"Loaded {len(skills)} skills from local directory")
            self._enabled = True
        else:
            logger.warning("No skills found in local directory")

    def get_toolset(self) -> Optional[SkillsToolset]:
        """Get the current toolset."""
        return self._toolset

    def refresh(self) -> None:
        """Force a refresh of skills."""
        logger.info("Refreshing skills...")
        self._load_skills()


_skills_manager: Optional[SkillsManager] = None


def init_skills_manager(skills_dir: Optional[str] = None, refresh_interval: int = 300) -> SkillsManager:
    """Initialize the global skills manager."""
    global _skills_manager
    if skills_dir is None:
        skills_dir = os.environ.get("SKILLS_DIR", "/app/backend/skills")
    _skills_manager = SkillsManager(skills_dir=skills_dir, refresh_interval=refresh_interval)
    return _skills_manager


def get_skills_manager() -> Optional[SkillsManager]:
    """Get the global skills manager."""
    return _skills_manager


def get_skills_toolsets():
    """Get the skills toolset from the manager."""
    manager = get_skills_manager()
    if manager:
        return manager.get_toolset()
    return None
