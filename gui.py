# gui.py - Pygame GUI for SmoL Chess

import os
import random

import pygame

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
        pygame.display.set_caption("SmoL Chess")
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

        self.anim_active = False
        self.anim_sprite = None
        self.anim_from_px = (0, 0)
        self.anim_to_px = (0, 0)
        self.anim_to_sq = None
        self.anim_start_ms = 0

        self.move_log = []
        self.last_move = None
        self.check_king = None
        self.match_players = {
            "W": {"name": "White", "type": "---"},
            "B": {"name": "Black", "type": "---"},
        }

    def show_start_menu(self, option_defs, default_white="minimax", default_black="mcts"):
        selected = {"W": default_white, "B": default_black}
        focus = "W"
        option_keys = list(option_defs.keys())
        pygame.display.set_caption("SmoL Chess — Select AIs")

        while True:
            mouse_pos = pygame.mouse.get_pos()
            layout = self._menu_layout(option_defs)

            for event in pygame.event.get():
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
                        return selected
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if layout["start_button"].collidepoint(event.pos):
                        return selected
                    for side in ("W", "B"):
                        for key, rect in layout["cards"][side].items():
                            if rect.collidepoint(event.pos):
                                selected[side] = key
                                focus = side

            self._draw_menu(option_defs, selected, focus, layout, mouse_pos)
            pygame.display.flip()
            self.clock.tick(FPS)

    def set_match_players(self, white_player, black_player, white_type, black_type):
        self.match_players = {
            "W": {"name": white_player.name, "type": white_type},
            "B": {"name": black_player.name, "type": black_type},
        }
        pygame.display.set_caption(f"SmoL Chess — {white_player.name} vs {black_player.name}")

    def update(
        self,
        board,
        status_text,
        move_number,
        last_move=None,
        check_king=None,
        current_turn=None,
        last_move_time=None,
    ):
        if last_move and last_move != self.last_move:
            self._start_move_animation(board, last_move)

        self.last_move = last_move
        self.check_king = check_king
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        self.screen.fill(BG)
        self._draw_board()
        self._draw_highlights()
        self._draw_pieces(board)
        self._draw_coords()
        self._draw_panel(status_text, move_number, current_turn, last_move_time)
        pygame.display.flip()
        self.clock.tick(FPS)

    def add_log(self, text):
        self.move_log.append(text)
        if len(self.move_log) > 30:
            self.move_log.pop(0)

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

    def _draw_board(self):
        self.screen.blit(self.board_surface, (0, 0))

    def _draw_highlights(self):
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
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect)
        pygame.draw.line(self.screen, BORDER, (BOARD_PX, 0), (BOARD_PX, WIN_H), 2)

        x = BOARD_PX + 14
        y = 16

        title = self.font_title.render("SmoL Chess", True, ACCENT_GOLD)
        self.screen.blit(title, (x, y))
        y += 34

        y = self._draw_player_card(x, y, "W", (215, 225, 215), King)
        y += 10
        y = self._draw_player_card(x, y, "B", (215, 215, 230), Queen)
        y += 14

        stats_rect = pygame.Rect(x, y, PANEL_W - 28, 112)
        self._draw_round_card(stats_rect, CARD_BG_ALT)
        status = self.font_title.render(status_text, True, (255, 188, 104))
        self.screen.blit(status, (stats_rect.x + 12, stats_rect.y + 10))

        move_time_text = "---" if last_move_time is None else f"{last_move_time:.2f}s"
        rows = [
            f"Move: {move_number}",
            f"Turn: {self._turn_label(current_turn)}",
            f"Last Move Time: {move_time_text}",
            f"White AI: {self.match_players['W']['type']}",
            f"Black AI: {self.match_players['B']['type']}",
        ]
        row_y = stats_rect.y + 42
        for row_text in rows:
            rendered = self.font_label.render(row_text, True, TEXT_COLOR)
            self.screen.blit(rendered, (stats_rect.x + 12, row_y))
            row_y += 14
        y = stats_rect.bottom + 12

        log_rect = pygame.Rect(x, y, PANEL_W - 28, WIN_H - y - 14)
        self._draw_round_card(log_rect, CARD_BG)
        log_title = self.font_label.render("Move Log", True, ACCENT_GOLD)
        self.screen.blit(log_title, (log_rect.x + 12, log_rect.y + 10))

        line_y = log_rect.y + 34
        for entry in self.move_log[-18:]:
            rendered = self.font_log.render(entry, True, (186, 188, 199))
            self.screen.blit(rendered, (log_rect.x + 12, line_y))
            line_y += 16
            if line_y > log_rect.bottom - 10:
                break

    def _draw_player_card(self, x, y, side, accent_color, sprite_piece):
        rect = pygame.Rect(x, y, PANEL_W - 28, 72)
        self._draw_round_card(rect, CARD_BG)
        sprite = self._scaled_sprite(side, sprite_piece, 42)
        if sprite is not None:
            self.screen.blit(sprite, sprite.get_rect(center=(rect.x + 28, rect.y + 36)))

        side_label = "White" if side == "W" else "Black"
        line1 = self.font_label.render(f"{side_label}: {self.match_players[side]['name']}", True, accent_color)
        line2 = self.font_label.render(f"AI Type: {self.match_players[side]['type']}", True, TEXT_COLOR)
        self.screen.blit(line1, (rect.x + 56, rect.y + 16))
        self.screen.blit(line2, (rect.x + 56, rect.y + 38))
        return rect.bottom

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

    def _menu_layout(self, option_defs):
        left_panel = pygame.Rect(48, 120, 340, 300)
        right_panel = pygame.Rect(WIN_W - 388, 120, 340, 300)
        start_button = pygame.Rect(WIN_W // 2 - 110, WIN_H - 90, 220, 52)

        cards = {"W": {}, "B": {}}
        for idx, key in enumerate(option_defs.keys()):
            cards["W"][key] = pygame.Rect(left_panel.x + 18, left_panel.y + 78 + idx * 64, left_panel.width - 36, 50)
            cards["B"][key] = pygame.Rect(right_panel.x + 18, right_panel.y + 78 + idx * 64, right_panel.width - 36, 50)

        return {
            "panels": {"W": left_panel, "B": right_panel},
            "cards": cards,
            "start_button": start_button,
        }

    def _draw_menu(self, option_defs, selected, focus, layout, mouse_pos):
        self.screen.fill(BG)
        self.screen.blit(self.board_surface, (0, 0))
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 215))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.circle(self.screen, (64, 48, 28), (110, 90), 90)
        pygame.draw.circle(self.screen, (50, 68, 42), (WIN_W - 120, WIN_H - 80), 120)

        title = self.font_menu_title.render("SmoL Chess", True, ACCENT_GOLD)
        subtitle = self.font_menu_subtitle.render(
            "Choose the White and Black AI opponents before starting the match.",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(title, title.get_rect(center=(WIN_W // 2, 52)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIN_W // 2, 86)))

        self._draw_menu_side("W", "White AI", selected["W"], focus == "W", option_defs, layout["panels"]["W"], layout["cards"]["W"], mouse_pos)
        self._draw_menu_side("B", "Black AI", selected["B"], focus == "B", option_defs, layout["panels"]["B"], layout["cards"]["B"], mouse_pos)

        button_rect = layout["start_button"]
        hovered = button_rect.collidepoint(mouse_pos)
        button_color = BUTTON_HOVER if hovered else BUTTON_BG
        self._draw_round_card(button_rect, button_color, border_color=(255, 220, 145))
        text = self.font_menu_card.render("Start Match", True, (34, 24, 10))
        self.screen.blit(text, text.get_rect(center=button_rect.center))

        hint = self.font_menu_hint.render("Tab switches side • A/D or ←/→ changes option • Enter starts", True, (194, 197, 205))
        self.screen.blit(hint, hint.get_rect(center=(WIN_W // 2, WIN_H - 18)))

    def _draw_menu_side(self, side, heading, selected_key, focused, option_defs, panel_rect, card_rects, mouse_pos):
        border_color = ACCENT_GOLD if focused else BORDER
        self._draw_round_card(panel_rect, CARD_BG_ALT, border_color=border_color)

        sprite_piece = King if side == "W" else Queen
        sprite = self._scaled_sprite(side, sprite_piece, 50)
        if sprite is not None:
            self.screen.blit(sprite, sprite.get_rect(center=(panel_rect.x + 40, panel_rect.y + 36)))

        label = self.font_menu_card.render(heading, True, TEXT_COLOR)
        sub = self.font_menu_hint.render("Select one engine", True, (190, 194, 206))
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
