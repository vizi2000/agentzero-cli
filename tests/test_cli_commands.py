from cli.approval import ToolApprovalHandler
from cli.commands import CLISlashCommands


class DummyRenderer:
    def approved(self, *args, **kwargs):
        pass

    def tool_request(self, *args, **kwargs):
        pass

    def status(self, *args, **kwargs):
        pass

    def info(self, msg):
        pass

    def rejected(self, *args, **kwargs):
        pass


class DummyInput:
    def get_input(self, prompt):
        return ""

    def get_approval(self):
        return "a"


class DummyBackend:
    def __init__(self):
        self.security_mode = "balanced"
        self.whitelist = ["ls"]


def test_slash_parse_help():
    commands = CLISlashCommands()
    parsed = commands.parse("/help")
    assert parsed == ("help", [])


def test_tool_approval_whitelist():
    handler = ToolApprovalHandler(DummyRenderer(), DummyInput(), DummyBackend())
    event = {"tool_name": "terminal", "command": "ls -la"}
    assert handler.should_auto_approve(event)
