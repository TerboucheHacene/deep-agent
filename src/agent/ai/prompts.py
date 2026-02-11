from pathlib import Path

__all__ = [
    "load_prompt",
    "list_available_prompts",
    "WRITE_TODOS_DESCRIPTION",
    "TODO_USAGE_INSTRUCTIONS",
    "LS_DESCRIPTION",
    "READ_FILE_DESCRIPTION",
    "WRITE_FILE_DESCRIPTION",
    "FILE_USAGE_INSTRUCTIONS",
    "SUMMARIZE_WEB_SEARCH",
    "RESEARCHER_INSTRUCTIONS",
    "TASK_DESCRIPTION_PREFIX",
    "SUBAGENT_USAGE_INSTRUCTIONS",
]


def load_prompt(prompt_name: str, prompts_dir: Path | None = None) -> str:
    """Load a prompt from a markdown file in the prompts directory.

    Args:
        prompt_name: Name of the prompt file (with or without .md extension)
        prompts_dir: Optional custom path to prompts directory.
                     If None, uses default location relative to this file.

    Returns:
        The content of the prompt file as a string.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.

    Examples:
        >>> prompt = load_prompt("researcher_instructions")
        >>> prompt = load_prompt("write_todos_description.md")
    """
    if prompts_dir is None:
        # Default: prompts folder is sibling to this file
        prompts_dir = Path(__file__).parent / "prompts"

    # Ensure .md extension
    if not prompt_name.endswith(".md"):
        prompt_name = f"{prompt_name}.md"

    prompt_path = prompts_dir / prompt_name

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}\n"
            f"Available prompts in {prompts_dir}:\n"
            f"{', '.join(f.stem for f in prompts_dir.glob('*.md') if f.name != 'README.md')}"
        )

    return prompt_path.read_text(encoding="utf-8")


def list_available_prompts(prompts_dir: Path | None = None) -> list[str]:
    """List all available prompt files (excluding README).

    Args:
        prompts_dir: Optional custom path to prompts directory.

    Returns:
        List of prompt file names without .md extension.
    """
    if prompts_dir is None:
        prompts_dir = Path(__file__).parent / "prompts"

    if not prompts_dir.exists():
        return []

    return [f.stem for f in prompts_dir.glob("*.md") if f.name != "README.md"]


# Load all prompts as constants
WRITE_TODOS_DESCRIPTION: str = load_prompt("write_todos_description")
TODO_USAGE_INSTRUCTIONS: str = load_prompt("todo_usage_instructions")
LS_DESCRIPTION: str = load_prompt("ls_description")
READ_FILE_DESCRIPTION: str = load_prompt("read_file_description")
WRITE_FILE_DESCRIPTION: str = load_prompt("write_file_description")
FILE_USAGE_INSTRUCTIONS: str = load_prompt("file_usage_instructions")
SUMMARIZE_WEB_SEARCH: str = load_prompt("summarize_web_search")
RESEARCHER_INSTRUCTIONS: str = load_prompt("researcher_instructions")
TASK_DESCRIPTION_PREFIX: str = load_prompt("task_description_prefix")
SUBAGENT_USAGE_INSTRUCTIONS: str = load_prompt("subagent_usage_instructions")


# Example usage
if __name__ == "__main__":
    print("Available prompts:")
    for prompt in list_available_prompts():
        print(f"  - {prompt}")

    print("\nRESEARCHER_INSTRUCTIONS preview:")
    print(RESEARCHER_INSTRUCTIONS[:200] + "...")
