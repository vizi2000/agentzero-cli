"""Arcade widget for AgentZeroCLI - animated mini-games during waiting."""

import random

from textual.widgets import Static


class ArcadeWidget(Static):
    """Animated arcade widget showing Space Invaders or Pong during waiting."""

    def __init__(self, mode: str = "invaders", fps: int = 12, **kwargs):
        super().__init__("", **kwargs)
        self.mode = mode
        self.fps = fps
        self.active = False
        self._timer = None
        self._frame = 0
        self._rng = random.Random()
        self._stars = []
        self._board_width = 0
        self._board_height = 0
        self._invaders = set()
        self._invader_rows = 0
        self._invader_cols = 0
        self._invader_origin_x = 0
        self._invader_origin_y = 0
        self._invader_dir = 1
        self._invader_speed = 3
        self._player_x = 0
        self._bullet = None
        self._pong_ball = [0, 0]
        self._pong_dir = [1, 1]
        self._pong_left_y = 0
        self._pong_right_y = 0
        self._pong_paddle = 3

    def on_mount(self) -> None:
        self._sync_board()
        self._reset_state()
        self._render_idle()

    def on_resize(self, event) -> None:
        self._sync_board()
        self._reset_state()
        if self.active:
            self._render_frame()
        else:
            self._render_idle()

    def set_mode(self, mode: str) -> None:
        if mode not in ("invaders", "pong", "off"):
            mode = "invaders"
        self.mode = mode
        self._reset_state()
        if self.active:
            self._render_frame()
        elif self.mode == "off":
            self._render_off()
        else:
            self._render_idle()

    def start(self) -> None:
        if self.mode == "off":
            self.active = False
            self.set_class(True, "idle")
            self.set_class(False, "waiting")
            if self._timer:
                self._timer.stop()
                self._timer = None
            self._render_off()
            return
        self.active = True
        self.set_class(True, "waiting")
        self.set_class(False, "idle")
        if self._timer is None:
            self._timer = self.set_interval(1 / max(1, self.fps), self._tick)
        self._render_frame()

    def stop(self) -> None:
        self.active = False
        self.set_class(True, "idle")
        self.set_class(False, "waiting")
        if self._timer:
            self._timer.stop()
            self._timer = None
        if self.mode == "off":
            self._render_off()
        else:
            self._render_idle()

    def _sync_board(self) -> None:
        width = self.size.width or 28
        height = self.size.height or 10
        self._board_width = max(18, width)
        self._board_height = max(8, height)

    def _reset_state(self) -> None:
        self._frame = 0
        self._stars = []
        if self.mode == "pong":
            self._reset_pong()
        else:
            self._reset_invaders()

    def _reset_invaders(self) -> None:
        width = self._board_width
        self._invader_cols = max(4, min(9, (width - 6) // 3))
        self._invader_rows = 3
        self._invader_origin_x = 2
        self._invader_origin_y = 1
        self._invader_dir = 1
        self._invader_speed = 3
        self._invaders = {
            (row, col) for row in range(self._invader_rows) for col in range(self._invader_cols)
        }
        self._player_x = max(2, width // 2)
        self._bullet = None

    def _reset_pong(self) -> None:
        width, height = self._board_width, self._board_height
        self._pong_ball = [width // 2, height // 2]
        self._pong_dir = [1, 1]
        self._pong_paddle = max(2, height // 4)
        self._pong_left_y = max(1, height // 2 - self._pong_paddle // 2)
        self._pong_right_y = self._pong_left_y

    def _tick(self) -> None:
        if not self.active:
            return
        self._frame += 1
        self._advance_stars()
        if self.mode == "pong":
            self._tick_pong()
        else:
            self._tick_invaders()

    def _advance_stars(self) -> None:
        width, height = self._board_width, self._board_height
        updated = [(x, y + 1) for x, y in self._stars if y + 1 < height]
        if self._rng.random() < 0.35:
            updated.append((self._rng.randrange(1, max(2, width - 1)), 0))
        self._stars = updated

    def _invader_positions(self) -> dict:
        positions = {}
        for row, col in self._invaders:
            x = self._invader_origin_x + col * 3
            y = self._invader_origin_y + row * 2
            positions[(x, y)] = (row, col)
        return positions

    def _tick_invaders(self) -> None:
        width, height = self._board_width, self._board_height
        if not self._invaders:
            self._reset_invaders()
        if self._frame % self._invader_speed == 0:
            next_origin = self._invader_origin_x + self._invader_dir
            min_x = next_origin
            max_x = next_origin + (self._invader_cols - 1) * 3
            if min_x <= 1 or max_x >= width - 2:
                self._invader_dir *= -1
                self._invader_origin_y += 1
            else:
                self._invader_origin_x = next_origin
        if self._invader_origin_y + (self._invader_rows - 1) * 2 >= height - 3:
            self._reset_invaders()

        positions = self._invader_positions()
        target_x = None
        if positions:
            target_x = min(positions.keys(), key=lambda pos: abs(pos[0] - self._player_x))[0]
            if target_x > self._player_x:
                self._player_x += 1
            elif target_x < self._player_x:
                self._player_x -= 1

        player_y = max(1, height - 2)
        self._player_x = max(1, min(width - 2, self._player_x))

        if self._bullet:
            self._bullet[1] -= 1
            if self._bullet[1] <= 0:
                self._bullet = None
            else:
                hit_key = (self._bullet[0], self._bullet[1])
                hit = positions.pop(hit_key, None)
                if hit:
                    self._invaders.discard(hit)
                    self._bullet = None

        if (
            self._bullet is None
            and target_x is not None
            and self._frame % 6 == 0
            and abs(target_x - self._player_x) <= 1
        ):
            self._bullet = [self._player_x, player_y - 1]

        grid = self._blank_grid()
        for x, y in self._stars:
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "."
        for (x, y), _ in positions.items():
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "W"
        if self._bullet:
            x, y = self._bullet
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "|"
        if 0 <= player_y < height:
            grid[player_y][self._player_x] = "A"
        self._render_grid(grid)

    def _tick_pong(self) -> None:
        width, height = self._board_width, self._board_height
        ball_x, ball_y = self._pong_ball
        dir_x, dir_y = self._pong_dir

        target_left = ball_y - self._pong_paddle // 2
        if target_left > self._pong_left_y:
            self._pong_left_y += 1
        elif target_left < self._pong_left_y:
            self._pong_left_y -= 1

        target_right = ball_y - self._pong_paddle // 2
        if target_right > self._pong_right_y:
            self._pong_right_y += 1
        elif target_right < self._pong_right_y:
            self._pong_right_y -= 1

        max_paddle_y = max(0, height - self._pong_paddle - 1)
        self._pong_left_y = max(0, min(max_paddle_y, self._pong_left_y))
        self._pong_right_y = max(0, min(max_paddle_y, self._pong_right_y))

        ball_x += dir_x
        ball_y += dir_y

        if ball_y <= 0 or ball_y >= height - 1:
            dir_y *= -1
            ball_y = max(0, min(height - 1, ball_y))

        if ball_x <= 1:
            if self._pong_left_y <= ball_y <= self._pong_left_y + self._pong_paddle - 1:
                dir_x = 1
            else:
                self._reset_pong()
                ball_x, ball_y = self._pong_ball
                dir_x, dir_y = self._pong_dir
        elif ball_x >= width - 2:
            if self._pong_right_y <= ball_y <= self._pong_right_y + self._pong_paddle - 1:
                dir_x = -1
            else:
                self._reset_pong()
                ball_x, ball_y = self._pong_ball
                dir_x, dir_y = self._pong_dir

        self._pong_ball = [ball_x, ball_y]
        self._pong_dir = [dir_x, dir_y]

        grid = self._blank_grid()
        for x, y in self._stars:
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "."
        for offset in range(self._pong_paddle):
            left_y = self._pong_left_y + offset
            right_y = self._pong_right_y + offset
            if 0 <= left_y < height:
                grid[left_y][1] = "|"
            if 0 <= right_y < height:
                grid[right_y][width - 2] = "|"
        if 0 <= ball_x < width and 0 <= ball_y < height:
            grid[ball_y][ball_x] = "o"
        self._render_grid(grid)

    def _blank_grid(self) -> list:
        return [[" " for _ in range(self._board_width)] for _ in range(self._board_height)]

    def _render_grid(self, grid: list) -> None:
        lines = ["".join(row) for row in grid]
        self.update("\n".join(lines))

    def _render_idle(self) -> None:
        width, height = self._board_width, self._board_height
        label = "SYSTEM READY"
        sub = "SEND A COMMAND TO START"
        lines = []
        for row in range(height):
            if row == height // 2 - 1:
                lines.append(label.center(width))
            elif row == height // 2:
                lines.append(sub.center(width))
            else:
                lines.append(" " * width)
        self.update("\n".join(lines))

    def _render_off(self) -> None:
        width, height = self._board_width, self._board_height
        label = "ARCADE OFF"
        lines = []
        for row in range(height):
            if row == height // 2:
                lines.append(label.center(width))
            else:
                lines.append(" " * width)
        self.update("\n".join(lines))

    def _render_frame(self) -> None:
        if self.mode == "pong":
            self._tick_pong()
        else:
            self._tick_invaders()
