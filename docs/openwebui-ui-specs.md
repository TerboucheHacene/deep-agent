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

## Architecture: Typed Events + Open WebUI Pipe

```
┌─────────────────┐     SSE (typed JSON)     ┌──────────────────┐     events     ┌──────────────┐
│  Deep Agent     │ ───────────────────────► │  Open WebUI Pipe │ ─────────────► │  Open WebUI  │
│  Backend        │                          │  (routing layer) │                │  Frontend    │
└─────────────────┘                          └──────────────────┘                └──────────────┘
```

**Benefits:**
- Clean separation: Backend emits data, Pipe routes to UI components
- Native Open WebUI features: status bar, citations, streaming
- No HTML/markdown hacks in backend
- Tool results as clickable citations (preview + full content)

---

## Typed Event Protocol

### Event Types

| Type | Purpose | Open WebUI Mapping |
|------|---------|-------------------|
| `status` | Progress updates | `__event_emitter__` → Status bar |
| `tool_start` | Tool invocation begins | `__event_emitter__` → Status bar |
| `tool_end` | Tool result available | `__event_emitter__` → Citation |
| `token` | AI response token | `yield` → Chat bubble |
| `agent_start` | Sub-agent begins | `__event_emitter__` → Status bar |
| `agent_end` | Sub-agent completes | `__event_emitter__` → Status bar |
| `done` | Stream complete | Finalize status bar |

### Event Schemas

#### Status Event
```json
{
  "type": "status",
  "data": {
    "description": "Thinking...",
    "agent_depth": 0
  }
}
```

#### Tool Start Event
```json
{
  "type": "tool_start",
  "data": {
    "tool_id": "run_abc123",
    "name": "web_search",
    "agent_depth": 0
  }
}
```

#### Tool End Event
```json
{
  "type": "tool_end",
  "data": {
    "tool_id": "run_abc123",
    "name": "web_search",
    "result": "Found 5 results about MCP...",
    "agent_depth": 0
  }
}
```

#### Token Event
```json
{
  "type": "token",
  "data": {
    "content": "Based",
    "agent_depth": 0
  }
}
```

#### Agent Start Event
```json
{
  "type": "agent_start",
  "data": {
    "agent_id": "run_xyz789",
    "name": "Research Sub-agent",
    "depth": 1
  }
}
```

#### Agent End Event
```json
{
  "type": "agent_end",
  "data": {
    "agent_id": "run_xyz789",
    "depth": 1
  }
}
```

#### Done Event
```json
{
  "type": "done"
}
```

---

## API Contract

### Request
```json
POST /chat/stream
{
  "messages": [...],
  "stream": true
}
```

### SSE Response Format
```
data: {"type": "status", "data": {"description": "Starting research..."}}

data: {"type": "tool_start", "data": {"tool_id": "abc", "name": "web_search", "agent_depth": 0}}

data: {"type": "token", "data": {"content": "Let me ", "agent_depth": 0}}

data: {"type": "token", "data": {"content": "search...", "agent_depth": 0}}

data: {"type": "tool_end", "data": {"tool_id": "abc", "name": "web_search", "result": "Found 3 articles...", "agent_depth": 0}}

data: {"type": "agent_start", "data": {"agent_id": "xyz", "name": "task", "depth": 1}}

data: {"type": "token", "data": {"content": "Analyzing ", "agent_depth": 1}}

data: {"type": "agent_end", "data": {"agent_id": "xyz", "depth": 1}}

data: {"type": "token", "data": {"content": "Based on my research...", "agent_depth": 0}}

data: {"type": "done"}

```

---

## Open WebUI Pipe

### Valves Configuration

| Valve | Type | Default | Description |
|-------|------|---------|-------------|
| `DEEP_AGENT_URL` | string | `http://localhost:8000` | Backend API URL |
| `SHOW_TOOL_CITATIONS` | bool | `true` | Show tool results as citations |
| `SHOW_SUBAGENT_STATUS` | bool | `true` | Distinguish sub-agent activity |

### Event Routing Logic

```python
async def pipe(self, body: dict, __event_emitter__=None):
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", f"{self.valves.DEEP_AGENT_URL}/chat/stream", json=body) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                event = json.loads(line[6:])
                event_type = event.get("type")
                data = event.get("data", {})

                if event_type == "status":
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": data["description"], "done": False}
                    })

                elif event_type == "tool_start":
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": f"🔧 {data['name']}...", "done": False}
                    })

                elif event_type == "tool_end":
                    # Emit as citation for preview
                    await __event_emitter__({
                        "type": "source",
                        "data": {
                            "source": {"name": f"🔧 {data['name']}"},
                            "document": [data["result"][:500]],
                            "metadata": [{"full_result": data["result"]}]
                        }
                    })

                elif event_type == "token":
                    yield data["content"]

                elif event_type == "agent_start":
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": f"🤖 Sub-agent: {data['name']}...", "done": False}
                    })

                elif event_type == "agent_end":
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": "Sub-agent completed", "done": True}
                    })

                elif event_type == "done":
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": "Complete", "done": True}
                    })
```

---

## UI Behavior

### Status Bar
- Shows current operation in Open WebUI's native "Thinking" indicator
- Updates in real-time as agent works
- Sub-agent activity distinguished with "🤖 Sub-agent:" prefix

### Chat Bubble
- Tokens stream directly into the response
- Smooth, real-time typing effect

### Citations (Tool Results)
- Each tool result appears as a clickable citation pill
- Click to see full tool output
- Provides preview without cluttering the response

---

## Technical Notes

- SSE format: `data: {json}\n\n`
- Each event is a complete JSON object
- `agent_depth` tracks nesting level (0 = main agent, 1+ = sub-agents)
- Pipe handles all UI formatting, backend stays clean

---

## Installation Guide

### 1. Start the Deep Agent Backend

```bash
# From the deep-agent directory
uvicorn agent.services.api.main:app --host 0.0.0.0 --port 8000
```

### 2. Install the Pipe in Open WebUI

1. Go to **Admin Panel** → **Functions**
2. Click **+** to add a new function
3. Select type: **Pipe**
4. Copy the contents of `openwebui/deep_agent_pipe.py`
5. Click **Save**
6. Enable the function

### 3. Configure Valves

In the function settings, configure:

| Valve | Description | Default |
|-------|-------------|---------|
| `DEEP_AGENT_URL` | Backend API URL | `http://localhost:8000` |
| `SHOW_TOOL_CITATIONS` | Show tool results as citations | `true` |
| `SHOW_SUBAGENT_STATUS` | Show sub-agent activity | `true` |
| `REQUEST_TIMEOUT` | Timeout in seconds | `300` |

### 4. Use the Pipe

1. In Open WebUI chat, select **Deep Agent Pipe** as your model
2. Send a message
3. Watch the status bar update and tokens stream in real-time
4. Click citations to see full tool outputs

---

## File Structure

```
deep-agent/
├── src/agent/services/api/routes/chat.py  # Backend streaming API
├── openwebui/deep_agent_pipe.py           # Open WebUI Pipe
└── docs/openwebui-ui-specs.md             # This specification
```
