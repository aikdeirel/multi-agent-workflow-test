import os
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Dynamic prompt manager with intelligent caching and hot-reload capability.
    Tracks file modification times and automatically reloads changed prompts.
    """

    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = prompts_dir
        self._cache: Dict[str, Dict[str, any]] = {}

        # Ensure prompts directory exists
        if not os.path.exists(self.prompts_dir):
            logger.warning(f"Prompts directory '{self.prompts_dir}' does not exist")

    def get_prompt(self, name: str) -> str:
        """
        Get a prompt by name with intelligent caching and hot-reload.

        Args:
            name: Name of the prompt file (with or without .md extension)

        Returns:
            Content of the prompt file

        Raises:
            FileNotFoundError: If the prompt file doesn't exist
            IOError: If there's an error reading the file
        """
        # Ensure .md extension
        if not name.endswith(".md"):
            name += ".md"

        filepath = os.path.join(self.prompts_dir, name)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Prompt file not found: {filepath}")

        try:
            # Get current file modification time
            current_mtime = os.path.getmtime(filepath)

            # Check if we have cached version and if it's still valid
            if name in self._cache:
                cached_mtime = self._cache[name].get("mtime", 0)
                if current_mtime <= cached_mtime:
                    logger.debug(f"Using cached prompt: {name}")
                    return self._cache[name]["content"]

            # Read file content
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Update cache
            self._cache[name] = {"content": content, "mtime": current_mtime}

            logger.debug(f"Loaded/reloaded prompt: {name}")
            return content

        except Exception as e:
            logger.error(f"Error loading prompt '{name}': {str(e)}")
            raise IOError(f"Error reading prompt file {filepath}: {str(e)}")

    def invalidate_cache(self, name: Optional[str] = None) -> None:
        """
        Invalidate cache for a specific prompt or all prompts.

        Args:
            name: Name of prompt to invalidate, or None to invalidate all
        """
        if name is None:
            self._cache.clear()
            logger.info("Invalidated all prompt cache")
        else:
            if not name.endswith(".md"):
                name += ".md"
            if name in self._cache:
                del self._cache[name]
                logger.info(f"Invalidated cache for prompt: {name}")

    def cleanup_cache(self) -> None:
        """Clean up cache entries for deleted files."""
        to_remove = []

        for name in self._cache.keys():
            filepath = os.path.join(self.prompts_dir, name)
            if not os.path.exists(filepath):
                to_remove.append(name)

        for name in to_remove:
            del self._cache[name]
            logger.info(f"Removed cache entry for deleted file: {name}")

    def list_available_prompts(self) -> list[str]:
        """
        List all available prompt files in the prompts directory.

        Returns:
            List of prompt file names (without .md extension)
        """
        if not os.path.exists(self.prompts_dir):
            return []

        try:
            files = [
                f[:-3]
                for f in os.listdir(self.prompts_dir)
                if f.endswith(".md")
                and os.path.isfile(os.path.join(self.prompts_dir, f))
            ]
            return sorted(files)
        except Exception as e:
            logger.error(f"Error listing prompt files: {str(e)}")
            return []

    def get_cache_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get information about cached prompts.

        Returns:
            Dictionary with cache information
        """
        info = {}
        for name, cache_data in self._cache.items():
            info[name] = {
                "cached_at": time.ctime(cache_data["mtime"]),
                "size": len(cache_data["content"]),
            }
        return info


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(prompts_dir: str = "prompts") -> PromptManager:
    """Get global prompt manager instance, creating it if needed."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(prompts_dir)
    return _prompt_manager
