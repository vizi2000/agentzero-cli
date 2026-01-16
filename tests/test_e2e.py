import asyncio
import json

import pytest
from aiohttp import web

from backend import RemoteAgentBackend


@pytest.mark.asyncio
async def test_streaming_flow(tmp_path):
    async def handler(request):
        resp = web.StreamResponse(
            status=200,
            reason="OK",
            headers={"Content-Type": "text/event-stream"},
        )
        await resp.prepare(request)

        events = [
            {"type": "status", "content": "preflight"},
            {"type": "tool_request", "tool_name": "read_file", "command": "cat secrets"},
            {"type": "final_response", "content": "done"},
        ]

        for payload in events:
            line = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await resp.write(line.encode("utf-8"))
            await asyncio.sleep(0)

        await resp.write(b"data: [DONE]\n\n")
        await resp.write_eof()
        return resp

    app = web.Application()
    app.router.add_post("/api_message", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]

    config = {
        "connection": {
            "api_url": f"http://127.0.0.1:{port}/api_message",
            "workspace_root": str(tmp_path),
            "stream": True,
            "timeout_seconds": 2,
        },
        "context": {"enabled": False},
    }
    backend = RemoteAgentBackend(config)

    got = []
    async for event in backend.send_prompt("hi"):
        got.append(event)

    assert any(evt.get("type") == "tool_request" for evt in got)
    assert any(evt.get("type") == "final_response" for evt in got)

    await runner.cleanup()
