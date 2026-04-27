# gui.py - Pygame GUI for SmoL Chess

import os
import math
import random

import pygame

from board import get_legal_moves
from pieces import King, Knight, Pawn, Queen

BG = (18, 18, 24)
LIGHT_SQ = (240, 217, 181)
DARK_SQ = (181, 136, 99)
LAST_MOVE = (205, 210, 56, 140)
CHECK_RED = (220, 50, 50, 180)
TEXT_COLOR = (230, 230, 230)
PANEL_BG = (26, 27, 34)
BORDER = (88, 85, 98)
ACCENT_GOLD = (239, 200, 112)
ACCENT_GREEN = (119, 181, 101)
CARD_BG = (40, 42, 52)
CARD_BG_ALT = (48, 51, 62)
CARD_HOVER = (63, 68, 82)
BUTTON_BG = (204, 165, 80)
BUTTON_HOVER = (226, 187, 101)
SHADOW = (0, 0, 0, 90)

SQ_SIZE = 90
BOARD_PX = SQ_SIZE * 6
PANEL_W = 320
WIN_W = BOARD_PX + PANEL_W
WIN_H = BOARD_PX
TITLE_BAR_H = 0
WINDOW_H = WIN_H
FPS = 60
PIECE_SCALE = 0.86
ANIM_MS = 160

PIECE_FILES = {
    ("W", King): "wk.png",
    ("W", Queen): "wq.png",
    ("W", Knight): "wn.png",
    ("W", Pawn): "wp.png",
    ("B", King): "bk.png",
    ("B", Queen): "bq.png",
    ("B", Knight): "bn.png",
    ("B", Pawn): "bp.png",
}


class GUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.content_surface = pygame.Surface((WIN_W, WIN_H))
        self.window_title = "SmoL Chess"
        pygame.display.set_caption(self.window_title)
        self.clock = pygame.time.Clock()

        self.font_label = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 14)
        self.font_title = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 20, bold=True)
        self.font_log = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 13)
        self.font_big = self._pick_font(["dejavusans", "liberationsans", "consolas"], 36, bold=True)
        self.font_menu_title = self._pick_font(["dejavusans", "liberationsans", "consolas"], 40, bold=True)
        self.font_menu_subtitle = self._pick_font(["dejavusans", "liberationsans", "consolas"], 18)
        self.font_menu_card = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 16, bold=True)
        self.font_menu_hint = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 12)

        self.piece_sprites = {}
        self.use_sprite_pieces = self._load_piece_sprites()
        self.board_surface = self._build_board_surface()
        self.menu_wood_surface = self._load_menu_wood_surface()
        self.panel_wood_surface = pygame.transform.smoothscale(self.menu_wood_surface, (PANEL_W, WIN_H))
        self.title_wood_surface = None
        self.panel_text_color = (246, 238, 220)
        self.panel_muted_color = (218, 209, 190)

        self.anim_active = False
        self.anim_sprite = None
        self.anim_from_px = (0, 0)
        self.anim_to_px = (0, 0)
        self.anim_to_sq = None
        self.anim_start_ms = 0

        self.move_log = []
        self.log_scroll_offset = 0
        self.log_scroll_rect = pygame.Rect(0, 0, 0, 0)
        self.last_move = None
        self.check_king = None
        self.match_players = {
            "W": {"name": "White", "type": "---"},
            "B": {"name": "Black", "type": "---"},
        }

    def show_start_menu(self, option_defs, default_white="minimax", default_black="mcts", default_ai_time=4.5):
        selected = {"W": default_white, "B": default_black}
        max_ai_time = default_ai_time
        dragging_slider = False
        focus = "W"
        option_keys = list(option_defs.keys())
        self._set_window_title("SmoL Chess — Select Players")

        while True:
            mouse_pos = self._content_mouse_pos()
            layout = self._menu_layout(option_defs)

            for event in pygame.event.get():
                self._handle_log_scroll_event(event)
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        raise SystemExit
                    if event.key == pygame.K_TAB:
                        focus = "B" if focus == "W" else "W"
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        idx = option_keys.index(selected[focus])
                        selected[focus] = option_keys[(idx - 1) % len(option_keys)]
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        idx = option_keys.index(selected[focus])
                        selected[focus] = option_keys[(idx + 1) % len(option_keys)]
                    elif event.key == pygame.K_RETURN:
                        return {**selected, "max_ai_time": max_ai_time}
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    content_pos = self._content_event_pos(event)
                    if content_pos is None:
                        continue
                    if layout["time_slider_hit"].collidepoint(content_pos):
                        dragging_slider = True
                        max_ai_time = self._slider_time_from_x(content_pos[0], layout["time_slider_track"])
                        continue
                    if layout["start_button"].collidepoint(content_pos):
                        return {**selected, "max_ai_time": max_ai_time}
                    for side in ("W", "B"):
                        for key, rect in layout["cards"][side].items():
                            if rect.collidepoint(content_pos):
                                selected[side] = key
                                focus = side
                if event.type == pygame.MOUSEMOTION and dragging_slider:
                    content_pos = self._content_event_pos(event)
                    if content_pos is not None:
                        max_ai_time = self._slider_time_from_x(content_pos[0], layout["time_slider_track"])
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging_slider = False

            self._draw_content(lambda: self._draw_menu(option_defs, selected, focus, layout, mouse_pos, max_ai_time))
            pygame.display.flip()
            self.clock.tick(FPS)

    def set_match_players(self, white_player, black_player, white_type, black_type):
        self.match_players = {
            "W": {"name": white_player.name, "type": white_type},
            "B": {"name": black_player.name, "type": black_type},
        }
        self._set_window_title(f"SmoL Chess — {white_player.name} vs {black_player.name}")

    def _set_window_title(self, title):
        self.window_title = title
        pygame.display.set_caption(title)

    def _draw_content(self, draw_func):
        window_surface = self.screen
        self.screen = self.content_surface
        try:
            draw_func()
        finally:
            self.screen = window_surface
        self.screen.blit(self.content_surface, (0, TITLE_BAR_H))

    def _content_mouse_pos(self):
        x, y = pygame.mouse.get_pos()
        y -= TITLE_BAR_H
        if y < 0 or y >= WIN_H:
            return (-1, -1)
        return (x, y)

    def _content_event_pos(self, event):
        if not hasattr(event, "pos"):
            return None
        x, y = event.pos
        y -= TITLE_BAR_H
        if y < 0 or y >= WIN_H:
            return None
        return (x, y)

    def _title_button_rects(self):
        return {}

    def _handle_window_chrome_event(self, event):
        return False

    def _handle_log_scroll_event(self, event):
        if event.type not in (pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN):
            return False

        mouse_pos = self._content_mouse_pos()
        if not self.log_scroll_rect.collidepoint(mouse_pos):
            return False

        max_offset = max(0, len(self.move_log) - self._visible_log_line_count())
        if event.type == pygame.MOUSEWHEEL:
            self.log_scroll_offset = max(0, min(max_offset, self.log_scroll_offset - event.y))
            return True

        if event.button == 4:
            self.log_scroll_offset = max(0, self.log_scroll_offset - 1)
            return True
        if event.button == 5:
            self.log_scroll_offset = min(max_offset, self.log_scroll_offset + 1)
            return True

        return False

    def _visible_log_line_count(self):
        if self.log_scroll_rect.height <= 0:
            return 1
        return max(1, self.log_scroll_rect.height // 16)

    def _draw_title_bar(self):
        return
        self.screen.blit(self.title_wood_surface, (0, 0))
        tint = pygame.Surface((WIN_W, TITLE_BAR_H), pygame.SRCALPHA)
        tint.fill((22, 12, 6, 112))
        self.screen.blit(tint, (0, 0))
        pygame.draw.line(self.screen, (45, 25, 13), (0, TITLE_BAR_H - 2), (WIN_W, TITLE_BAR_H - 2), 2)
        pygame.draw.line(self.screen, (146, 94, 47), (0, TITLE_BAR_H - 1), (WIN_W, TITLE_BAR_H - 1), 1)

        icon_sprite = self._scaled_sprite("W", King, 22)
        if icon_sprite is not None:
            self.screen.blit(icon_sprite, icon_sprite.get_rect(center=(25, TITLE_BAR_H // 2)))

        title = self.font_label.render(self.window_title, True, (250, 239, 217))
        self.screen.blit(title, title.get_rect(center=(WIN_W // 2, TITLE_BAR_H // 2)))

        buttons = self._title_button_rects()
        button_specs = [
            ("minimize", (248, 177, 37)),
            ("spacer", (108, 101, 92)),
            ("close", (232, 84, 69)),
        ]
        mouse_pos = pygame.mouse.get_pos()
        for key, color in button_specs:
            rect = buttons[key]
            center = rect.center
            hover = rect.collidepoint(mouse_pos)
            radius = 7 if not hover else 8
            pygame.draw.circle(self.screen, (30, 18, 10), center, radius + 2)
            pygame.draw.circle(self.screen, color, center, radius)

    def _draw_window_frame(self):
        return
        radius = 16
        border_rect = pygame.Rect(1, 1, WIN_W - 2, WINDOW_H - 2)
        pygame.draw.rect(self.screen, (82, 53, 29), border_rect, width=2, border_radius=radius)
        pygame.draw.rect(self.screen, (168, 104, 48), border_rect.inflate(-3, -3), width=1, border_radius=radius - 2)

    def update(
        self,
        board,
        status_text,
        move_number,
        last_move=None,
        check_king=None,
        current_turn=None,
        last_move_time=None,
        selected_square=None,
        legal_targets=None,
    ):
        if last_move and last_move != self.last_move:
            self._start_move_animation(board, last_move)

        self.last_move = last_move
        self.check_king = check_king
        for event in pygame.event.get():
            self._handle_log_scroll_event(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        self._render_game(
            board,
            status_text,
            move_number,
            current_turn,
            last_move_time,
            selected_square=selected_square,
            legal_targets=legal_targets,
        )

    def _render_game(
        self,
        board,
        status_text,
        move_number,
        current_turn,
        last_move_time,
        selected_square=None,
        legal_targets=None,
    ):
        self._draw_content(
            lambda: self._render_game_content(
                board,
                status_text,
                move_number,
                current_turn,
                last_move_time,
                selected_square,
                legal_targets or [],
            )
        )
        pygame.display.flip()
        self.clock.tick(FPS)

    def _render_game_content(
        self,
        board,
        status_text,
        move_number,
        current_turn,
        last_move_time,
        selected_square=None,
        legal_targets=None,
    ):
        self.screen.fill(BG)
        self._draw_board()
        self._draw_highlights(selected_square, legal_targets or [])
        self._draw_pieces(board)
        self._draw_coords()
        self._draw_panel(status_text, move_number, current_turn, last_move_time)

    def get_human_move(
        self,
        board,
        color,
        status_text,
        move_number,
        last_move=None,
        check_king=None,
        current_turn=None,
        last_move_time=None,
    ):
        legal_moves = get_legal_moves(board, color)
        selected_piece = None
        selected_square = None
        legal_targets = []

        self.last_move = last_move
        self.check_king = check_king

        while True:
            for event in pygame.event.get():
                if self._handle_log_scroll_event(event):
                    continue
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit
                if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                    continue

                content_pos = self._content_event_pos(event)
                if content_pos is None:
                    continue

                row, col = self._board_square_from_pos(content_pos)
                if row is None:
                    selected_piece = None
                    selected_square = None
                    legal_targets = []
                    continue

                clicked_piece = board[row][col]
                target = (row, col)
                if selected_piece is not None and target in legal_targets:
                    return selected_piece, target

                if clicked_piece is not None and clicked_piece.color == color:
                    piece_moves = [
                        dest
                        for legal_piece, dest in legal_moves
                        if legal_piece is clicked_piece
                    ]
                    if piece_moves:
                        selected_piece = clicked_piece
                        selected_square = target
                        legal_targets = piece_moves
                    continue

                selected_piece = None
                selected_square = None
                legal_targets = []

            self._render_game(
                board,
                status_text,
                move_number,
                current_turn,
                last_move_time,
                selected_square=selected_square,
                legal_targets=legal_targets,
            )

    def add_log(self, text):
        self.move_log.append(text)
        self.log_scroll_offset = 0

    def show_winner(self, message, board):
        self.update(board, message, 0, current_turn=None, last_move_time=None)
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        text = self.font_big.render(message, True, ACCENT_GOLD)
        rect = text.get_rect(center=(WIN_W // 2, WIN_H // 2))
        shadow = self.font_big.render(message, True, (0, 0, 0))
        self.screen.blit(shadow, rect.move(3, 3))
        self.screen.blit(text, rect)

        sub = self.font_title.render("Close window to exit", True, TEXT_COLOR)
        self.screen.blit(sub, sub.get_rect(center=(WIN_W // 2, WIN_H // 2 + 50)))

        pygame.display.flip()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
        pygame.quit()

    def _pick_font(self, names, size, bold=False):
        for name in names:
            path = pygame.font.match_font(name)
            if path:
                font = pygame.font.Font(path, size)
                font.set_bold(bold)
                return font
        return pygame.font.SysFont(None, size, bold=bold)

    def _build_board_surface(self):
        board_surf = pygame.Surface((BOARD_PX, BOARD_PX))
        rng = random.Random(66)

        for row in range(6):
            for col in range(6):
                rect = pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)
                base = LIGHT_SQ if (row + col) % 2 == 0 else DARK_SQ
                board_surf.fill(base, rect)

                for _ in range(10):
                    y = rng.randint(rect.top + 4, rect.bottom - 4)
                    alpha = rng.randint(10, 24)
                    tint = (255, 255, 255, alpha) if (row + col) % 2 == 0 else (0, 0, 0, alpha)
                    grain = pygame.Surface((SQ_SIZE - 8, 1), pygame.SRCALPHA)
                    grain.fill(tint)
                    board_surf.blit(grain, (rect.left + 4, y))

        return board_surf

    def _load_menu_wood_surface(self):
        texture_path = os.path.join(os.path.dirname(__file__), "assets", "ui", "menu_wood.png")
        if os.path.exists(texture_path):
            try:
                texture = pygame.image.load(texture_path).convert()
                return pygame.transform.smoothscale(texture, (WIN_W, WIN_H))
            except pygame.error:
                pass
        return self._build_menu_wood_surface(WIN_W, WIN_H)

    def _build_menu_wood_surface(self, width, height):
        surf = pygame.Surface((width, height))
        rng = random.Random(2026)

        for y in range(height):
            wave = math.sin(y * 0.045) * 9 + math.sin(y * 0.013) * 14
            base = 72 + int(wave)
            pygame.draw.line(surf, (base, 47 + base // 8, 27), (0, y), (width, y))

        plank_w = 92
        for x in range(0, width + plank_w, plank_w):
            seam = (35, 22, 14)
            pygame.draw.line(surf, seam, (x, 0), (x, height), 3)
            pygame.draw.line(surf, (108, 72, 42), (x + 3, 0), (x + 3, height), 1)

            for _ in range(34):
                y = rng.randrange(0, height)
                line_len = rng.randrange(28, plank_w - 8)
                x0 = x + rng.randrange(8, 28)
                tone = rng.randrange(72, 130)
                color = (tone, max(38, tone - 34), max(20, tone - 64))
                pygame.draw.line(surf, color, (x0, y), (min(width, x0 + line_len), y), 1)

            for _ in range(3):
                knot_x = x + rng.randrange(20, max(21, plank_w - 20))
                knot_y = rng.randrange(38, height - 38)
                pygame.draw.ellipse(surf, (58, 34, 19), (knot_x - 18, knot_y - 8, 36, 16), 2)
                pygame.draw.ellipse(surf, (105, 64, 32), (knot_x - 10, knot_y - 4, 20, 8), 1)

        vignette = pygame.Surface((width, height), pygame.SRCALPHA)
        for i in range(46):
            alpha = max(0, 75 - i * 2)
            pygame.draw.rect(vignette, (0, 0, 0, alpha), pygame.Rect(i, i, width - i * 2, height - i * 2), width=1)
        surf.blit(vignette, (0, 0))
        return surf

    def _build_horizontal_wood_surface(self, width, height):
        surf = pygame.Surface((width, height))
        rng = random.Random(909)

        for y in range(height):
            grain = math.sin(y * 0.7) * 11 + math.sin(y * 0.23) * 7
            tone = 96 + int(grain)
            pygame.draw.line(surf, (tone, max(45, tone - 38), max(22, tone - 68)), (0, y), (width, y))

        for _ in range(90):
            y = rng.randrange(3, max(4, height - 3))
            x0 = rng.randrange(0, width)
            length = rng.randrange(width // 8, width // 2)
            tone = rng.randrange(78, 134)
            pygame.draw.line(
                surf,
                (tone, max(40, tone - 39), max(18, tone - 72)),
                (x0, y),
                (min(width, x0 + length), y),
                1,
            )

        pygame.draw.line(surf, (46, 24, 11), (0, 0), (width, 0), 2)
        pygame.draw.line(surf, (53, 27, 12), (0, height - 1), (width, height - 1), 2)
        pygame.draw.line(surf, (151, 94, 43), (0, 2), (width, 2), 1)
        return surf

    def _load_piece_sprites(self):
        pieces_dir = os.path.join(os.path.dirname(__file__), "assets", "pieces")
        target_size = int(SQ_SIZE * PIECE_SCALE)

        for key, filename in PIECE_FILES.items():
            path = os.path.join(pieces_dir, filename)
            if not os.path.exists(path):
                self.piece_sprites.clear()
                return False
            try:
                image = pygame.image.load(path).convert_alpha()
            except pygame.error:
                self.piece_sprites.clear()
                return False
            self.piece_sprites[key] = pygame.transform.smoothscale(image, (target_size, target_size))

        return True

    def _scaled_sprite(self, color, piece_type, size):
        sprite = self.piece_sprites.get((color, piece_type))
        if sprite is None:
            return None
        return pygame.transform.smoothscale(sprite, (size, size))

    def _start_move_animation(self, board, last_move):
        if not self.use_sprite_pieces:
            self.anim_active = False
            return

        (r0, c0), (r1, c1) = last_move
        piece = board[r1][c1]
        if piece is None:
            self.anim_active = False
            return

        sprite = self.piece_sprites.get((piece.color, type(piece)))
        if sprite is None:
            self.anim_active = False
            return

        self.anim_active = True
        self.anim_sprite = sprite
        self.anim_from_px = (c0 * SQ_SIZE + SQ_SIZE // 2, r0 * SQ_SIZE + SQ_SIZE // 2)
        self.anim_to_px = (c1 * SQ_SIZE + SQ_SIZE // 2, r1 * SQ_SIZE + SQ_SIZE // 2)
        self.anim_to_sq = (r1, c1)
        self.anim_start_ms = pygame.time.get_ticks()

    def _draw_piece_sprite(self, sprite, center_x, center_y):
        rect = sprite.get_rect(center=(center_x, center_y))
        self.screen.blit(sprite, rect)

    def _sq_rect(self, row, col):
        return pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)

    def _board_square_from_pos(self, pos):
        x, y = pos
        if not (0 <= x < BOARD_PX and 0 <= y < BOARD_PX):
            return None, None
        return y // SQ_SIZE, x // SQ_SIZE

    def _draw_board(self):
        self.screen.blit(self.board_surface, (0, 0))

    def _draw_highlights(self, selected_square=None, legal_targets=None):
        surf = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)

        if self.last_move:
            (r0, c0), (r1, c1) = self.last_move
            surf.fill((0, 0, 0, 0))
            pygame.draw.circle(surf, (*LAST_MOVE[:3], 120), (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 2 - 8, 4)
            self.screen.blit(surf, self._sq_rect(r0, c0))

            surf.fill((0, 0, 0, 0))
            pygame.draw.circle(surf, (*LAST_MOVE[:3], 170), (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 5)
            self.screen.blit(surf, self._sq_rect(r1, c1))

        if self.check_king:
            surf.fill((0, 0, 0, 0))
            pygame.draw.rect(
                surf,
                (*CHECK_RED[:3], 180),
                pygame.Rect(5, 5, SQ_SIZE - 10, SQ_SIZE - 10),
                border_radius=10,
            )
            self.screen.blit(surf, self._sq_rect(*self.check_king))

        if selected_square:
            surf.fill((0, 0, 0, 0))
            pygame.draw.rect(
                surf,
                (255, 230, 120, 185),
                pygame.Rect(7, 7, SQ_SIZE - 14, SQ_SIZE - 14),
                width=4,
                border_radius=8,
            )
            self.screen.blit(surf, self._sq_rect(*selected_square))

        for row, col in legal_targets or []:
            surf.fill((0, 0, 0, 0))
            pygame.draw.circle(
                surf,
                (72, 180, 128, 150),
                (SQ_SIZE // 2, SQ_SIZE // 2),
                SQ_SIZE // 2 - 13,
                width=4,
            )
            pygame.draw.circle(
                surf,
                (245, 238, 196, 180),
                (SQ_SIZE // 2, SQ_SIZE // 2),
                SQ_SIZE // 8,
            )
            self.screen.blit(surf, self._sq_rect(row, col))

    def _draw_pieces(self, board):
        anim_overlay = None
        if self.anim_active:
            elapsed = pygame.time.get_ticks() - self.anim_start_ms
            if elapsed >= ANIM_MS:
                self.anim_active = False
            else:
                t = elapsed / ANIM_MS
                sx, sy = self.anim_from_px
                tx, ty = self.anim_to_px
                anim_overlay = (sx + (tx - sx) * t, sy + (ty - sy) * t)

        for row in range(6):
            for col in range(6):
                piece = board[row][col]
                if piece is None:
                    continue

                if anim_overlay and self.anim_to_sq == (row, col):
                    continue

                sprite = self.piece_sprites.get((piece.color, type(piece))) if self.use_sprite_pieces else None
                center_x = col * SQ_SIZE + SQ_SIZE // 2
                center_y = row * SQ_SIZE + SQ_SIZE // 2

                if sprite is not None:
                    self._draw_piece_sprite(sprite, center_x, center_y)
                    continue

        if anim_overlay and self.anim_sprite is not None:
            self._draw_piece_sprite(self.anim_sprite, anim_overlay[0], anim_overlay[1])

    def _draw_coords(self):
        cols = "abcdef"
        for i in range(6):
            col_label = self.font_label.render(cols[i], True, BORDER)
            self.screen.blit(col_label, (i * SQ_SIZE + SQ_SIZE - 14, BOARD_PX - 16))
            row_label = self.font_label.render(str(6 - i), True, BORDER)
            self.screen.blit(row_label, (4, i * SQ_SIZE + 4))

    def _draw_panel(self, status_text, move_number, current_turn, last_move_time):
        panel_rect = pygame.Rect(BOARD_PX, 0, PANEL_W, WIN_H)
        self.screen.blit(self.panel_wood_surface, panel_rect.topleft)
        panel_tint = pygame.Surface((PANEL_W, WIN_H), pygame.SRCALPHA)
        panel_tint.fill((12, 7, 4, 132))
        self.screen.blit(panel_tint, panel_rect.topleft)
        pygame.draw.line(self.screen, (64, 35, 18), (BOARD_PX, 0), (BOARD_PX, WIN_H), 3)
        pygame.draw.line(self.screen, (154, 102, 52), (BOARD_PX + 3, 0), (BOARD_PX + 3, WIN_H), 1)

        x = BOARD_PX + 14
        y = 16

        title = self.font_title.render("SmoL Chess", True, (255, 217, 132))
        self.screen.blit(title, (x, y))
        y += 34

        y = self._draw_player_card(x, y, "W", (215, 225, 215), King)
        y += 10
        y = self._draw_player_card(x, y, "B", (215, 215, 230), Queen)
        y += 14

        stats_rect = pygame.Rect(x, y, PANEL_W - 28, 124)
        self._draw_wood_card(stats_rect)
        status_font = self._fit_font_title(status_text, stats_rect.width - 24)
        status = status_font.render(status_text, True, (255, 205, 121))
        self.screen.blit(status, (stats_rect.x + 12, stats_rect.y + 10))

        move_time_text = "---" if last_move_time is None else f"{last_move_time:.2f}s"
        rows = [
            f"Move: {move_number}",
            f"Turn: {self._turn_label(current_turn)}",
            f"Last Move Time: {move_time_text}",
            f"White Player: {self.match_players['W']['type']}",
            f"Black Player: {self.match_players['B']['type']}",
        ]
        row_y = stats_rect.y + 44
        for row_text in rows:
            rendered = self.font_log.render(row_text, True, self.panel_text_color)
            self.screen.blit(rendered, (stats_rect.x + 12, row_y))
            row_y += 15
        y = stats_rect.bottom + 12

        log_rect = pygame.Rect(x, y, PANEL_W - 28, WIN_H - y - 14)
        self._draw_wood_card(log_rect)
        log_title = self.font_label.render("Move Log", True, (255, 217, 132))
        self.screen.blit(log_title, (log_rect.x + 16, log_rect.y + 10))

        self.log_scroll_rect = pygame.Rect(log_rect.x + 14, log_rect.y + 34, log_rect.width - 30, log_rect.height - 48)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.log_scroll_rect)

        visible_entries = list(reversed(self.move_log))
        max_offset = max(0, len(visible_entries) - self._visible_log_line_count())
        self.log_scroll_offset = max(0, min(max_offset, self.log_scroll_offset))
        line_y = self.log_scroll_rect.y
        for entry in visible_entries[self.log_scroll_offset:]:
            rendered = self.font_log.render(entry, True, self.panel_muted_color)
            self.screen.blit(rendered, (self.log_scroll_rect.x + 2, line_y))
            line_y += 16
            if line_y > self.log_scroll_rect.bottom - 2:
                break

        self.screen.set_clip(old_clip)
        if len(visible_entries) > self._visible_log_line_count():
            self._draw_log_scrollbar(self.log_scroll_rect, len(visible_entries))

    def _draw_player_card(self, x, y, side, accent_color, sprite_piece):
        rect = pygame.Rect(x, y, PANEL_W - 28, 72)
        self._draw_wood_card(rect)
        sprite = self._scaled_sprite(side, sprite_piece, 42)
        if sprite is not None:
            self.screen.blit(sprite, sprite.get_rect(center=(rect.x + 28, rect.y + 36)))

        side_label = "White" if side == "W" else "Black"
        text_area = pygame.Rect(rect.x + 56, rect.y + 10, rect.width - 70, rect.height - 18)
        line1 = self._fit_font_label(f"{side_label}: {self.match_players[side]['name']}", text_area.width)
        line2 = self._fit_font_label(f"Player Type: {self.match_players[side]['type']}", text_area.width)
        self.screen.blit(line1.render(f"{side_label}: {self.match_players[side]['name']}", True, accent_color), (text_area.x, text_area.y + 6))
        self.screen.blit(line2.render(f"Player Type: {self.match_players[side]['type']}", True, self.panel_text_color), (text_area.x, text_area.y + 28))
        return rect.bottom

    def _draw_log_scrollbar(self, rect, total_entries):
        visible = self._visible_log_line_count()
        if total_entries <= visible:
            return
        track = pygame.Rect(rect.right + 4, rect.y, 4, rect.height)
        pygame.draw.rect(self.screen, (42, 29, 18), track, border_radius=3)

        thumb_h = max(20, int(track.height * visible / total_entries))
        max_offset = max(1, total_entries - visible)
        thumb_y = track.y + int((track.height - thumb_h) * self.log_scroll_offset / max_offset)
        thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
        pygame.draw.rect(self.screen, (204, 154, 79), thumb, border_radius=3)

    def _fit_font_label(self, text, max_width):
        for size in (14, 13, 12, 11):
            font = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], size)
            if font.size(text)[0] <= max_width:
                return font
        return self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 11)

    def _fit_font_title(self, text, max_width):
        for size in (20, 19, 18, 17, 16, 15, 14):
            font = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], size, bold=True)
            if font.size(text)[0] <= max_width:
                return font
        return self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 14, bold=True)

    def _turn_label(self, current_turn):
        if current_turn == "W":
            return "White"
        if current_turn == "B":
            return "Black"
        return "---"

    def _draw_round_card(self, rect, color, border_color=BORDER):
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW, shadow.get_rect(), border_radius=16)
        self.screen.blit(shadow, (rect.x + 4, rect.y + 4))
        pygame.draw.rect(self.screen, color, rect, border_radius=16)
        pygame.draw.rect(self.screen, border_color, rect, width=1, border_radius=16)

    def _draw_wood_card(self, rect):
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW, shadow.get_rect(), border_radius=16)
        self.screen.blit(shadow, (rect.x + 4, rect.y + 4))

        card = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        card.blit(self.panel_wood_surface, (-max(0, rect.x - BOARD_PX), -rect.y))
        shade = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shade.fill((8, 4, 2, 182))
        card.blit(shade, (0, 0))

        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=16)
        card.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(card, rect.topleft)

        pygame.draw.rect(self.screen, (201, 139, 68), rect, width=1, border_radius=16)
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(self.screen, (18, 11, 7), inner, border_radius=14)
        pygame.draw.rect(self.screen, (96, 57, 28), inner, width=1, border_radius=14)

    def _menu_layout(self, option_defs):
        left_panel = pygame.Rect(48, 108, 340, 306)
        right_panel = pygame.Rect(WIN_W - 388, 108, 340, 306)
        slider_box = pygame.Rect(WIN_W // 2 - 205, 422, 410, 42)
        slider_track = pygame.Rect(slider_box.x + 42, slider_box.y + 24, slider_box.width - 84, 6)
        start_button = pygame.Rect(WIN_W // 2 - 100, 474, 200, 40)

        cards = {"W": {}, "B": {}}
        for idx, key in enumerate(option_defs.keys()):
            cards["W"][key] = pygame.Rect(left_panel.x + 18, left_panel.y + 68 + idx * 52, left_panel.width - 36, 42)
            cards["B"][key] = pygame.Rect(right_panel.x + 18, right_panel.y + 68 + idx * 52, right_panel.width - 36, 42)

        return {
            "panels": {"W": left_panel, "B": right_panel},
            "cards": cards,
            "start_button": start_button,
            "time_slider_box": slider_box,
            "time_slider_track": slider_track,
            "time_slider_hit": slider_track.inflate(18, 30),
        }

    def _slider_time_from_x(self, x, track_rect):
        min_time = 0.5
        max_time = 10.0
        ratio = (x - track_rect.left) / track_rect.width
        ratio = max(0.0, min(1.0, ratio))
        value = min_time + ratio * (max_time - min_time)
        return round(value * 2) / 2

    def _draw_time_slider(self, box_rect, track_rect, max_ai_time, mouse_pos):
        min_time = 0.5
        max_time = 10.0
        ratio = (max_ai_time - min_time) / (max_time - min_time)
        knob_x = int(track_rect.left + track_rect.width * ratio)
        knob = pygame.Rect(0, 0, 18, 18)
        knob.center = (knob_x, track_rect.centery)

        self._draw_round_card(box_rect, (31, 33, 42), border_color=(88, 91, 104))

        label = self.font_menu_hint.render(f"AI max think time: {max_ai_time:.1f}s", True, (232, 234, 240))
        self.screen.blit(label, label.get_rect(center=(WIN_W // 2, box_rect.y + 12)))

        pygame.draw.rect(self.screen, (38, 40, 49), track_rect.inflate(0, 4), border_radius=5)
        filled = pygame.Rect(track_rect.left, track_rect.y, knob_x - track_rect.left, track_rect.height)
        pygame.draw.rect(self.screen, ACCENT_GOLD, filled.inflate(0, 4), border_radius=5)
        pygame.draw.circle(self.screen, (24, 25, 31), knob.center, 12)
        pygame.draw.circle(self.screen, BUTTON_HOVER if knob.collidepoint(mouse_pos) else BUTTON_BG, knob.center, 9)

    def _draw_menu(self, option_defs, selected, focus, layout, mouse_pos, max_ai_time):
        self.screen.fill(BG)
        self.screen.blit(self.board_surface, (0, 0))
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 215))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.circle(self.screen, (64, 48, 28), (110, 90), 90)
        pygame.draw.circle(self.screen, (50, 68, 42), (WIN_W - 120, WIN_H - 80), 120)

        title = self.font_menu_title.render("SmoL Chess", True, ACCENT_GOLD)
        subtitle = self.font_menu_subtitle.render(
            "Choose White and Black players before starting the match.",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(title, title.get_rect(center=(WIN_W // 2, 52)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIN_W // 2, 86)))

        self._draw_menu_side("W", "White Player", selected["W"], focus == "W", option_defs, layout["panels"]["W"], layout["cards"]["W"], mouse_pos)
        self._draw_menu_side("B", "Black Player", selected["B"], focus == "B", option_defs, layout["panels"]["B"], layout["cards"]["B"], mouse_pos)

        self._draw_time_slider(layout["time_slider_box"], layout["time_slider_track"], max_ai_time, mouse_pos)

        button_rect = layout["start_button"]
        hovered = button_rect.collidepoint(mouse_pos)
        button_color = BUTTON_HOVER if hovered else BUTTON_BG
        self._draw_round_card(button_rect, button_color, border_color=(255, 220, 145))
        text = self.font_menu_card.render("Start Match", True, (34, 24, 10))
        self.screen.blit(text, text.get_rect(center=button_rect.center))

        hint = self.font_menu_hint.render("Tab switches side • A/D or ←/→ changes player • Enter starts", True, (194, 197, 205))
        self.screen.blit(hint, hint.get_rect(center=(WIN_W // 2, WIN_H - 12)))

    def _draw_menu_side(self, side, heading, selected_key, focused, option_defs, panel_rect, card_rects, mouse_pos):
        border_color = ACCENT_GOLD if focused else BORDER
        self._draw_round_card(panel_rect, CARD_BG_ALT, border_color=border_color)

        sprite_piece = King if side == "W" else Queen
        sprite = self._scaled_sprite(side, sprite_piece, 50)
        if sprite is not None:
            self.screen.blit(sprite, sprite.get_rect(center=(panel_rect.x + 40, panel_rect.y + 36)))

        label = self.font_menu_card.render(heading, True, TEXT_COLOR)
        sub = self.font_menu_hint.render("Select one player", True, (190, 194, 206))
        self.screen.blit(label, (panel_rect.x + 74, panel_rect.y + 18))
        self.screen.blit(sub, (panel_rect.x + 74, panel_rect.y + 42))

        for key, rect in card_rects.items():
            hovered = rect.collidepoint(mouse_pos)
            is_selected = key == selected_key
            bg = CARD_HOVER if hovered else CARD_BG
            border = ACCENT_GREEN if is_selected else (112, 114, 126)
            self._draw_round_card(rect, bg, border_color=border)

            title = self.font_menu_card.render(option_defs[key]["title"], True, TEXT_COLOR)
            subtitle = self.font_menu_hint.render(option_defs[key]["subtitle"], True, (180, 184, 194))
            self.screen.blit(title, (rect.x + 14, rect.y + 10))
            self.screen.blit(subtitle, (rect.x + 14, rect.y + 28))

            if is_selected:
                marker = self.font_menu_hint.render("Selected", True, ACCENT_GREEN)
                self.screen.blit(marker, (rect.right - 62, rect.y + 16))
