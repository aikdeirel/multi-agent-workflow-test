import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Simple prompt manager for reading prompt files.
    """

    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = prompts_dir

        # Ensure prompts directory exists
        if not os.path.exists(self.prompts_dir):
            logger.warning(f"Prompts directory '{self.prompts_dir}' does not exist")

    def get_prompt(self, name: str) -> str:
        """
        Get a prompt by name.

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
            # Read file content
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()

            logger.debug(f"Loaded prompt: {name}")
            return content

        except Exception as e:
            logger.error(f"Error loading prompt '{name}': {str(e)}")
            raise IOError(f"Error reading prompt file {filepath}: {str(e)}")

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


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(prompts_dir: str = "prompts") -> PromptManager:
    """Get global prompt manager instance, creating it if needed."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(prompts_dir)
    return _prompt_manager
