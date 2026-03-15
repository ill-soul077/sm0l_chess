# gui.py — Pygame GUI for SmoL Chess

import pygame
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


class GUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("SmoL Chess — Minimax vs Fuzzy Logic")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_piece  = pygame.font.SysFont("segoeuisymbol", 56)
        self.font_label  = pygame.font.SysFont("consolas", 14)
        self.font_title  = pygame.font.SysFont("consolas", 20, bold=True)
        self.font_log    = pygame.font.SysFont("consolas", 13)
        self.font_big    = pygame.font.SysFont("consolas", 36, bold=True)

        self.move_log    = []       # list of strings
        self.last_move   = None     # ((r0,c0),(r1,c1))
        self.check_king  = None     # (row, col) of king in check

    # ── Public API ────────────────────────────

    def update(self, board, status_text, move_number, last_move=None, check_king=None):
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

    def _sq_rect(self, row, col):
        return pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)

    def _draw_board(self):
        for r in range(6):
            for c in range(6):
                color = LIGHT_SQ if (r + c) % 2 == 0 else DARK_SQ
                pygame.draw.rect(self.screen, color, self._sq_rect(r, c))

    def _draw_highlights(self):
        surf = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)

        # Last move highlight
        if self.last_move:
            (r0, c0), (r1, c1) = self.last_move
            surf.fill((*LAST_MOVE[:3], 140))
            self.screen.blit(surf, self._sq_rect(r0, c0))
            self.screen.blit(surf, self._sq_rect(r1, c1))

        # King in check
        if self.check_king:
            surf.fill((*CHECK_RED[:3], 180))
            self.screen.blit(surf, self._sq_rect(*self.check_king))

    def _draw_pieces(self, board):
        for r in range(6):
            for c in range(6):
                piece = board[r][c]
                if piece is None:
                    continue
                symbol = SYMBOLS.get((piece.color, type(piece)), '?')
                color  = WHITE_PIECE if piece.color == 'W' else BLACK_PIECE

                text = self.font_piece.render(symbol, True, color)

                # Shadow for white pieces
                if piece.color == 'W':
                    shadow = self.font_piece.render(symbol, True, (80, 80, 80))
                    rect = text.get_rect(center=(c * SQ_SIZE + SQ_SIZE//2 + 1,
                                                  r * SQ_SIZE + SQ_SIZE//2 + 1))
                    self.screen.blit(shadow, rect)

                rect = text.get_rect(center=(c * SQ_SIZE + SQ_SIZE//2,
                                              r * SQ_SIZE + SQ_SIZE//2))
                self.screen.blit(text, rect)

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