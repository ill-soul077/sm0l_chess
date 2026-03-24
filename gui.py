# gui.py — Pygame GUI for SmoL Chess

import pygame
import os
import random
from pieces import King, Queen, Knight, Pawn

# ── Colours ──────────────────────────────────
BG          = (18,  18,  24)
LIGHT_SQ    = (240, 217, 181)
DARK_SQ     = (181, 136,  99)
HIGHLIGHT   = (106, 168,  79, 180)
LAST_MOVE   = (205, 210,  56, 140)
CHECK_RED   = (220,  50,  50, 180)
TEXT_COLOR  = (230, 230, 230)
PANEL_BG    = (28,  28,  36)
WHITE_PIECE = (255, 255, 255)
BLACK_PIECE = (30,   30,  30)
BORDER      = (80,  80,  100)

SQ_SIZE   = 90          # pixels per square
BOARD_PX  = SQ_SIZE * 6 # 540
PANEL_W   = 260
WIN_W     = BOARD_PX + PANEL_W
WIN_H     = BOARD_PX
FPS       = 60
PIECE_SCALE = 0.86
ANIM_MS     = 160

# ── Unicode chess symbols ─────────────────────
SYMBOLS = {
    ('W', King):   '♔',
    ('W', Queen):  '♕',
    ('W', Knight): '♘',
    ('W', Pawn):   '♙',
    ('B', King):   '♚',
    ('B', Queen):  '♛',
    ('B', Knight): '♞',
    ('B', Pawn):   '♟',
}

PIECE_FILES = {
    ('W', King):   'wk.png',
    ('W', Queen):  'wq.png',
    ('W', Knight): 'wn.png',
    ('W', Pawn):   'wp.png',
    ('B', King):   'bk.png',
    ('B', Queen):  'bq.png',
    ('B', Knight): 'bn.png',
    ('B', Pawn):   'bp.png',
}


class GUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("SmoL Chess — Minimax vs Fuzzy Logic")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_piece  = self._pick_font(["dejavusans", "noto sans symbols2", "segoeuisymbol"], 56)
        self.font_label  = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 14)
        self.font_title  = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 20, bold=True)
        self.font_log    = self._pick_font(["dejavusansmono", "liberationmono", "consolas"], 13)
        self.font_big    = self._pick_font(["dejavusans", "liberationsans", "consolas"], 36, bold=True)

        self.piece_sprites = {}
        self.use_sprite_pieces = self._load_piece_sprites()

        # Pre-rendered board layers for a richer look with low runtime cost.
        self.board_surface = self._build_board_surface()

        # Lightweight move animation state.
        self.anim_active = False
        self.anim_sprite = None
        self.anim_from_px = (0, 0)
        self.anim_to_px = (0, 0)
        self.anim_to_sq = None
        self.anim_start_ms = 0

        self.move_log    = []       # list of strings
        self.last_move   = None     # ((r0,c0),(r1,c1))
        self.check_king  = None     # (row, col) of king in check

    # ── Public API ────────────────────────────

    def update(self, board, status_text, move_number, last_move=None, check_king=None):
        if last_move and last_move != self.last_move:
            self._start_move_animation(board, last_move)

        self.last_move  = last_move
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
        self._draw_panel(status_text, move_number)
        pygame.display.flip()
        self.clock.tick(FPS)

    def add_log(self, text):
        self.move_log.append(text)
        if len(self.move_log) > 30:
            self.move_log.pop(0)

    def show_winner(self, message, board):
        """Overlay a winner banner and wait for user to close."""
        self.update(board, message, 0)
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        text = self.font_big.render(message, True, (255, 215, 0))
        rect = text.get_rect(center=(WIN_W // 2, WIN_H // 2))
        # Shadow
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

    def delay(self, ms):
        pygame.time.delay(ms)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

    # ── Internal drawing ──────────────────────

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

        for r in range(6):
            for c in range(6):
                sq = pygame.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE)
                base = LIGHT_SQ if (r + c) % 2 == 0 else DARK_SQ
                board_surf.fill(base, sq)

                # Subtle grain lines to avoid flat squares.
                for _ in range(10):
                    y = rng.randint(sq.top + 4, sq.bottom - 4)
                    alpha = rng.randint(10, 24)
                    tint = (255, 255, 255, alpha) if (r + c) % 2 == 0 else (0, 0, 0, alpha)
                    grain = pygame.Surface((SQ_SIZE - 8, 1), pygame.SRCALPHA)
                    grain.fill(tint)
                    board_surf.blit(grain, (sq.left + 4, y))

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
                img = pygame.image.load(path).convert_alpha()
            except pygame.error:
                self.piece_sprites.clear()
                return False
            sprite = pygame.transform.smoothscale(img, (target_size, target_size))
            self.piece_sprites[key] = sprite

        return True

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

        # Last move highlight
        if self.last_move:
            (r0, c0), (r1, c1) = self.last_move
            surf.fill((0, 0, 0, 0))
            pygame.draw.circle(surf, (*LAST_MOVE[:3], 120), (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 2 - 8, 4)
            self.screen.blit(surf, self._sq_rect(r0, c0))

            surf.fill((0, 0, 0, 0))
            pygame.draw.circle(surf, (*LAST_MOVE[:3], 170), (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 5)
            self.screen.blit(surf, self._sq_rect(r1, c1))

        # King in check
        if self.check_king:
            surf.fill((0, 0, 0, 0))
            pygame.draw.rect(surf, (*CHECK_RED[:3], 180), pygame.Rect(5, 5, SQ_SIZE - 10, SQ_SIZE - 10), border_radius=10)
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
                cx = sx + (tx - sx) * t
                cy = sy + (ty - sy) * t
                anim_overlay = (cx, cy)

        for r in range(6):
            for c in range(6):
                piece = board[r][c]
                if piece is None:
                    continue

                # Skip destination square while animated piece glides in.
                if anim_overlay and self.anim_to_sq == (r, c):
                    continue

                sprite = self.piece_sprites.get((piece.color, type(piece))) if self.use_sprite_pieces else None
                cx = c * SQ_SIZE + SQ_SIZE // 2
                cy = r * SQ_SIZE + SQ_SIZE // 2

                if sprite is not None:
                    self._draw_piece_sprite(sprite, cx, cy)
                    continue

                symbol = SYMBOLS.get((piece.color, type(piece)), '?')
                color = WHITE_PIECE if piece.color == 'W' else BLACK_PIECE
                text = self.font_piece.render(symbol, True, color)

                if piece.color == 'W':
                    shadow = self.font_piece.render(symbol, True, (80, 80, 80))
                    self.screen.blit(shadow, shadow.get_rect(center=(cx + 1, cy + 1)))
                self.screen.blit(text, text.get_rect(center=(cx, cy)))

        if anim_overlay and self.anim_sprite is not None:
            self._draw_piece_sprite(self.anim_sprite, anim_overlay[0], anim_overlay[1])

    def _draw_coords(self):
        cols = 'abcdef'
        for i in range(6):
            # Column letters at bottom
            lbl = self.font_label.render(cols[i], True, BORDER)
            self.screen.blit(lbl, (i * SQ_SIZE + SQ_SIZE - 14, BOARD_PX - 16))
            # Row numbers at left
            lbl = self.font_label.render(str(6 - i), True, BORDER)
            self.screen.blit(lbl, (2, i * SQ_SIZE + 2))

    def _draw_panel(self, status_text, move_number):
        panel_rect = pygame.Rect(BOARD_PX, 0, PANEL_W, WIN_H)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect)
        pygame.draw.line(self.screen, BORDER, (BOARD_PX, 0), (BOARD_PX, WIN_H), 2)

        x = BOARD_PX + 12
        y = 16

        # Title
        title = self.font_title.render("SmoL Chess", True, (255, 215, 0))
        self.screen.blit(title, (x, y)); y += 30

        # Players
        p1 = self.font_label.render("♔ White — Minimax (α-β, depth 3)", True, (200, 220, 200))
        p2 = self.font_label.render("♚ Black — MCTS (800 simulations)",  True, (200, 200, 220))
        self.screen.blit(p1, (x, y)); y += 20
        self.screen.blit(p2, (x, y)); y += 28

        # Move counter
        mc = self.font_label.render(f"Move: {move_number}", True, TEXT_COLOR)
        self.screen.blit(mc, (x, y)); y += 24

        # Status
        st = self.font_title.render(status_text, True, (255, 180, 80))
        self.screen.blit(st, (x, y)); y += 36

        # Divider
        pygame.draw.line(self.screen, BORDER, (x, y), (x + PANEL_W - 24, y)); y += 10

        # Move log
        log_title = self.font_label.render("— Move Log —", True, BORDER)
        self.screen.blit(log_title, (x, y)); y += 18

        for entry in self.move_log[-20:]:
            rendered = self.font_log.render(entry, True, (180, 180, 195))
            self.screen.blit(rendered, (x, y))
            y += 16
            if y > WIN_H - 10:
                break