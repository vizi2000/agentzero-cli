"""Tests for tool executor."""

import pytest
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.executor import (
    execute_shell,
    read_file,
    write_file,
    list_files,
    is_blocked,
    is_readonly,
    is_write_operation,
    execute_tool,
)


class TestSecurityChecks:
    """Tests for security validation."""
    
    def test_blocks_rm_rf_root(self):
        """Blocks rm -rf /"""
        blocked, reason = is_blocked("rm -rf /")
        assert blocked
        assert "rm -rf /" in reason
    
    def test_blocks_fork_bomb(self):
        """Blocks fork bomb"""
        blocked, _ = is_blocked(":(){ :|:& };:")
        assert blocked
    
    def test_allows_safe_commands(self):
        """Allows safe commands"""
        blocked, _ = is_blocked("ls -la")
        assert not blocked
        
        blocked, _ = is_blocked("cat file.txt")
        assert not blocked
    
    def test_readonly_detection(self):
        """Detects readonly commands"""
        assert is_readonly("ls -la")
        assert is_readonly("cat file.txt")
        assert is_readonly("git status")
        assert is_readonly("grep pattern file")
        
        assert not is_readonly("rm file")
        assert not is_readonly("mkdir dir")
    
    def test_write_operation_detection(self):
        """Detects write operations"""
        assert is_write_operation("rm file")
        assert is_write_operation("mkdir dir")
        assert is_write_operation("git push")
        assert is_write_operation("echo test > file")
        
        assert not is_write_operation("ls -la")
        assert not is_write_operation("cat file")


class TestShellExecution:
    """Tests for shell command execution."""
    
    @pytest.mark.asyncio
    async def test_echo_command(self):
        """Executes echo command"""
        result = await execute_shell("echo Hello")
        assert result.success
        assert "Hello" in result.output
        assert result.return_code == 0
    
    @pytest.mark.asyncio
    async def test_failed_command(self):
        """Handles failed commands"""
        result = await execute_shell("ls /nonexistent_dir_12345")
        assert not result.success
        assert result.return_code != 0
    
    @pytest.mark.asyncio
    async def test_blocked_command(self):
        """Blocks dangerous commands"""
        result = await execute_shell("rm -rf /")
        assert not result.success
        assert "blocked" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_timeout(self):
        """Handles command timeout"""
        result = await execute_shell("sleep 10", timeout=1)
        assert not result.success
        assert "timed out" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_working_directory(self):
        """Respects working directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await execute_shell("pwd", cwd=tmpdir)
            assert result.success
            assert tmpdir in result.output


class TestFileOperations:
    """Tests for file read/write operations."""
    
    @pytest.mark.asyncio
    async def test_read_file(self):
        """Reads file contents"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            f.flush()
            
            result = await read_file(f.name)
            assert result.success
            assert "test content" in result.output
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Handles nonexistent file"""
        result = await read_file("/nonexistent_file_12345.txt")
        assert not result.success
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_write_file(self):
        """Writes file contents"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            
            result = await write_file(path, "hello world")
            assert result.success
            
            assert os.path.exists(path)
            with open(path) as f:
                assert f.read() == "hello world"
    
    @pytest.mark.asyncio
    async def test_list_files(self):
        """Lists directory contents"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "file1.txt").touch()
            Path(tmpdir, "file2.txt").touch()
            Path(tmpdir, "subdir").mkdir()
            
            result = await list_files(tmpdir)
            assert result.success
            assert "file1.txt" in result.output
            assert "file2.txt" in result.output
            assert "subdir" in result.output


class TestExecuteTool:
    """Tests for the main execute_tool function."""
    
    @pytest.mark.asyncio
    async def test_shell_tool(self):
        """Executes shell tool"""
        events = []
        async for event in execute_tool("shell", "echo test"):
            events.append(event)
        
        types = [e["type"] for e in events]
        assert "status" in types
        assert "tool_output" in types
        
        # Check output contains result
        outputs = [e["content"] for e in events if e["type"] == "tool_output"]
        assert any("test" in o for o in outputs)
    
    @pytest.mark.asyncio
    async def test_read_file_tool(self):
        """Executes read_file tool"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("file content here")
            f.flush()
            
            events = []
            async for event in execute_tool("read_file", f.name):
                events.append(event)
            
            outputs = [e["content"] for e in events if e["type"] == "tool_output"]
            assert any("file content here" in o for o in outputs)
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_unknown_tool_defaults_to_shell(self):
        """Unknown tool defaults to shell execution"""
        events = []
        async for event in execute_tool("unknown_tool", "echo fallback"):
            events.append(event)
        
        outputs = [e["content"] for e in events if e["type"] == "tool_output"]
        assert any("fallback" in o for o in outputs)
