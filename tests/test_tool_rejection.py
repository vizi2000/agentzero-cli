from backend import RemoteAgentBackend


class DummyBackend(RemoteAgentBackend):
    def __init__(self):
        config = {"connection": {"api_url": "http://example", "workspace_root": "."}}
        super().__init__(config)


def test_reject_tool_results_false():
    backend = DummyBackend()
    event = {"tool_name": "write_file", "command": "write path", "tool_call_id": "z"}
    results = []

    async def collect():
        async for evt in backend.reject_tool(event, reason="denied"):
            results.append(evt)

    import asyncio

    asyncio.run(collect())

    assert any(evt.get("type") == "status" for evt in results)
    assert backend.context_id is None
