# Prompts Documentation

This directory contains all prompt templates and tool descriptions used in the deep-agent framework, extracted from `src/agent/ai/prompts.py`.

## File Organization

### Tool Descriptions

- **[write_todos_description.md](write_todos_description.md)** - Create and manage structured task lists
- **[ls_description.md](ls_description.md)** - List files in virtual filesystem
- **[read_file_description.md](read_file_description.md)** - Read content from virtual files with pagination
- **[write_file_description.md](write_file_description.md)** - Create or overwrite files in virtual filesystem

### Usage Instructions

- **[todo_usage_instructions.md](todo_usage_instructions.md)** - Guidelines for using TODO system
- **[file_usage_instructions.md](file_usage_instructions.md)** - Workflow for virtual file system operations
- **[subagent_usage_instructions.md](subagent_usage_instructions.md)** - How to delegate tasks to sub-agents

### System Prompts

- **[researcher_instructions.md](researcher_instructions.md)** - Instructions for research assistant agents
- **[summarize_web_search.md](summarize_web_search.md)** - Template for summarizing web search results
- **[task_description_prefix.md](task_description_prefix.md)** - Prefix for sub-agent task delegation

## Usage

These prompts are used throughout the deep-agent framework to guide agent behavior, tool usage, and task execution. Each file is a standalone markdown document that can be:

- Read and understood independently
- Modified for customization
- Referenced in code via the original Python constants
- Used as templates for new prompts

## Source

All prompts are maintained in `src/agent/ai/prompts.py` as Python string constants. This markdown documentation provides human-readable versions for easier review and editing.
