import logging
import os
import time
from typing import List, Optional
from threading import Lock

from pydantic_ai_skills import SkillsDirectory, SkillsToolset
from pydantic_ai.toolsets.combined import AbstractToolset

logger = logging.getLogger(__name__)


class SkillsManager:
    """Manages skills loading and periodic refresh from a directory."""
    
    def __init__(self, skills_dir: str = "/app/backend/skills", refresh_interval: int = 300):
        self.skills_dir = skills_dir
        self.refresh_interval = refresh_interval
        self._toolsets: List[AbstractToolset] = []
        self._last_refresh = 0
        self._lock = Lock()
        self._enabled = os.path.exists(skills_dir)
        
        if self._enabled:
            logger.info(f"Skills directory found: {skills_dir}")
            self._load_skills()
        else:
            logger.warning(f"Skills directory not found: {skills_dir}")
    
    def _load_skills(self) -> None:
        """Load all skills from subdirectories into a single SkillsToolset."""
        from pydantic_ai_skills import SkillsDirectory, SkillsToolset
        
        with self._lock:
            self._toolsets = []
            
            if not os.path.exists(self.skills_dir):
                logger.warning(f"Skills directory does not exist: {self.skills_dir}")
                return
            
            skill_dirs = []
            for entry in os.listdir(self.skills_dir):
                if entry.startswith("."):
                    continue
                
                full_path = os.path.join(self.skills_dir, entry)
                
                if not os.path.isdir(full_path):
                    continue
                
                skill_dirs.append(SkillsDirectory(path=full_path))
                logger.info(f"Found skill: {entry}")
            
            if skill_dirs:
                toolset = SkillsToolset(directories=skill_dirs)
                self._toolsets.append(toolset)
                logger.info(f"Loaded {len(skill_dirs)} skills in single toolset")
            
            self._last_refresh = time.time()
    
    def should_refresh(self) -> bool:
        """Check if skills should be refreshed."""
        if not self._enabled:
            return False
        return (time.time() - self._last_refresh) > self.refresh_interval
    
    def refresh_if_needed(self) -> None:
        """Refresh skills if the interval has passed."""
        if self.should_refresh():
            logger.info("Refreshing skills...")
            self._load_skills()
    
    def get_toolsets(self) -> List[AbstractToolset]:
        """Get the current toolsets."""
        self.refresh_if_needed()
        with self._lock:
            return list(self._toolsets)
    
    def force_refresh(self) -> None:
        """Force a refresh of skills."""
        logger.info("Force refreshing skills...")
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


def get_skills_toolsets() -> List[AbstractToolset]:
    """Get toolsets from the skills manager, refreshing if needed."""
    manager = get_skills_manager()
    if manager:
        return manager.get_toolsets()
    return []
