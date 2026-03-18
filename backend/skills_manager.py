import logging
import os
import time
import zipfile
import tempfile
from typing import List, Optional
from threading import Lock

from pydantic_ai_skills import SkillsDirectory, SkillsToolset
from pydantic_ai.toolsets.prefixed import PrefixedToolset
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
        """Load all skills from the skills directory."""
        with self._lock:
            self._toolsets = []
            
            if not os.path.exists(self.skills_dir):
                logger.warning(f"Skills directory does not exist: {self.skills_dir}")
                return
            
            skill_files = []
            for entry in os.listdir(self.skills_dir):
                full_path = os.path.join(self.skills_dir, entry)
                
                if entry.startswith("."):
                    continue
                
                if os.path.isdir(full_path):
                    skill_files.append(("dir", full_path, entry))
                elif entry.endswith((".zip", ".skill")):
                    skill_files.append(("file", full_path, entry))
            
            for idx, (skill_type, path, name) in enumerate(skill_files):
                try:
                    if skill_type == "dir":
                        skills_dir_obj = SkillsDirectory(path=path)
                        toolset = SkillsToolset(directories=[skills_dir_obj])
                    else:
                        import zipfile
                        import tempfile
                        tmp_dir = tempfile.mkdtemp()
                        with zipfile.ZipFile(path, "r") as zf:
                            zf.extractall(tmp_dir)
                        skills_dir_obj = SkillsDirectory(path=tmp_dir)
                        toolset = SkillsToolset(directories=[skills_dir_obj])
                    
                    prefixed = PrefixedToolset(toolset, prefix=f"skill{idx}_")
                    self._toolsets.append(prefixed)
                    logger.info(f"Loaded skill: {name}")
                except Exception as e:
                    logger.error(f"Failed to load skill {name}: {e}")
            
            self._last_refresh = time.time()
            logger.info(f"Loaded {len(self._toolsets)} skill toolsets")
    
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


def init_skills_manager(skills_dir: str = None, refresh_interval: int = 300) -> SkillsManager:
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
