# Open WebUI - Deep Agent UI Specifications

## Overview

Simple UI for displaying Deep Agent execution with ONE global collapse to show/hide all execution steps.

---

## Current Implementation

### Design Principle

**Simple**: ONE global collapse block containing ALL intermediate steps.
**Clean**: When collapsed, user sees only the final AI answer.

### Output Format

```markdown
<details>
<summary>🔍 Execution Steps (5 tools)</summary>

**🤖 AI:** Let me help you research MCP. I'll start by setting up the workspace...

**🔧 ls:** file1.txt, file2.py...

**🔧 write_file:** ✓ completed

**🔧 write_todos:** ✓ completed

**🤖 AI:** Now let me delegate the research task to investigate MCP...

**🔧 task:** [Sub-agent's full response about MCP research...]

</details>

Based on my research, here's a comprehensive overview of MCP and its various meanings...
```

### Collapse Behavior

| State | What User Sees |
|-------|---------------|
| **Collapsed** (default) | Only the final AI message |
| **Expanded** | All intermediate steps: AI messages + tool calls |

---

## UI Requirements

### 1. Global Collapsible Block

| Requirement | Description |
|-------------|-------------|
| **Single collapse** | ONE `<details>` block for ALL steps |
| **Collapsed by default** | Only final answer visible |
| **Click to expand** | See all intermediate AI messages + tool calls |
| **Tool count in header** | "🔍 Execution Steps (N tools)" |

### 2. Step Types Inside Collapse

| Step Type | Format |
|-----------|--------|
| AI message | `**🤖 AI:** [message content]` |
| Tool call | `**🔧 tool_name:** [result preview]` |

### 3. Tool Result Display

| Result Type | Display |
|-------------|---------|
| Normal output | Truncated preview (200 chars max) |
| Empty/Command objects | "✓ completed" |
| Long outputs | Truncated with "..." |
| HTML in results | Escaped for safety |

### 4. Streaming Behavior (Real-time)

| Event | Action |
|-------|--------|
| First tool starts | Open `<details open>` + stream AI content before it |
| Tool ends | Stream tool result immediately |
| More tools | Stream each step as it completes |
| Final AI starts | Close `</details>` + stream final answer |

**Key features**:
- Uses `<details open>` so steps are visible during execution
- Each step streams immediately (real-time feedback)
- User can collapse the block after execution completes
- Final AI message always visible outside the collapse

---

## Desired Improvements (Future)

### A. Tool Result Details
- Expandable full result view per tool (not just preview)
- Copy button for tool outputs

### B. Visual Indicators
- Spinner while agent is working
- Success/error icons per tool

### C. Filter Options
- Search within tool results

---

## API Contract

### Request
```json
POST /chat/stream
{
  "messages": [...],
  "stream": true,
  "show_tool_details": true  // false = hide collapse block
}
```

### SSE Response Events (Real-time)
```json
// 1. Open collapse (on first tool)
{"content": "\n<details open>\n<summary>🔍 Execution Steps</summary>\n\n"}

// 2. Stream each step as it happens
{"content": "**🤖 AI:** Let me research this...\n\n"}
{"content": "**🔧 tavily_search:** Found 3 results...\n\n"}
{"content": "**🔧 think_tool:** Reflection recorded...\n\n"}

// 3. Close collapse
{"content": "\n</details>\n\n"}

// 4. Stream final AI message
{"content": "Based on my research..."}

// 5. End
{"done": true}
```

---

## Open WebUI Pipeline Valve

| Valve | Type | Default | Description |
|-------|------|---------|-------------|
| `api_url` | string | `http://deep-agent-api:8000` | Backend API URL |
| `stream` | bool | `true` | Enable streaming |
| `show_tool_details` | bool | `true` | Show/hide execution steps collapse |

---

## Technical Notes

- Uses `<details open>` during execution (expanded by default)
- User can collapse after execution completes
- Real-time streaming: each step emitted immediately
- Final AI message always outside collapse (visible when collapsed)
- Markdown rendered by Open WebUI
