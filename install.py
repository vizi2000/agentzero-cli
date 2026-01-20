import os

# Definicje zawartości plików
files = {
    "requirements.txt": """textual>=0.40.0
pyyaml>=6.0""",

    "config.yaml": """# Konfiguracja Agent Zero CLI

connection:
  host: "localhost"
  port: 8000
  api_key: "sekretny-klucz"

security:
  # Tryby: 'paranoid' (pytaj o wszystko), 'balanced' (auto-read, ask-write), 'god_mode' (rób wszystko)
  mode: "balanced"
  
  # Automatycznie zatwierdzaj te komendy (tylko w trybie balanced)
  whitelist:
    - "ls"
    - "dir"
    - "cat"
    - "echo"
    - "git status"
    - "pwd"
    - "whoami"

  # Zawsze blokuj lub wymagaj potwierdzenia (nadpisuje whitelist)
  blacklist_patterns:
    - "rm -rf"
    - "format"
    - "mkfs"
    - ":(){ :|:& };:" # Fork bomb
    - "shutdown"

ui:
  theme: "hacker_green"
  show_timestamps: true""",

    "backend.py": """import asyncio
import random

class MockAgentBackend:
    \"\"\"
    Klasa symulująca zachowanie Agenta Zero po drugiej stronie sieci.
    Docelowo ta klasa zostanie zastąpiona klientem WebSocket.
    \"\"\"

    async def send_prompt(self, user_text: str):
        \"\"\"Symuluje wysłanie promptu do agenta i otrzymanie strumienia myśli.\"\"\"
        
        # 1. Symulacja opóźnienia sieci
        yield {"type": "status", "content": "Łączenie z Agentem..."}
        await asyncio.sleep(0.5)
        
        yield {"type": "status", "content": "Agent analizuje zadanie..."}
        await asyncio.sleep(1.0)

        # 2. Symulacja procesu myślowego (Chain of Thought)
        thoughts = [
            f"Użytkownik prosi o: '{user_text}'.",
            "Analizuję strukturę plików w katalogu roboczym...",
            "Wykryłem stare pliki tymczasowe w ./build.",
            "Muszę wyczyścić środowisko przed rozpoczęciem pracy."
        ]

        for thought in thoughts:
            yield {"type": "thought", "content": thought}
            await asyncio.sleep(0.8) # Symulacja "pisania" przez AI

        # 3. Symulacja decyzji o użyciu narzędzia (Tool Call)
        # W prawdziwej aplikacji to przyjdzie z JSON-a od Agenta
        yield {
            "type": "tool_request",
            "tool_name": "terminal",
            "command": "rm -rf ./build/*",
            "reason": "Wymagane czyszczenie cache przed kompilacją.",
            "risk_level": "high"
        }

    async def explain_risk(self, command: str):
        \"\"\"Symuluje zapytanie do LLM o wyjaśnienie ryzyka danej komendy.\"\"\"
        await asyncio.sleep(1.5) # Chwila "namysłu"
        return (
            f"[bold yellow]ANALIZA AI:[/]\\n"
            f"Komenda [i]{command}[/i] trwale usuwa pliki bez przenoszenia do kosza.\\n"
            f"W kontekście Twojego projektu, katalog [i]./build[/i] zawiera tylko pliki generowane automatycznie.\\n"
            f"[bold green]WERDYKT:[/b] Bezpieczne, jeśli nie trzymasz tam kodu źródłowego."
        )

    async def execute_tool(self, command: str):
        \"\"\"Symuluje wykonanie narzędzia po akceptacji.\"\"\"
        yield {"type": "status", "content": f"Wykonywanie: {command}..."}
        await asyncio.sleep(1.0)
        yield {"type": "tool_output", "content": "Deleted 42 files.\\nDirectory cleaned."}
        yield {"type": "final_response", "content": "Zadanie wykonane. Środowisko jest czyste."}""",

    "main.py": r'''import asyncio
import yaml
import random
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll, Grid
from textual.widgets import Header, Footer, Input, Static, Button, Label, Markdown
from textual.screen import ModalScreen, Screen
from textual.worker import Worker
from textual.binding import Binding

# Importujemy nasz symulator backendu
from backend import MockAgentBackend

# --- Ładowanie Konfiguracji ---
try:
    with open("config.yaml", "r") as f:
        CONFIG = yaml.safe_load(f)
except FileNotFoundError:
    CONFIG = {"security": {"mode": "balanced"}} # Fallback

# --- STYLE CSS ---
CSS = """
/* Globalne style */
Screen { background: #1e1e1e; color: #00ff41; }

/* --- Sekcja Chatu --- */
#chat-container {
    height: 1fr;
    border: solid #333;
    background: #0d0d0d;
    padding: 1;
    margin: 1;
    scrollbar-color: #00ff41 #333;
}

.user-msg { color: #ffffff; background: #005f00; padding: 1; margin-bottom: 1; text-align: right; width: 100%; border-right: thick #00ff41; }
.agent-thought { color: #888888; text-style: italic; padding-left: 2; margin-bottom: 0; }
.agent-msg { color: #aaffaa; background: #111111; border-left: thick #00ff41; padding: 1; margin-bottom: 1; width: 100%; }
.tool-output { color: #00ccff; background: #001122; padding: 1; margin: 0 2; border: dashed #005577; }

/* --- Modal Bezpieczeństwa --- */
ToolApprovalScreen { align: center middle; background: rgba(0, 0, 0, 0.85); }
#dialog { padding: 0 1; width: 70; height: auto; border: double #ff0000; background: #1a0000; }
#risk-header { background: #ff0000; color: #ffffff; text-align: center; text-style: bold; padding: 1; width: 100%; }
#command-box { background: #330000; color: #ffaaaa; padding: 1; margin: 1 0; border: solid #880000; text-align: center; }
#buttons-layout { align: center bottom; height: auto; margin-top: 1; margin-bottom: 1; }
Button { margin: 0 1; border: none; }
Button.success { background: #008800; color: white; }
Button.warning { background: #aa8800; color: black; }
Button.error { background: #880000; color: white; }
Button:focus { text-style: bold; border: wide #ffffff; }
.explanation-text { color: #ffddaa; padding: 1; margin-top: 1; border-top: dashed #555; }

/* --- GAME SCREEN (Agent ZUSA: Poland Mission) --- */
RetroGameScreen { background: #050510; align: center middle; }
#game-header { dock: top; height: 3; content-align: center middle; background: #111; color: #00ff41; text-style: bold; border-bottom: solid #333; }

#game-board { 
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

/* Stany gry */
.evil-agi { 
    background: #550000; 
    color: #ffaaaa; 
    border: double #ff0000; 
    text-style: bold blink; 
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
"""

# --- MODAL: EKRAN WERYFIKACJI ---
class ToolApprovalScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("left", "focus_previous", "Lewo", show=False),
        Binding("right", "focus_next", "Prawo", show=False),
    ]

    def __init__(self, tool_name: str, command: str, reason: str, backend: MockAgentBackend):
        super().__init__()
        self.tool_name = tool_name
        self.command = command
        self.reason = reason
        self.backend = backend

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"⚠️ AGENT ZERO: INTERWENCJA BEZPIECZEŃSTWA", id="risk-header")
            yield Label(f"\n[bold]Narzędzie:[/] {self.tool_name}", markup=True)
            yield Label(f"[bold]Powód:[/] {self.reason}", markup=True)
            yield Static(f"$ {self.command}", id="command-box")
            yield Static("", id="explanation-area", classes="explanation-text")
            with Horizontal(id="buttons-layout"):
                yield Button("Zatwierdź (Y)", classes="success", id="approve")
                yield Button("Wyjaśnij (E)", classes="warning", id="explain")
                yield Button("Odrzuć (N)", classes="error", id="reject")

    def on_mount(self) -> None:
        self.query_one("#explain").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "approve": self.dismiss("approved")
        elif btn_id == "reject": self.dismiss("rejected")
        elif btn_id == "explain":
            explanation_widget = self.query_one("#explanation-area", Static)
            explanation_widget.update("[blink]Pytam model AI o analizę ryzyka...[/]")
            explanation = await self.backend.explain_risk(self.command)
            explanation_widget.update(explanation)
            event.button.disabled = True
            event.button.label = "Analiza Gotowa"
            self.query_one("#reject").focus()

# --- RETRO GAME SCREEN: AGENT ZUSA (THE ONES) ---
class RetroGameScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Powrót")]

    CITIES = [
        "Warszawa", "Kraków", "Łódź", "Wrocław", "Poznań",
        "Gdańsk", "Szczecin", "Bydgoszcz", "Lublin", "Białystok",
        "Katowice", "Gdynia", "Częstochowa", "Radom", "Toruń",
        "Sosnowiec", "Rzeszów", "Kielce", "Gliwice", "Zabrze",
        "Olsztyn", "Bielsko-Biała", "Bytom", "Zielona Góra", "Rybnik",
        "Pszczew", "Maków Podh."
    ]

    def compose(self) -> ComposeResult:
        yield Label("MISSION: POLAND | AGENT: THE ONES (Zero)", id="game-header")
        with Container(id="game-board"):
            for i, city in enumerate(self.CITIES):
                yield Button(f"{city}", classes="city-node", id=f"city-{i}")
        yield Footer()

    def on_mount(self) -> None:
        self.tokens = 50 # Startowe Tokeny
        self.cities_lost = 0
        self.agent_pos = 0 # Start w Warszawie
        
        # FIX: Konwersja DOMQuery na listę, aby działało .index()
        self.buttons = list(self.query(".city-node"))
        
        # Oznacz start
        self.update_agent_visuals()
        
        # EvilAGI atakuje co 1.5 sekundy
        self.spawn_timer = self.set_interval(1.5, self.spawn_evil_agi)
        
        # Sprawdzanie zniszczeń
        self.explode_timer = self.set_interval(0.5, self.check_system_failure)
        
        self.update_header()

    def update_agent_visuals(self):
        # Reset visuali agenta
        for btn in self.buttons:
            if "agent-here" in btn.classes:
                btn.remove_class("agent-here")
                # Przywróć nazwę miasta bez ikonki
                city_name = self.CITIES[self.buttons.index(btn)]
                if "evil-agi" in btn.classes:
                    btn.label = f"☠ {city_name}"
                elif "secure" in btn.classes:
                    btn.label = f"🛡 {city_name}"
                else:
                    btn.label = city_name

        # Ustaw nowego agenta
        current_btn = self.buttons[self.agent_pos]
        current_btn.add_class("agent-here")
        # Łysy z brodą - ASCII art icon
        current_btn.label = f"[🧔] {self.CITIES[self.agent_pos]}"

    def spawn_evil_agi(self):
        target = random.choice(self.buttons)
        # Nie atakuj tam gdzie stoi agent, ani tam gdzie już jest zniszczone/zainfekowane
        if target != self.buttons[self.agent_pos] and "evil-agi" not in target.classes and "destroyed" not in target.classes:
            target.add_class("evil-agi")
            target.remove_class("secure")
            city_name = self.CITIES[self.buttons.index(target)]
            target.label = f"☠ {city_name}"
            target.infection_start = datetime.now().timestamp()

    def check_system_failure(self):
        now = datetime.now().timestamp()
        for node in self.buttons:
            if "evil-agi" in node.classes and hasattr(node, "infection_start"):
                # Jeśli infekcja trwa dłużej niż 5 sekund -> System Lost
                if now - node.infection_start > 5.0:
                    node.remove_class("evil-agi")
                    node.add_class("destroyed")
                    node.label = "--- LOST ---"
                    self.cities_lost += 1
                    self.update_header()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        target_btn = event.button
        target_index = int(target_btn.id.split("-")[1])
        
        # Jeśli miasto zniszczone - brak ruchu
        if "destroyed" in target_btn.classes:
            return

        # LOGIKA GRY:
        
        # 1. Jeśli klikasz tam gdzie jesteś -> STAKING (Mnożenie Tokenów)
        if target_index == self.agent_pos:
            if "secure" in target_btn.classes:
                growth = max(1, int(self.tokens * 0.1)) # 10% zysku
                self.tokens += growth
                self.notify(f"STAKING: +{growth} Tokens")
            else:
                self.notify("Zabezpiecz teren przed stakingiem!")
        
        # 2. Jeśli klikasz inne miasto -> TELEPORTACJA
        else:
            self.agent_pos = target_index
            self.update_agent_visuals()
            
            # Jeśli wpadłeś na EvilAGI -> WALKA (Koszt Tokenów)
            if "evil-agi" in target_btn.classes:
                if self.tokens >= 10:
                    self.tokens -= 10
                    target_btn.remove_class("evil-agi")
                    target_btn.add_class("secure")
                    self.notify("EvilAGI zneutralizowane! (-10 Tokens)")
                else:
                    self.notify("Brak Tokenów na walkę! Uciekaj i mnóż!")
            
            # Jeśli wpadłeś na czyste/zabezpieczone -> Nic (lub mały bonus)
            elif "secure" not in target_btn.classes:
                target_btn.add_class("secure") # Automatyczne zabezpieczenie przy odwiedzinach

        self.update_header()

    def update_header(self):
        status_color = "green" if self.tokens > 20 else "red"
        self.query_one("#game-header").update(
            f"TOKENS: [{status_color}]{self.tokens}[/] | LOST NODES: {self.cities_lost}/5 | [ESC] Powrót"
        )

# --- GŁÓWNA APLIKACJA ---
class AgentZeroCLI(App):
    CSS = CSS
    TITLE = "Agent Zero CLI"
    SUB_TITLE = f"Mode: {CONFIG['security']['mode'].upper()} | F1: MISSION POLAND"
    
    BINDINGS = [
        ("f1", "push_game", "Graj w Agent ZUSA"),
        ("ctrl+c", "quit", "Wyjście")
    ]

    def __init__(self):
        super().__init__()
        self.backend = MockAgentBackend()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(id="chat-container")
        yield Input(placeholder="Wpisz polecenie...", id="input-area")
        yield Footer()

    def on_mount(self) -> None:
        chat = self.query_one("#chat-container")
        welcome_msg = f"[bold green]● System Online.[/]\\nZaładowano: [i]{CONFIG['security']['mode']}[/i]."
        chat.mount(Static(welcome_msg, classes="agent-msg"))

    def action_push_game(self) -> None:
        self.push_screen(RetroGameScreen())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value
        if not user_input: return
        event.input.value = ""
        chat = self.query_one("#chat-container")
        await chat.mount(Markdown(f"**TY:** {user_input}", classes="user-msg"))
        chat.scroll_end()
        self.run_worker(self.process_agent_interaction(user_input))

    async def process_agent_interaction(self, user_text: str):
        chat = self.query_one("#chat-container")
        async for event in self.backend.send_prompt(user_text):
            if event['type'] == 'thought':
                await chat.mount(Label(f"💭 {event['content']}", classes="agent-thought"))
                chat.scroll_end()
            elif event['type'] == 'tool_request':
                decision = await self.push_screen_wait(
                    ToolApprovalScreen(event['tool_name'], event['command'], event['reason'], self.backend)
                )
                if decision == "approved":
                    await chat.mount(Static(f"✅ ZATWIERDZONO: {event['command']}", classes="system-msg"))
                    async for exec_event in self.backend.execute_tool(event['command']):
                        if exec_event['type'] == 'tool_output':
                             await chat.mount(Static(exec_event['content'], classes="tool-output"))
                        elif exec_event['type'] == 'final_response':
                             await chat.mount(Markdown(f"**AGENT:** {exec_event['content']}", classes="agent-msg"))
                else:
                    await chat.mount(Static("❌ ODRZUCONO.", classes="system-msg"))
            chat.scroll_end()

if __name__ == "__main__":
    app = AgentZeroCLI()
    app.run()
''',

    "README.md": """# Agent Zero CLI (z Mini-Grą)

Profesjonalny TUI z funkcją "Break Mode" inspirowaną klasykiem Agent USA.

## 🌟 Główne Funkcje
1.  **Architektura Client-Server:** Oddzielenie interfejsu od logiki agenta.
2.  **Interceptor Bezpieczeństwa:** Ochrona przed `rm -rf`.
3.  **Funkcja Explain:** Analiza ryzyka przez AI.
4.  **Tryb Rozrywki (F1):** Gra **"Agent ZUSA: TheOnes"** (Polish Mission).
    * Wciel się w Agenta0 (Łysy z brodą `[🧔]`).
    * Teleportuj się między polskimi miastami.
    * Zwalczaj wirusa EvilAGI (kosztuje Tokeny).
    * Mnóż Tokeny (Staking) zostając w bezpiecznych miastach.

## 🚀 Uruchomienie
1.  `python install.py`
2.  `source venv/bin/activate` (jeśli używasz venv)
3.  `pip install -r requirements.txt`
4.  `python main.py`

Użyj klawisza **F1**, aby uruchomić grę w dowolnym momencie.
"""
}

def install():
    print("🚀 Aktualizuję Agent Zero CLI (Bugfix Update)...")
    for filename, content in files.items():
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content.strip())
            print(f"✅ Zaktualizowano: {filename}")
        except Exception as e:
            print(f"❌ Błąd: {e}")
    
    print("\n🎉 Gotowe! Uruchom 'python main.py' i wciśnij F1.")

if __name__ == "__main__":
    install()