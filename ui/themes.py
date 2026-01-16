"""Theme definitions for AgentZeroCLI application."""

from textual.theme import Theme

DEFAULT_THEME = "Studio Dark"

THEME_ALIASES = {
    "default": DEFAULT_THEME,
    "claude": "Studio Light",
    "gemini": "Studio Light",
    "studio light": "Studio Light",
    "studio-light": "Studio Light",
    "studio_light": "Studio Light",
    "studio dark": "Studio Dark",
    "studio-dark": "Studio Dark",
    "studio_dark": "Studio Dark",
    "hacker_green": "MS DOS XT PC",
    "hacker-green": "MS DOS XT PC",
}


def _slugify_theme(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


THEME_PRESETS = {
    "Studio Light": Theme(
        name="Studio Light",
        primary="#2563eb",
        secondary="#0ea5e9",
        warning="#f59e0b",
        error="#ef4444",
        success="#22c55e",
        accent="#2563eb",
        foreground="#0f172a",
        background="#f6f7fb",
        surface="#f8fafc",
        panel="#ffffff",
        boost="#e2e8f0",
        dark=False,
    ),
    "Studio Dark": Theme(
        name="Studio Dark",
        primary="#60a5fa",
        secondary="#34d399",
        warning="#f59e0b",
        error="#ef4444",
        success="#22c55e",
        accent="#60a5fa",
        foreground="#e5e7eb",
        background="#0b0d10",
        surface="#0f141a",
        panel="#111827",
        boost="#1f2937",
        dark=True,
    ),
    "High Tech 2026": Theme(
        name="High Tech 2026",
        primary="#7dd3fc",
        secondary="#34d399",
        warning="#f5a524",
        error="#ff5e5e",
        success="#22c55e",
        accent="#7dd3fc",
        foreground="#e5e7eb",
        background="#0b0d10",
        surface="#0f141a",
        panel="#111827",
        boost="#1f2937",
        dark=True,
    ),
    "Atari 800XL": Theme(
        name="Atari 800XL",
        primary="#6aa0ff",
        secondary="#f3d34a",
        warning="#f3d34a",
        error="#ff7a7a",
        success="#5bd67a",
        accent="#6aa0ff",
        foreground="#e8f1ff",
        background="#13224f",
        surface="#142454",
        panel="#1b2f66",
        boost="#2b4180",
        dark=True,
    ),
    "Commodore C64": Theme(
        name="Commodore C64",
        primary="#8b83e0",
        secondary="#a7e2ff",
        warning="#ffd166",
        error="#ff8a8a",
        success="#79e08d",
        accent="#8b83e0",
        foreground="#d6d1ff",
        background="#352879",
        surface="#2f236b",
        panel="#40318e",
        boost="#4b3aa4",
        dark=True,
    ),
    "ZX Spectrum": Theme(
        name="ZX Spectrum",
        primary="#ff005c",
        secondary="#00f0ff",
        warning="#ffd200",
        error="#ff5a5a",
        success="#4bdc7a",
        accent="#ff005c",
        foreground="#f2f2f2",
        background="#000000",
        surface="#090909",
        panel="#111111",
        boost="#1a1a1a",
        dark=True,
    ),
    "Atari ST": Theme(
        name="Atari ST",
        primary="#7cff9a",
        secondary="#f4b400",
        warning="#f4b400",
        error="#ff7a7a",
        success="#7cff9a",
        accent="#7cff9a",
        foreground="#d7f5e3",
        background="#1b1e1d",
        surface="#1f2322",
        panel="#232726",
        boost="#2a2f2d",
        dark=True,
    ),
    "Amiga 500": Theme(
        name="Amiga 500",
        primary="#7aa2ff",
        secondary="#ff8fb1",
        warning="#ff8fb1",
        error="#ff6f7f",
        success="#7aa2ff",
        accent="#7aa2ff",
        foreground="#f4ead7",
        background="#0e1028",
        surface="#141838",
        panel="#171a3a",
        boost="#1c2148",
        dark=True,
    ),
    "MS DOS XT PC": Theme(
        name="MS DOS XT PC",
        primary="#33ff33",
        secondary="#00aa00",
        warning="#ffff00",
        error="#ff3333",
        success="#00ff00",
        accent="#33ff33",
        foreground="#33ff33",
        background="#000000",
        surface="#0a0a0a",
        panel="#0c0c0c",
        boost="#141414",
        dark=True,
    ),
    "Mac One": Theme(
        name="Mac One",
        primary="#000000",
        secondary="#555555",
        warning="#888888",
        error="#333333",
        success="#000000",
        accent="#000000",
        foreground="#000000",
        background="#ffffff",
        surface="#f0f0f0",
        panel="#e8e8e8",
        boost="#d0d0d0",
        dark=False,
    ),
    "Mac Classic": Theme(
        name="Mac Classic",
        primary="#000080",
        secondary="#0000cc",
        warning="#cc9900",
        error="#cc0000",
        success="#008000",
        accent="#000080",
        foreground="#000000",
        background="#c0c0c0",
        surface="#d4d4d4",
        panel="#e0e0e0",
        boost="#b0b0b0",
        dark=False,
    ),
    "Mac Aqua": Theme(
        name="Mac Aqua",
        primary="#0066cc",
        secondary="#00aaff",
        warning="#ff9500",
        error="#ff3b30",
        success="#34c759",
        accent="#0066cc",
        foreground="#1d1d1f",
        background="#f5f5f7",
        surface="#ffffff",
        panel="#e8e8ed",
        boost="#d1d1d6",
        dark=False,
    ),
}


def resolve_theme_name(theme_name: str) -> str:
    """Resolve theme name to canonical form."""
    if not theme_name:
        return DEFAULT_THEME
    raw = str(theme_name).strip()
    if raw in THEME_PRESETS:
        return raw
    alias = THEME_ALIASES.get(raw.lower())
    if alias:
        return alias
    slug = _slugify_theme(raw)
    for candidate in THEME_PRESETS.keys():
        if _slugify_theme(candidate) == slug:
            return candidate
    return DEFAULT_THEME
