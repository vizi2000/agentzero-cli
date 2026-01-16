"""CSS styles for AgentZeroCLI application."""

CSS = """
/* Global shell */
Screen {
    background: $background;
    color: $foreground;
}
Header { background: $panel; color: $primary; text-style: bold; border: none; }
Footer { background: $panel; color: $text-muted; border: none; }

#app-body { height: 1fr; padding: 1; }
#brand-bar {
    height: 3;
    padding: 0 1;
    margin-bottom: 1;
    background: $panel;
    align: left middle;
    border: solid $boost;
}
#brand-title { color: $primary; text-style: bold; width: 1fr; }
#brand-meta { color: $text-muted; text-style: dim; width: 1fr; text-align: center; }
#brand-signal { color: $secondary; text-style: bold; width: 12; text-align: right; }
#main-row { height: 1fr; }

/* --- Chat Tabs --- */
#chat-tabs-bar {
    height: 3;
    background: $panel;
    border-bottom: solid $boost;
}
#new-tab-btn {
    width: 5;
    min-width: 5;
    background: $surface;
    color: $primary;
    border: none;
}
#new-tab-btn:hover { background: $panel; }

/* --- Chat --- */
#chat-area {
    width: 3fr;
    height: 1fr;
    margin-right: 1;
}
#chat-container {
    height: 1fr;
    border: none;
    background: $surface;
    padding: 1;
    scrollbar-color: $primary $panel;
}

#side-panel {
    width: 1fr;
    border: none;
    background: $panel;
    padding: 1;
    scrollbar-color: $secondary $panel;
}

.panel {
    background: $panel;
    padding: 1;
    margin-bottom: 1;
    border: solid $boost;
}
.panel:hover {
    border: solid $primary;
}
.panel-title { color: $secondary; text-style: bold; margin-bottom: 1; }

#activity-card { height: 12; }
#activity-feed {
    height: 1fr;
    background: $surface;
    color: $foreground;
    padding: 0 1;
    border: solid $boost;
    scrollbar-color: $secondary $panel;
    text-style: dim;
}

#arcade-card { height: 12; }
#arcade-screen {
    height: 1fr;
    background: $surface;
    color: $primary;
    padding: 0 1;
    text-style: dim;
    border: solid $boost;
}
#arcade-screen.waiting { color: $primary; }
#arcade-screen.idle { color: $text-muted; }

/* --- Messages --- */
.user-msg {
    color: $foreground;
    background: $panel;
    padding: 1;
    margin-bottom: 1;
    text-align: right;
    width: 100%;
    border: solid $primary;
}
.agent-thought {
    color: $text-muted;
    text-style: italic;
    padding-left: 2;
    margin-bottom: 0;
}
.agent-msg {
    color: $foreground;
    background: $panel;
    padding: 1;
    margin-bottom: 1;
    width: 100%;
    border: solid $boost;
}
.tool-output {
    color: $foreground;
    background: $surface;
    padding: 1;
    margin: 0 1 1 1;
    border: solid $boost;
    text-style: dim;
}
.system-msg {
    color: $foreground;
    background: $panel;
    padding: 1;
    margin-bottom: 1;
    border: solid $boost;
    text-style: dim;
}
.status-msg {
    color: $text-muted;
    padding: 0 1;
    margin-bottom: 1;
    text-style: dim;
}

/* --- Thinking Indicator --- */
.thinking-indicator {
    color: $text-muted;
    text-style: italic;
    padding: 1;
    margin-bottom: 1;
    border-left: solid $primary;
    background: $surface;
}
.thinking-indicator.active {
    color: $primary;
}
.thinking-stream {
    color: $text-muted;
    text-style: italic dim;
    padding: 1;
    margin-bottom: 1;
    border: solid $boost;
    background: $surface;
}
.thinking-stream:hover {
    background: $panel;
}

/* --- Input --- */
Input {
    background: $surface;
    color: $foreground;
    border: solid $boost;
}
#input-area {
    height: auto;
    min-height: 3;
    max-height: 8;
    padding: 0 1;
    border: solid $boost;
}
#input-area:focus {
    border: solid $primary;
}
TextArea#input-area {
    height: auto;
    min-height: 3;
    max-height: 8;
}

/* --- Tool Preview --- */
#preview-container { height: 10; margin: 1 0; }
#preview-box {
    background: $surface;
    color: $foreground;
    padding: 1;
    border: solid $boost;
}

/* --- Security Modal --- */
ToolApprovalScreen { align: center middle; background: $background; }
#dialog {
    padding: 1;
    width: 78;
    height: auto;
    border: solid $warning;
    background: $panel;
}
#risk-header {
    background: $warning;
    color: $background;
    text-align: center;
    text-style: bold;
    padding: 1;
    width: 100%;
}
#command-box {
    background: $surface;
    color: $warning;
    padding: 1;
    margin: 1 0;
    border: solid $boost;
    text-align: center;
}
#buttons-layout { align: center bottom; height: auto; margin-top: 1; margin-bottom: 1; }
Button {
    margin: 0 1;
    border: solid $boost;
    padding: 0 2;
}
Button.success { background: $success; color: $background; }
Button.warning { background: $warning; color: $background; }
Button.error { background: $error; color: $background; }
Button:focus { text-style: bold; border: solid $primary; }
.explanation-text { color: $warning; padding: 1; margin-top: 1; border-top: dashed $boost; }

/* --- File Upload Screen --- */
FileUploadScreen { align: center middle; background: $background; }
#upload-dialog {
    width: 80;
    height: 30;
    border: solid $primary;
    background: $panel;
    padding: 1;
}
#upload-header {
    height: 2;
    text-align: center;
    text-style: bold;
    color: $primary;
}
#file-tree {
    height: 1fr;
    border: solid $boost;
    background: $surface;
}
#upload-buttons {
    height: 3;
    align: center middle;
}

/* --- Hierarchical Menu --- */
#menu-container {
    dock: left;
    width: 30;
    height: 100%;
    background: $panel;
    border-right: solid $boost;
    layer: menu;
}
#menu-container.hidden { display: none; }
#main-menu {
    height: 1fr;
    padding: 1;
}

/* --- Space Invaders Game --- */
SpaceInvadersScreen { background: #000; align: center middle; }
#game-header {
    dock: top;
    height: 2;
    background: #111;
    color: #0f0;
    text-align: center;
    text-style: bold;
}
#game-board {
    width: 64;
    height: 26;
    background: #000;
    color: #0f0;
    border: heavy #333;
}
#game-footer {
    dock: bottom;
    height: 1;
    color: #666;
    text-align: center;
}

/* --- Retro Game Screen (legacy) --- */
RetroGameScreen { background: #050510; align: center middle; }
#game-board-legacy {
    layout: grid;
    grid-size: 5 6;
    grid-gutter: 1;
    width: auto;
    height: auto;
    border: heavy #444;
    background: #000;
    padding: 1;
}
.city-node {
    width: 18;
    height: 3;
    background: #111;
    color: #555;
    border: solid #333;
    content-align: center middle;
    text-align: center;
}
.city-node:hover { background: #222; }
.evil-agi {
    background: #550000;
    color: #ffaaaa;
    border: double #ff0000;
    text-style: bold;
}
.secure {
    background: #002200;
    color: #00aa00;
    border: solid #005500;
}
.agent-here {
    background: #004400;
    color: #ffffff;
    border: thick #ffffff;
    text-style: bold;
}
.destroyed {
    background: #222;
    color: #444;
    border: none;
    text-style: strike;
}

/* --- Theme Accents --- */
.theme-atari-800xl #brand-bar { border: heavy $boost; }
.theme-commodore-c64 #brand-bar { border: double $boost; }
.theme-zx-spectrum #brand-bar { border: heavy $boost; }
.theme-atari-st #brand-bar { border: tall $boost; }
.theme-amiga-500 #brand-bar { border: wide $boost; }

.theme-ms-dos-xt-pc Header,
.theme-ms-dos-xt-pc Footer { text-style: bold; }
.theme-ms-dos-xt-pc #chat-container,
.theme-ms-dos-xt-pc #side-panel,
.theme-ms-dos-xt-pc .panel { border: ascii $boost; }
.theme-ms-dos-xt-pc #brand-bar { border: ascii $boost; }

.theme-mac-one #chat-container,
.theme-mac-classic #chat-container,
.theme-mac-aqua #chat-container { border: solid $boost; }
.theme-mac-one .panel,
.theme-mac-classic .panel,
.theme-mac-aqua .panel { border: solid $boost; }
"""
