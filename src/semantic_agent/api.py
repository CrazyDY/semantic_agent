from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agent import AgentRuntime
from .config import Settings
from .llm_client import OpenAICompatibleClient
from .tools import default_registry
from .tool_approval import ToolApprovalCoordinator


settings = Settings()
llm = OpenAICompatibleClient(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    model=settings.LLM_MODEL,
    connect_timeout=settings.LLM_CONNECT_TIMEOUT,
    read_timeout=settings.LLM_READ_TIMEOUT,
)
tools = default_registry()
agent = AgentRuntime(llm, tools, max_rounds=settings.AGENT_MAX_ROUNDS)
tool_approvals = ToolApprovalCoordinator()

app = FastAPI(title="Semantic Agent Event Runtime", version="1.0.0")


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(min_length=1)
    extra_body: dict[str, Any] | None = None


class ToolApprovalRequest(BaseModel):
    run_id: str
    call_id: str
    approved: bool


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "model": settings.LLM_MODEL, "base_url": settings.LLM_BASE_URL}


@app.post("/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    def generate():
        for event in agent.run(request.messages, request.extra_body, tool_approvals.wait):
            yield event.to_sse()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/tool-approvals")
def approve_tool(request: ToolApprovalRequest) -> dict[str, bool]:
    tool_approvals.decide(request.run_id, request.call_id, request.approved)
    return {"ok": True}


def main() -> None:
    uvicorn.run(app="semantic_agent.api:app", host="0.0.0.0")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return FRONTEND


FRONTEND = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>Semantic Agent</title>
<style>
body{font-family:Arial,sans-serif;max-width:900px;margin:30px auto;padding:0 16px;background:#f7f7f7}
#log{background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px;min-height:400px;white-space:pre-wrap}
.row{margin:8px 0;padding:8px 12px;border-radius:6px;background:#fafafa}
.type{font-weight:700}.thinking{background:#fffbe6}.tool{background:#f0f7ff}.msg{background:#f3fff3}.error{background:#fff0f0}
textarea{width:100%;height:100px}.bar{display:flex;gap:8px;margin-top:8px}button{padding:8px 16px}
</style>
</head>
<body>
<h2>Semantic Agent Event Demo</h2>
<textarea id="input">北京天气怎么样？</textarea>
<div class="bar"><button onclick="send()">发送</button><button onclick="clearLog()">清空</button></div>
<div id="log"></div>
<script>
const log=document.getElementById('log');
function clearLog(){log.innerHTML=''}
function add(type,data){const div=document.createElement('div');div.className='row '+(type.startsWith('thinking')?'thinking':type.startsWith('tool')?'tool':type.startsWith('message')?'msg':type==='error'?'error':'');div.innerHTML='<span class="type">'+type+'</span> '+escapeHtml(JSON.stringify(data));log.appendChild(div);log.scrollTop=log.scrollHeight}
function escapeHtml(s){return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
async function send(){clearLog();const q=document.getElementById('input').value;const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:q}]})});if(!r.ok){add('error',{message:await r.text()});return}const reader=r.body.getReader(),dec=new TextDecoder();let buf='';while(true){const {value,done}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});const parts=buf.split('\n\n');buf=parts.pop();for(const block of parts){let type='',data='';for(const line of block.split('\n')){if(line.startsWith('event:'))type=line.slice(6).trim();if(line.startsWith('data:'))data=line.slice(5).trim()}if(type&&data){try{add(type,JSON.parse(data))}catch{}}}}}
</script>
</body>
</html>'''
