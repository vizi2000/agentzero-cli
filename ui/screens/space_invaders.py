"""Full Space Invaders game implementation for AgentZeroCLI."""

import random

from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Static


class SpaceInvadersScreen(Screen):
    """Classic Space Invaders game with keyboard controls."""

    BINDINGS = [
        Binding("escape", "quit_game", "Quit"),
        Binding("left", "move_left", "Left", show=False),
        Binding("right", "move_right", "Right", show=False),
        Binding("space", "shoot", "Fire", show=False),
        Binding("p", "pause", "Pause"),
    ]

    DEFAULT_CSS = """
    SpaceInvadersScreen {
        background: #000;
        align: center middle;
    }
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
    """

    # Game state
    score: reactive[int] = reactive(0)
    lives: reactive[int] = reactive(3)
    level: reactive[int] = reactive(1)
    paused: reactive[bool] = reactive(False)
    game_over: reactive[bool] = reactive(False)

    # Board dimensions
    BOARD_WIDTH = 60
    BOARD_HEIGHT = 24
    PLAYER_Y = 22

    # Sprites
    PLAYER = "^A^"
    INVADER_TYPES = ["=W=", "<M>", "{O}"]
    INVADER_POINTS = [30, 20, 10]
    BULLET = "|"
    ENEMY_BULLET = "!"
    BARRIER = "#"

    def __init__(self):
        super().__init__()
        self.player_x = self.BOARD_WIDTH // 2
        self.player_bullets = []
        self.enemy_bullets = []
        self.invaders = []
        self.barriers = []
        self.invader_direction = 1
        self.invader_move_counter = 0
        self.invader_speed = 4
        self._game_timer = None
        self._shoot_cooldown = 0

    def compose(self):
        yield Static("", id="game-header")
        yield Static("", id="game-board")
        yield Static("Arrows: Move | Space: Fire | P: Pause | ESC: Quit", id="game-footer")

    def on_mount(self) -> None:
        self._init_game()
        self._game_timer = self.set_interval(1 / 20, self._game_tick)
        self._render()

    def _init_game(self) -> None:
        """Initialize game state for new game or level."""
        self.player_x = self.BOARD_WIDTH // 2
        self.player_bullets = []
        self.enemy_bullets = []
        self._spawn_invaders()
        self._spawn_barriers()

    def _spawn_invaders(self) -> None:
        """Create invader formation."""
        self.invaders = []
        rows = 5
        cols = 11
        start_x = 4
        start_y = 2

        for row in range(rows):
            inv_type = min(row // 2, 2)
            for col in range(cols):
                self.invaders.append(
                    {
                        "x": start_x + col * 4,
                        "y": start_y + row * 2,
                        "type": inv_type,
                        "alive": True,
                    }
                )

    def _spawn_barriers(self) -> None:
        """Create protective barriers."""
        self.barriers = []
        barrier_y = self.PLAYER_Y - 4

        for i in range(4):
            bx = 6 + i * 14
            for dx in range(5):
                for dy in range(3):
                    self.barriers.append(
                        {
                            "x": bx + dx,
                            "y": barrier_y + dy,
                            "hp": 4,
                        }
                    )

    def _game_tick(self) -> None:
        """Main game loop tick."""
        if self.paused or self.game_over:
            return

        self._move_bullets()
        self._move_invaders()
        self._enemy_shoot()
        self._check_collisions()
        self._check_win_lose()
        self._render()

        if self._shoot_cooldown > 0:
            self._shoot_cooldown -= 1

    def _move_bullets(self) -> None:
        """Update bullet positions."""
        self.player_bullets = [
            {"x": b["x"], "y": b["y"] - 1} for b in self.player_bullets if b["y"] > 0
        ]
        self.enemy_bullets = [
            {"x": b["x"], "y": b["y"] + 1} for b in self.enemy_bullets if b["y"] < self.BOARD_HEIGHT
        ]

    def _move_invaders(self) -> None:
        """Move invader formation."""
        self.invader_move_counter += 1
        if self.invader_move_counter < self.invader_speed:
            return
        self.invader_move_counter = 0

        alive = [i for i in self.invaders if i["alive"]]
        if not alive:
            return

        min_x = min(i["x"] for i in alive)
        max_x = max(i["x"] for i in alive)

        hit_edge = (self.invader_direction > 0 and max_x >= self.BOARD_WIDTH - 5) or (
            self.invader_direction < 0 and min_x <= 2
        )

        if hit_edge:
            self.invader_direction *= -1
            for inv in alive:
                inv["y"] += 1
            self.invader_speed = max(1, self.invader_speed - 1)
        else:
            for inv in alive:
                inv["x"] += self.invader_direction

    def _enemy_shoot(self) -> None:
        """Random enemy shooting."""
        alive = [i for i in self.invaders if i["alive"]]
        if not alive:
            return

        if random.random() < 0.03 and len(self.enemy_bullets) < 3:
            shooter = random.choice(alive)
            self.enemy_bullets.append(
                {
                    "x": shooter["x"] + 1,
                    "y": shooter["y"] + 1,
                }
            )

    def _check_collisions(self) -> None:
        """Check all collisions."""
        # Player bullets vs invaders
        for bullet in self.player_bullets[:]:
            for inv in self.invaders:
                if not inv["alive"]:
                    continue
                if abs(bullet["x"] - inv["x"]) <= 1 and abs(bullet["y"] - inv["y"]) <= 1:
                    inv["alive"] = False
                    if bullet in self.player_bullets:
                        self.player_bullets.remove(bullet)
                    self.score += self.INVADER_POINTS[inv["type"]]
                    break

        # Enemy bullets vs player
        for bullet in self.enemy_bullets[:]:
            if abs(bullet["x"] - self.player_x - 1) <= 1 and bullet["y"] >= self.PLAYER_Y:
                self.enemy_bullets.remove(bullet)
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True

        # Bullets vs barriers
        all_bullets = self.player_bullets[:] + self.enemy_bullets[:]
        for bullet in all_bullets:
            for barrier in self.barriers[:]:
                if abs(bullet["x"] - barrier["x"]) < 1 and abs(bullet["y"] - barrier["y"]) < 1:
                    barrier["hp"] -= 1
                    if barrier["hp"] <= 0:
                        self.barriers.remove(barrier)
                    if bullet in self.player_bullets:
                        self.player_bullets.remove(bullet)
                    elif bullet in self.enemy_bullets:
                        self.enemy_bullets.remove(bullet)
                    break

    def _check_win_lose(self) -> None:
        """Check win/lose conditions."""
        alive = [i for i in self.invaders if i["alive"]]

        # Win: all invaders destroyed
        if not alive:
            self.level += 1
            self.invader_speed = max(4, 6 - self.level)
            self._spawn_invaders()
            return

        # Lose: invaders reached bottom
        lowest_y = max(i["y"] for i in alive)
        if lowest_y >= self.PLAYER_Y - 2:
            self.game_over = True

    def _render(self) -> None:
        """Render game state to screen."""
        board = [[" " for _ in range(self.BOARD_WIDTH)] for _ in range(self.BOARD_HEIGHT)]

        # Draw invaders
        for inv in self.invaders:
            if not inv["alive"]:
                continue
            sprite = self.INVADER_TYPES[inv["type"]]
            x, y = int(inv["x"]), int(inv["y"])
            if 0 <= y < self.BOARD_HEIGHT:
                for i, c in enumerate(sprite):
                    if 0 <= x + i < self.BOARD_WIDTH:
                        board[y][x + i] = c

        # Draw barriers
        for barrier in self.barriers:
            x, y = barrier["x"], barrier["y"]
            if 0 <= y < self.BOARD_HEIGHT and 0 <= x < self.BOARD_WIDTH:
                board[y][x] = self.BARRIER

        # Draw player
        for i, c in enumerate(self.PLAYER):
            px = self.player_x + i
            if 0 <= px < self.BOARD_WIDTH:
                board[self.PLAYER_Y][px] = c

        # Draw player bullets
        for bullet in self.player_bullets:
            x, y = int(bullet["x"]), int(bullet["y"])
            if 0 <= y < self.BOARD_HEIGHT and 0 <= x < self.BOARD_WIDTH:
                board[y][x] = self.BULLET

        # Draw enemy bullets
        for bullet in self.enemy_bullets:
            x, y = int(bullet["x"]), int(bullet["y"])
            if 0 <= y < self.BOARD_HEIGHT and 0 <= x < self.BOARD_WIDTH:
                board[y][x] = self.ENEMY_BULLET

        # Render to widget
        lines = ["".join(row) for row in board]
        self.query_one("#game-board", Static).update("\n".join(lines))

        # Update header
        lives_str = "+" * self.lives
        header = f"SCORE: {self.score:06d}  LEVEL: {self.level}  LIVES: {lives_str}"
        if self.paused:
            header += "  [PAUSED]"
        if self.game_over:
            header = f"GAME OVER - Final Score: {self.score}  Press ESC to exit"
        self.query_one("#game-header", Static).update(header)

    # Actions
    def action_move_left(self) -> None:
        if not self.paused and not self.game_over:
            self.player_x = max(0, self.player_x - 2)

    def action_move_right(self) -> None:
        if not self.paused and not self.game_over:
            self.player_x = min(self.BOARD_WIDTH - 3, self.player_x + 2)

    def action_shoot(self) -> None:
        if self.paused or self.game_over:
            return
        if self._shoot_cooldown > 0:
            return
        if len(self.player_bullets) >= 2:
            return

        self.player_bullets.append(
            {
                "x": self.player_x + 1,
                "y": self.PLAYER_Y - 1,
            }
        )
        self._shoot_cooldown = 8

    def action_pause(self) -> None:
        if not self.game_over:
            self.paused = not self.paused
            self._render()

    def action_quit_game(self) -> None:
        if self._game_timer:
            self._game_timer.stop()
        self.app.pop_screen()
