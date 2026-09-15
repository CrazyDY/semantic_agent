# Semantic Agent Event Runtime

A small runnable Agent Runtime for OpenAI-compatible `/chat/completions` endpoints using `requests`.

## Features

- OpenAI-compatible SSE parsing
- `reasoning_content` / `reasoning` compatibility
- Semantic events: `run.*`, `step.*`, `thinking.*`, `message.*`, `tool_call.*`, `tool_execute.*`, `error`
- Streaming tool-call argument accumulation
- Multiple parallel tool calls in one assistant turn
- Tool execution and multi-round `tool_calls -> tool result -> LLM`
- FastAPI SSE endpoint
- Built-in demo UI and optional Vue 3 frontend (`frontend/`)
- Vue chat input supports image uploads, drag-and-drop, and clipboard paste; images are sent as OpenAI-compatible `image_url` content parts
- The Vue UI can terminate an in-progress streamed response from the top bar


## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12+, pinned via `.python-version`)

## Setup

```bash
uv sync
```

`uv sync` creates a `.venv` and installs all dependencies from `uv.lock`.

Copy `.env.example` to `.env` and configure your model endpoint:

```text
LLM_BASE_URL=http://127.0.0.1:8000/v1
LLM_API_KEY=EMPTY
LLM_MODEL=your-model
```

`uv run` loads `.env` automatically. You can also export the variables manually:

```bash
# Windows PowerShell
$env:LLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:LLM_API_KEY="EMPTY"
$env:LLM_MODEL="your-model"

# Linux/macOS
export LLM_BASE_URL=http://127.0.0.1:8000/v1
export LLM_API_KEY=EMPTY
export LLM_MODEL=your-model
```

## Run

Start the FastAPI server:

```bash
uv run uvicorn semantic_agent.api:app --reload
```

Alternatively, start the equivalent Tornado API (the FastAPI API remains
unchanged):

```bash
uv run python -m semantic_agent.tornado_api
```

The Tornado server provides the same `GET /health` and SSE `POST /chat`
endpoints and accepts the same OpenAI-compatible text or multimodal message
content.

Open `http://127.0.0.1:8000/` to use the built-in demo UI.

Optional Vue 3 frontend:

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/chat` to the backend; open `http://127.0.0.1:5173/`.

## Event format

```text
event: thinking.delta
data: {"id":"run_x_reasoning","delta":"..."}
```

The frontend never needs to parse provider-specific `choices[].delta` fields.

## Important behavior

When Chat Completions returns `finish_reason=tool_calls`, the runtime does **not** end the run. It appends the complete assistant `tool_calls`, executes each registered tool, appends `role=tool` results, and calls the model again.

Replace `default_registry()` with your real business tools.
