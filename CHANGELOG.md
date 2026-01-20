# Changelog

All notable changes to Agent Zero CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Preparing for public open source release

## [0.1.0] - 2025-01-12

### Added
- Initial beta release
- TUI interface with Textual framework
- CLI interface (non-TUI mode)
- Three security modes: `paranoid`, `balanced`, `god_mode`
- Tool approval system with human-in-the-loop
- Context builder with file tree, previews, git status
- 12 retro-inspired themes (C64, Atari, ZX Spectrum, Mac Classic, etc.)
- Multi-project workspace support
- Agent profile switching
- Real-time streaming of agent responses
- Live feed with status/thinking/tool events
- Built-in Space Invaders arcade game
- Shell command whitelist/blacklist
- Sensitive data redaction in context previews
- OpenRouter and MCP Gateway LLM provider support
- Observer system for workspace monitoring

### Security
- Context preview redaction for API keys and secrets
- Sensitive file exclusion (config.yaml, .env)
- Symlink traversal protection
