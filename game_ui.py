"""
PopOut Game Interface  ·  Dark Terminal Aesthetic
=================================================
Supports:
  Human vs Human
  Human vs Computer (MCTS or ID3)
  Computer vs Human (MCTS or ID3)
  Computer vs Computer (any combination)
  ID3 vs MCTS (preset mode)

Controls (Human moves):
  ↓  – click the green circle above a column  → DROP
  ↑  – click the green circle below a column  → POP
  Q  – quit at any time
"""

import pygame
import sys
import time
import os
import math
import threading
import tracemalloc
import psutil

from PopOut import PopOutState, PLAYER_1, PLAYER_2, ROWS, COLS, EMPTY
from MCTS import MCTSHeuristic as MCTSAlgo
from ID3 import load_tree, predict_sample

pygame.init()

# ═══════════════════════════════════════════════════════════════════════════════
#  Layout
# ═══════════════════════════════════════════════════════════════════════════════
SCREEN_W, SCREEN_H = 1280, 720

CELL        = 82
BOARD_W     = COLS * CELL        # 574
BOARD_H     = ROWS * CELL        # 492
DROP_ZONE_H = 56
POP_ZONE_H  = 56
GAP         = 8

MARGIN_TOP = (SCREEN_H - DROP_ZONE_H - GAP - BOARD_H - GAP - POP_ZONE_H - 56) // 2
DROP_TOP   = MARGIN_TOP
BOARD_TOP  = DROP_TOP + DROP_ZONE_H + GAP
POP_TOP    = BOARD_TOP + BOARD_H + GAP
STATUS_Y   = POP_TOP + POP_ZONE_H + 8
BOARD_LEFT = (SCREEN_W - BOARD_W) // 2

# ═══════════════════════════════════════════════════════════════════════════════
#  Paths
# ═══════════════════════════════════════════════════════════════════════════════
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR     = os.path.join(SCRIPT_DIR, "assets")
DATA_DIR       = os.path.join(SCRIPT_DIR, "data")
FONT_MONO_PATH = os.path.join(SCRIPT_DIR, "Space_Mono", "SpaceMono-Bold.ttf")
FONT_UI_PATH   = os.path.join(SCRIPT_DIR, "Space_Grotesk", "static", "SpaceGrotesk-Medium.ttf")
TREE_PATH      = os.path.join(DATA_DIR, "popout_tree.json")
DATA_PATH      = os.path.join(DATA_DIR, "popout_pairs.csv")

# ═══════════════════════════════════════════════════════════════════════════════
#  Colour palette  ·  Dark Terminal
# ═══════════════════════════════════════════════════════════════════════════════
C_BG        = ( 10,  10,  15)   # fundo principal
C_SURFACE   = ( 14,  14,  26)   # cards / painéis
C_SURFACE2  = ( 18,  18,  42)   # tabuleiro
C_BORDER    = ( 30,  30,  46)   # bordas normais
C_TEXT      = (232, 228, 219)   # texto principal
C_MUTED     = ( 74,  74, 106)   # texto secundário
C_DIM       = ( 42,  42,  64)   # texto apagado / contadores
C_P1        = (201,  79,  42)   # Player 1  ·  vermelho-laranja
C_P1_RING   = (224, 128,  96)   # anel brilhante P1
C_P2        = ( 42,  74, 201)   # Player 2  ·  azul-índigo
C_P2_RING   = ( 96, 128, 224)   # anel brilhante P2
C_GREEN     = ( 42, 122,  74)   # indicador drop/pop disponível
C_GREEN_HL  = ( 60, 200, 100)   # hover drop/pop
C_GREEN_BG  = ( 10,  26,  16)   # fundo hover
C_ACCENT    = (201,  79,  42)   # acento geral (= C_P1)
C_EMPTY_CLR = ( 22,  22,  38)   # célula vazia

# ═══════════════════════════════════════════════════════════════════════════════
#  Game constants
# ═══════════════════════════════════════════════════════════════════════════════
AI_MCTS = "MCTS"
AI_ID3  = "ID3"

DIFFICULTY = {
    1: {"max_simulations": 300,  "max_time": 0.8},
    2: {"max_simulations": 700,  "max_time": 1.5},
    3: {"max_simulations": 1500, "max_time": 3.0},
}
DIFFICULTY_LABELS = {1: "Easy", 2: "Medium", 3: "Hard"}
MAX_MOVES_CVC = 250

# ── Animation spinner frames ─────────────────────────────────────────────────
_SPIN = ["|", "/", "\u2014", "\\"]

# ── CvC speed presets (seconds; None = step-by-step) ────────────────────────
CVC_SPEEDS    = [0.05, 0.25, 0.8, None]
CVC_SPEED_LBL = ["1·fast", "2·normal", "3·slow", "SPC·step"]

# ═══════════════════════════════════════════════════════════════════════════════
#  Font cache  (loads each font+size once, reuses thereafter)
# ═══════════════════════════════════════════════════════════════════════════════
_font_cache: dict = {}

def _load_font(path: str, size: int, fallback: str) -> pygame.font.Font:
    key = (path, size)
    if key not in _font_cache:
        if os.path.exists(path):
            try:
                _font_cache[key] = pygame.font.Font(path, size)
                return _font_cache[key]
            except Exception:
                pass
        _font_cache[key] = pygame.font.SysFont(fallback, size)
    return _font_cache[key]

def mono(size: int) -> pygame.font.Font:
    """Space Mono Bold — monospace fallback."""
    return _load_font(FONT_MONO_PATH, size, "monospace")

def ui(size: int) -> pygame.font.Font:
    """Space Grotesk Medium — sans fallback."""
    return _load_font(FONT_UI_PATH, size, "sans")

# ═══════════════════════════════════════════════════════════════════════════════
#  ID3 agent  (lazy-loaded)
# ═══════════════════════════════════════════════════════════════════════════════
_id3_tree = None

def get_id3_tree():
    global _id3_tree
    if _id3_tree is not None:
        return _id3_tree
    _id3_tree = load_tree(TREE_PATH)
    if _id3_tree is None:
        print("ID3 tree not found — training from dataset…")
        import pandas as pd
        if os.path.exists(DATA_PATH):
            df = pd.read_csv(DATA_PATH)
            from ID3 import id3 as id3_build, save_tree
            features = [f'c{i}' for i in range(42)]
            df['move'] = df['move'].astype(str)
            _id3_tree = id3_build(df, features, 'move', max_depth=12)
            save_tree(_id3_tree, TREE_PATH)
        else:
            print("ERROR: No dataset to train ID3!")
    return _id3_tree


def get_id3_move(state):
    import random
    tree        = get_id3_tree()
    valid_moves = state.get_valid_moves()
    if not valid_moves:
        return None

    # Immediate win
    for move in valid_moves:
        ns = state.make_move(move)
        if ns.get_winner() == state.current_player:
            return move

    # Block opponent win
    opp = state.get_opponent()
    for move in valid_moves:
        ns = state.make_move(move)
        if ns.get_winner() == opp:
            return move

    if tree is None:
        return random.choice(valid_moves)

    board_flat = [cell for row in state.board for cell in row]
    sample     = {f'c{i}': str(board_flat[i]) for i in range(42)}
    pred       = predict_sample(tree, sample, default=None)
    drop_moves = [m for m in valid_moves if m[0] == "drop"]

    # pred is "drop_4" or "pop_2" — parse and find best matching valid move
    if isinstance(pred, str) and '_' in pred:
        try:
            move_type, move_col_str = pred.split('_', 1)
            move_col  = int(move_col_str)
            candidate = (move_type, move_col)
            if candidate in valid_moves:
                return candidate
            typed = [m for m in valid_moves if m[0] == move_type]
            if typed:
                return min(typed, key=lambda m: abs(m[1] - move_col))
        except (ValueError, AttributeError):
            pass

    # Fallback: centre drop
    if drop_moves:
        drop_moves.sort(key=lambda m: abs(m[1] - COLS // 2))
        return drop_moves[0]
    return valid_moves[0]


# ═══════════════════════════════════════════════════════════════════════════════
#  Board helpers
# ═══════════════════════════════════════════════════════════════════════════════

def find_winning_cells(board):
    """Return list of (row, col) that form the winning 4-in-a-row, or []."""
    for player in (PLAYER_1, PLAYER_2):
        # Horizontal
        for row in range(ROWS):
            for col in range(COLS - 3):
                cells = [(row, col + i) for i in range(4)]
                if all(board[r][c] == player for r, c in cells):
                    return cells
        # Vertical
        for col in range(COLS):
            for row in range(ROWS - 3):
                cells = [(row + i, col) for i in range(4)]
                if all(board[r][c] == player for r, c in cells):
                    return cells
        # Diagonal ↘
        for row in range(ROWS - 3):
            for col in range(COLS - 3):
                cells = [(row + i, col + i) for i in range(4)]
                if all(board[r][c] == player for r, c in cells):
                    return cells
        # Diagonal ↗
        for row in range(3, ROWS):
            for col in range(COLS - 3):
                cells = [(row - i, col + i) for i in range(4)]
                if all(board[r][c] == player for r, c in cells):
                    return cells
    return []


def get_drop_row(board, col):
    """Row where a piece lands if dropped in col; -1 if column is full."""
    for row in range(ROWS - 1, -1, -1):
        if board[row][col] == EMPTY:
            return row
    return -1


# ═══════════════════════════════════════════════════════════════════════════════
#  Drawing primitives
# ═══════════════════════════════════════════════════════════════════════════════

def fill_bg(screen: pygame.Surface):
    screen.fill(C_BG)


def draw_piece(screen, cx, cy, r, color, ring_color):
    """Disc with coloured ring + dark gap — gives a raised / 3-D feel."""
    pygame.draw.circle(screen, C_BG,       (cx, cy), r + 3)
    pygame.draw.circle(screen, ring_color, (cx, cy), r + 2)
    pygame.draw.circle(screen, color,      (cx, cy), r)


def draw_empty_cell(screen, cx, cy, r):
    """Empty board slot."""
    pygame.draw.circle(screen, C_BG,        (cx, cy), r + 2)
    pygame.draw.circle(screen, C_EMPTY_CLR, (cx, cy), r)
    pygame.draw.circle(screen, C_BORDER,    (cx, cy), r, 1)


def draw_logo(screen, cx, cy):
    """'POP' white + 'OUT' orange + orange dot — pure code, no images."""
    f  = mono(68)
    t1 = f.render("POP", True, C_TEXT)
    t2 = f.render("OUT", True, C_ACCENT)
    total_w = t1.get_width() + t2.get_width()
    x = cx - total_w // 2
    screen.blit(t1, (x, cy))
    screen.blit(t2, (x + t1.get_width(), cy))
    pygame.draw.circle(screen, C_ACCENT,
                       (x + total_w + 11, cy + t1.get_height() - 16), 7)


def draw_panel(screen, rect: pygame.Rect):
    pygame.draw.rect(screen, C_SURFACE, rect, border_radius=10)
    pygame.draw.rect(screen, C_BORDER,  rect, width=1, border_radius=10)


def draw_menu_btn(screen, rect: pygame.Rect, label: str, num: int, hover: bool):
    """Numbered list-style button with orange border on hover."""
    bg     = (21, 15, 10) if hover else C_SURFACE
    border = C_ACCENT     if hover else C_BORDER
    pygame.draw.rect(screen, bg,     rect, border_radius=6)
    pygame.draw.rect(screen, border, rect, width=1, border_radius=6)

    n = mono(12).render(f"0{num}", True, C_ACCENT if hover else C_DIM)
    screen.blit(n, (rect.x + 16, rect.centery - n.get_height() // 2))

    t = ui(17).render(label, True, C_TEXT)
    screen.blit(t, (rect.x + 54, rect.centery - t.get_height() // 2))

    if hover:
        arr = ui(17).render("→", True, C_ACCENT)
        screen.blit(arr, (rect.right - arr.get_width() - 16,
                          rect.centery - arr.get_height() // 2))


def draw_status_bar(screen, state, move_count: int, rect: pygame.Rect,
                    thinking: bool = False, spin_frame: int = 0):
    """Bottom bar: coloured dot + player name + hint + move counter."""
    pygame.draw.rect(screen, C_SURFACE, rect, border_radius=8)
    pygame.draw.rect(screen, C_BORDER,  rect, width=1, border_radius=8)

    color = C_P1 if state.current_player == PLAYER_1 else C_P2
    pygame.draw.circle(screen, color, (rect.x + 22, rect.centery), 5)

    lbl  = mono(9).render("TURNO ATUAL", True, C_MUTED)
    name = ui(15).render("Yellow · P1" if state.current_player == PLAYER_1
                         else "Purple · P2", True, C_TEXT)
    screen.blit(lbl,  (rect.x + 38, rect.centery - 13))
    screen.blit(name, (rect.x + 38, rect.centery + 2))

    if thinking:
        frame_char = _SPIN[spin_frame % len(_SPIN)]
        t = mono(11).render(f"{frame_char}  THINKING", True, C_ACCENT)
        screen.blit(t, (rect.centerx - t.get_width() // 2,
                        rect.centery  - t.get_height() // 2))
    else:
        hint = mono(10).render("↓ drop   ↑ pop", True, C_DIM)
        screen.blit(hint, (rect.centerx - hint.get_width() // 2,
                           rect.centery  - hint.get_height() // 2))

    mc = mono(10).render(f"move {move_count:02d}", True, C_DIM)
    screen.blit(mc, (rect.right - mc.get_width() - 16,
                     rect.centery - mc.get_height() // 2))


# Fixed rects for bottom-bar buttons — computed once at import time
_BACK_RECT = pygame.Rect(16,            SCREEN_H - 48, 120, 36)
_QUIT_RECT = pygame.Rect(SCREEN_W - 136, SCREEN_H - 48, 120, 36)


def draw_back_btn(screen, mp):
    """Pill-shaped '← back' button at bottom-left with hover highlight."""
    hover  = _BACK_RECT.collidepoint(mp)
    bg     = (21, 15, 10) if hover else C_SURFACE
    border = C_ACCENT     if hover else C_BORDER
    pygame.draw.rect(screen, bg,     _BACK_RECT, border_radius=7)
    pygame.draw.rect(screen, border, _BACK_RECT, width=1, border_radius=7)
    t = mono(13).render("← back", True, C_TEXT if hover else C_MUTED)
    screen.blit(t, t.get_rect(center=_BACK_RECT.center))
    return _BACK_RECT


def draw_quit_hint(screen):
    """Pill-shaped 'Q · quit' button at bottom-right."""
    pygame.draw.rect(screen, C_SURFACE, _QUIT_RECT, border_radius=7)
    pygame.draw.rect(screen, C_BORDER,  _QUIT_RECT, width=1, border_radius=7)
    t = mono(13).render("Q · quit", True, C_MUTED)
    screen.blit(t, t.get_rect(center=_QUIT_RECT.center))


# ═══════════════════════════════════════════════════════════════════════════════
#  Board rendering
# ═══════════════════════════════════════════════════════════════════════════════

def get_col_and_zone(mx, my):
    if mx < BOARD_LEFT or mx >= BOARD_LEFT + BOARD_W:
        return -1, None
    col = (mx - BOARD_LEFT) // CELL
    if DROP_TOP <= my < BOARD_TOP:
        return col, "drop"
    if BOARD_TOP <= my < BOARD_TOP + BOARD_H:
        return col, "board"
    if POP_TOP <= my < POP_TOP + POP_ZONE_H:
        return col, "pop"
    return -1, None


def draw_board(screen, state, hover_col, hover_zone, move_count: int,
               thinking: bool = False, win_cells=(), ghost_col=-1, ghost_row=-1,
               spin_frame: int = 0):
    """Full board render: background, pieces, indicators, status bar."""
    # Column numbers 1–7 at top of screen
    for _c in range(COLS):
        _cx = BOARD_LEFT + _c * CELL + CELL // 2
        _n  = mono(9).render(str(_c + 1), True, C_DIM)
        screen.blit(_n, (_cx - _n.get_width() // 2, 5))

    # Board background
    board_rect = pygame.Rect(BOARD_LEFT - 10, BOARD_TOP - 10,
                             BOARD_W + 20, BOARD_H + 20)
    pygame.draw.rect(screen, C_SURFACE2, board_rect, border_radius=12)
    pygame.draw.rect(screen, C_BORDER,   board_rect, width=1, border_radius=12)

    board       = state.board
    valid_moves = state.get_valid_moves()
    valid_drops = {col for t, col in valid_moves if t == "drop"}
    valid_pops  = {col for t, col in valid_moves if t == "pop"}

    r     = CELL // 2 - 6
    ind_r = CELL // 2 - 20
    win_set = set(map(tuple, win_cells))

    # ── Pieces ────────────────────────────────────────────────────────────────
    for row in range(ROWS):
        for col in range(COLS):
            cx   = BOARD_LEFT + col * CELL + CELL // 2
            cy   = BOARD_TOP  + row * CELL + CELL // 2
            cell = board[row][col]
            if cell == PLAYER_1:
                draw_piece(screen, cx, cy, r, C_P1, C_P1_RING)
            elif cell == PLAYER_2:
                draw_piece(screen, cx, cy, r, C_P2, C_P2_RING)
            else:
                draw_empty_cell(screen, cx, cy, r)
            # Pop-available highlight on bottom row
            if row == ROWS - 1 and col in valid_pops and cell != EMPTY:
                pygame.draw.circle(screen, C_GREEN_HL, (cx, cy), r + 4, 2)
            # Winning cell glow (pulsing ring)
            if (row, col) in win_set:
                pulse = int(3 + 2 * math.sin(pygame.time.get_ticks() / 150))
                pygame.draw.circle(screen, (255, 255, 255), (cx, cy), r + pulse, 3)

    # Ghost drop preview (semi-transparent disc at landing position)
    if ghost_col >= 0 and ghost_row >= 0:
        gcx = BOARD_LEFT + ghost_col * CELL + CELL // 2
        gcy = BOARD_TOP  + ghost_row * CELL + CELL // 2
        ghost_surf = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        gcolor = (*C_P1, 90) if state.current_player == PLAYER_1 else (*C_P2, 90)
        gring  = (*C_P1_RING, 60) if state.current_player == PLAYER_1 else (*C_P2_RING, 60)
        pygame.draw.circle(ghost_surf, gring,  (CELL // 2, CELL // 2), r + 2)
        pygame.draw.circle(ghost_surf, gcolor, (CELL // 2, CELL // 2), r)
        screen.blit(ghost_surf, (gcx - CELL // 2, gcy - CELL // 2))

    # ── Drop indicators (above board) ─────────────────────────────────────────
    for col in range(COLS):
        cx = BOARD_LEFT + col * CELL + CELL // 2
        cy = DROP_TOP + DROP_ZONE_H // 2
        if col in valid_drops:
            is_h = (col == hover_col and hover_zone == "drop")
            pygame.draw.circle(screen,
                               C_GREEN_BG if is_h else C_SURFACE2, (cx, cy), ind_r)
            pygame.draw.circle(screen,
                               C_GREEN_HL if is_h else C_GREEN,    (cx, cy), ind_r, 2)
            arr = mono(13).render("↓", True, C_GREEN_HL if is_h else C_GREEN)
            screen.blit(arr, arr.get_rect(center=(cx, cy)))
        else:
            pygame.draw.circle(screen, C_SURFACE2, (cx, cy), ind_r)
            pygame.draw.circle(screen, C_BORDER,   (cx, cy), ind_r, 1)

    # ── Pop indicators (below board) ──────────────────────────────────────────
    for col in range(COLS):
        cx = BOARD_LEFT + col * CELL + CELL // 2
        cy = POP_TOP + POP_ZONE_H // 2
        if col in valid_pops:
            is_h = (col == hover_col and hover_zone == "pop")
            pygame.draw.circle(screen,
                               C_GREEN_BG if is_h else C_SURFACE2, (cx, cy), ind_r)
            pygame.draw.circle(screen,
                               C_GREEN_HL if is_h else C_GREEN,    (cx, cy), ind_r, 2)
            arr = mono(13).render("↑", True, C_GREEN_HL if is_h else C_GREEN)
            screen.blit(arr, arr.get_rect(center=(cx, cy)))
        else:
            pygame.draw.circle(screen, C_SURFACE2, (cx, cy), ind_r)
            pygame.draw.circle(screen, C_BORDER,   (cx, cy), ind_r, 1)

    # ── Status bar ────────────────────────────────────────────────────────────
    sb_rect = pygame.Rect(BOARD_LEFT - 10, STATUS_Y, BOARD_W + 20, 50)
    draw_status_bar(screen, state, move_count, sb_rect, thinking, spin_frame)


# ═══════════════════════════════════════════════════════════════════════════════
#  Drop animation
# ═══════════════════════════════════════════════════════════════════════════════

def animate_drop(screen, state, col: int, move_count: int, clock):
    """Animate a piece falling from the drop zone into landing row.
    Call BEFORE state.make_move() so the board is still the pre-move state."""
    landing_row = get_drop_row(state.board, col)
    if landing_row == -1:
        return
    start_y  = DROP_TOP + DROP_ZONE_H // 2
    end_y    = BOARD_TOP + landing_row * CELL + CELL // 2
    cx       = BOARD_LEFT + col * CELL + CELL // 2
    r        = CELL // 2 - 6
    color      = C_P1      if state.current_player == PLAYER_1 else C_P2
    ring_color = C_P1_RING if state.current_player == PLAYER_1 else C_P2_RING

    duration = 0.16   # seconds
    t_start  = time.time()
    while True:
        t_norm = (time.time() - t_start) / duration
        if t_norm >= 1.0:
            break
        ease = t_norm * t_norm   # ease-in  (accelerates like gravity)
        cy = int(start_y + (end_y - start_y) * ease)
        fill_bg(screen)
        draw_board(screen, state, -1, None, move_count)
        draw_piece(screen, cx, cy, r, color, ring_color)
        draw_quit_hint(screen)
        pygame.display.flip()
        clock.tick(60)
        for ev in pygame.event.get(pygame.QUIT):
            pygame.quit(); sys.exit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Menus
# ═══════════════════════════════════════════════════════════════════════════════

def menu_main(screen) -> int:
    """Main menu — returns 1..5."""
    labels = [
        "Human vs Human",
        "Human vs Computer",
        "Computer vs Human",
        "Computer vs Computer",
        "ID3  vs  MCTS",
    ]
    panel_w = 560
    btn_h, btn_gap = 48, 8
    panel_h = len(labels) * btn_h + (len(labels) - 1) * btn_gap + 40
    panel_x = (SCREEN_W - panel_w) // 2
    panel_y = (SCREEN_H - panel_h) // 2 + 40

    btns = [
        pygame.Rect(panel_x + 20,
                    panel_y + 20 + i * (btn_h + btn_gap),
                    panel_w - 40, btn_h)
        for i in range(len(labels))
    ]
    logo_y = panel_y - 120

    clock = pygame.time.Clock()
    while True:
        fill_bg(screen)
        mp = pygame.mouse.get_pos()

        draw_logo(screen, SCREEN_W // 2, logo_y)
        sub = mono(10).render("// board game  ·  strategy", True, C_MUTED)
        screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, logo_y + 80))

        draw_panel(screen, pygame.Rect(panel_x, panel_y, panel_w, panel_h))
        for i, (rect, label) in enumerate(zip(btns, labels)):
            draw_menu_btn(screen, rect, label, i + 1, rect.collidepoint(mp))

        draw_quit_hint(screen)
        pygame.display.flip()
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate(btns):
                    if rect.collidepoint(mp):
                        return i + 1


def menu_ai_type(screen, player_label: str):
    """AI type picker — returns AI_MCTS, AI_ID3, or None (back)."""
    CARD_W, CARD_H = 280, 170
    gap    = 24
    left_x = (SCREEN_W - CARD_W * 2 - gap) // 2
    cy     = SCREEN_H // 2 + 10
    r_mcts = pygame.Rect(left_x,               cy - CARD_H // 2, CARD_W, CARD_H)
    r_id3  = pygame.Rect(left_x + CARD_W + gap, cy - CARD_H // 2, CARD_W, CARD_H)

    cards = [
        (r_mcts, AI_MCTS, "MCTS", "Search-based",
         "Monte Carlo Tree Search", "forte  ·  mais lento"),
        (r_id3,  AI_ID3,  "ID3",  "Decision Tree",
         "Árvore de decisão treinada", "rápido  ·  mais fraco"),
    ]

    clock = pygame.time.Clock()
    while True:
        fill_bg(screen)
        mp = pygame.mouse.get_pos()

        title = ui(22).render(f"{player_label}  ·  Choose AI", True, C_TEXT)
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, cy - 112))
        sub = mono(10).render("// select algorithm", True, C_MUTED)
        screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, cy - 84))

        for rect, _, name, desc1, desc2a, desc2b in cards:
            hover  = rect.collidepoint(mp)
            bg     = (21, 15, 10) if hover else C_SURFACE
            border = C_ACCENT     if hover else C_BORDER
            pygame.draw.rect(screen, bg,     rect, border_radius=10)
            pygame.draw.rect(screen, border, rect, width=1, border_radius=10)

            # Big first letter in accent, rest white
            f1 = mono(28).render(name[0],  True, C_ACCENT)
            f2 = mono(28).render(name[1:], True, C_TEXT)
            screen.blit(f1, (rect.x + 20, rect.y + 20))
            screen.blit(f2, (rect.x + 20 + f1.get_width(), rect.y + 20))

            d1 = ui(16).render(desc1,  True, C_TEXT)
            d2 = mono(9).render(desc2a, True, C_MUTED)
            d3 = mono(9).render(desc2b, True, C_MUTED)
            screen.blit(d1, (rect.x + 20, rect.y + 62))
            screen.blit(d2, (rect.x + 20, rect.y + 90))
            screen.blit(d3, (rect.x + 20, rect.y + 106))

        back_rect = draw_back_btn(screen, mp)
        draw_quit_hint(screen)
        pygame.display.flip()
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): return None
                if ev.key == pygame.K_q: pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if r_mcts.collidepoint(mp): return AI_MCTS
                if r_id3.collidepoint(mp):  return AI_ID3
                if back_rect.collidepoint(mp): return None


def menu_difficulty(screen, player_label: str):
    """MCTS difficulty picker — returns 1/2/3 or None (back)."""
    diffs = [
        (1, "Easy",   "0.8s", 1),
        (2, "Medium", "1.5s", 2),
        (3, "Hard",   "3.0s", 3),
    ]
    panel_w = 480
    btn_h, btn_gap = 54, 10
    panel_h = len(diffs) * btn_h + (len(diffs) - 1) * btn_gap + 36
    panel_x = (SCREEN_W - panel_w) // 2
    panel_y = (SCREEN_H - panel_h) // 2 + 30

    btns = [
        pygame.Rect(panel_x + 18,
                    panel_y + 18 + i * (btn_h + btn_gap),
                    panel_w - 36, btn_h)
        for i in range(len(diffs))
    ]

    clock = pygame.time.Clock()
    while True:
        fill_bg(screen)
        mp = pygame.mouse.get_pos()

        title = ui(22).render(f"{player_label}  ·  Difficulty", True, C_TEXT)
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, panel_y - 58))
        sub = mono(10).render("// higher = stronger, slower", True, C_MUTED)
        screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, panel_y - 30))

        draw_panel(screen, pygame.Rect(panel_x, panel_y, panel_w, panel_h))

        for (d, name, time_str, n_dots), rect in zip(diffs, btns):
            hover  = rect.collidepoint(mp)
            bg     = (21, 15, 10) if hover else C_SURFACE
            border = C_ACCENT     if hover else C_BORDER
            pygame.draw.rect(screen, bg,     rect, border_radius=6)
            pygame.draw.rect(screen, border, rect, width=1, border_radius=6)

            t = ui(18).render(name, True, C_TEXT)
            screen.blit(t, (rect.x + 20, rect.centery - t.get_height() // 2))

            # Difficulty dots  ●●○
            for j in range(3):
                clr = C_ACCENT if j < n_dots else C_BORDER
                pygame.draw.circle(screen, clr,
                                   (rect.right - 72 + j * 18, rect.centery), 5)

            ts = mono(10).render(time_str, True, C_MUTED)
            screen.blit(ts, (rect.right - ts.get_width() - 12,
                             rect.centery - ts.get_height() // 2))

        back_rect = draw_back_btn(screen, mp)
        draw_quit_hint(screen)
        pygame.display.flip()
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): return None
                if ev.key == pygame.K_q: pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate(btns):
                    if rect.collidepoint(mp): return i + 1
                if back_rect.collidepoint(mp): return None


def menu_post_game(screen, winner, p1_lbl: str, p2_lbl: str,
                   move_count: int, elapsed: float) -> str:
    """Win screen with dark overlay over the board — returns 'again' | 'menu'."""
    bg_capture = screen.copy()   # freeze board state as background
    overlay    = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((10, 10, 15, 225))

    cx = SCREEN_W // 2

    if winner == PLAYER_1:
        who, lbl = "P1", p1_lbl.upper()
    elif winner == PLAYER_2:
        who, lbl = "P2", p2_lbl.upper()
    else:
        who, lbl = "",   "DRAW"

    btns_labels = ["Play Again", "Main Menu", "Quit"]
    btn_w, btn_h, btn_gap = 220, 46, 10
    btns_top = SCREEN_H // 2 + 70
    btns = [
        pygame.Rect(cx - btn_w // 2,
                    btns_top + i * (btn_h + btn_gap), btn_w, btn_h)
        for i in range(len(btns_labels))
    ]

    clock = pygame.time.Clock()
    while True:
        screen.blit(bg_capture, (0, 0))
        screen.blit(overlay,    (0, 0))
        mp  = pygame.mouse.get_pos()
        cy0 = SCREEN_H // 2 - 70

        # "● GAME OVER" badge
        badge_txt  = mono(10).render("● GAME OVER", True, C_ACCENT)
        bw         = badge_txt.get_width() + 24
        bh         = badge_txt.get_height() + 10
        badge_rect = pygame.Rect(cx - bw // 2, cy0 - 80, bw, bh)
        pygame.draw.rect(screen, C_SURFACE, badge_rect, border_radius=12)
        pygame.draw.rect(screen, C_ACCENT,  badge_rect, width=1, border_radius=12)
        screen.blit(badge_txt, (badge_rect.x + 12, badge_rect.y + 5))

        # Sub-label
        sub_str = f"{who}  ·  {lbl}" if who else "— DRAW —"
        sub = mono(13).render(sub_str, True, C_MUTED)
        screen.blit(sub, (cx - sub.get_width() // 2, cy0 - 42))

        # Big title
        title = mono(62).render("WINS." if winner is not None else "DRAW.", True, C_TEXT)
        screen.blit(title, (cx - title.get_width() // 2, cy0))

        # Stats line
        stats = mono(11).render(
            f"{move_count} movimentos  ·  {elapsed:.1f}s  ·  {lbl}", True, C_MUTED)
        screen.blit(stats, (cx - stats.get_width() // 2, cy0 + 72))

        # Buttons
        for rect, label in zip(btns, btns_labels):
            hover  = rect.collidepoint(mp)
            bg     = (21, 15, 10) if hover else C_SURFACE
            border = C_ACCENT     if hover else C_BORDER
            pygame.draw.rect(screen, bg,     rect, border_radius=6)
            pygame.draw.rect(screen, border, rect, width=1, border_radius=6)
            t = ui(16).render(label, True, C_TEXT)
            screen.blit(t, (rect.centerx - t.get_width() // 2,
                            rect.centery  - t.get_height() // 2))

        pygame.display.flip()
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if btns[0].collidepoint(mp): return "again"
                if btns[1].collidepoint(mp): return "menu"
                if btns[2].collidepoint(mp): pygame.quit(); sys.exit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Move getters
# ═══════════════════════════════════════════════════════════════════════════════

def make_player_label(tipo, player, ai1_type, ai2_type, diff1, diff2) -> str:
    if player == PLAYER_1:
        if tipo in (1, 2): return "Human"
        ai = ai1_type
        d  = DIFFICULTY_LABELS.get(diff1, "")
        return f"MCTS-{d}" if ai == AI_MCTS else "ID3"
    else:
        if tipo in (1, 3): return "Human"
        ai = ai2_type
        d  = DIFFICULTY_LABELS.get(diff2, "")
        return f"MCTS-{d}" if ai == AI_MCTS else "ID3"


def get_human_move(screen, state, move_count: int, clock):
    """Block until the human clicks a valid move. Returns move or None (quit)."""
    valid_moves = state.get_valid_moves()
    valid_drops = {col for t, col in valid_moves if t == "drop"}
    valid_pops  = {col for t, col in valid_moves if t == "pop"}

    while True:
        mp = pygame.mouse.get_pos()
        hover_col, hover_zone = get_col_and_zone(*mp)

        # Ghost preview: compute landing row for hovered drop column
        ghost_col = ghost_row = -1
        if hover_zone == "drop" and hover_col in valid_drops:
            ghost_col = hover_col
            ghost_row = get_drop_row(state.board, hover_col)

        fill_bg(screen)
        draw_board(screen, state, hover_col, hover_zone, move_count, False,
                   ghost_col=ghost_col, ghost_row=ghost_row)
        draw_quit_hint(screen)
        pygame.display.flip()
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                col, zone = get_col_and_zone(*ev.pos)
                if col == -1:
                    continue
                if zone in ("drop", "board") and col in valid_drops:
                    return ("drop", col)
                if zone == "pop" and col in valid_pops:
                    return ("pop", col)


def get_computer_move(screen, state, ai_type, difficulty, move_count: int, clock):
    """Compute AI move in a background thread; animate a spinner while waiting."""
    result = [None]
    exc    = [None]

    def _compute():
        try:
            if ai_type == AI_ID3:
                result[0] = get_id3_move(state)
            else:
                params     = DIFFICULTY[difficulty]
                mcts       = MCTSAlgo(max_simulations=params["max_simulations"],
                                      max_time=params["max_time"])
                move, _    = mcts.search(state)
                result[0]  = move
        except Exception as e:
            exc[0] = e

    thread = threading.Thread(target=_compute, daemon=True)
    thread.start()

    spin = 0
    while thread.is_alive():
        fill_bg(screen)
        draw_board(screen, state, -1, None, move_count, thinking=True,
                   spin_frame=spin)
        draw_quit_hint(screen)
        pygame.display.flip()
        clock.tick(12)          # ~12 fps — smooth enough for a text spinner
        spin += 1
        for ev in pygame.event.get(pygame.QUIT):
            pygame.quit(); sys.exit()

    thread.join()
    if exc[0] is not None:
        raise exc[0]
    return result[0]


# ═══════════════════════════════════════════════════════════════════════════════
#  Core game loop
# ═══════════════════════════════════════════════════════════════════════════════

def game_loop(screen, tipo, diff1, diff2, ai1_type, ai2_type):
    tracemalloc.start()
    t_start   = time.time()
    clock     = pygame.time.Clock()
    cvc_delay = 0.25    # current CvC delay (seconds); keys 1/2/3/SPACE to change
    cvc_step  = False   # step-by-step mode (press SPACE to advance each move)

    # Pre-load ID3 tree to avoid mid-game stall
    if (tipo in (3, 4) and ai1_type == AI_ID3) or (tipo in (2, 4) and ai2_type == AI_ID3):
        get_id3_tree()

    state      = PopOutState()
    move_count = 0

    while not state.is_game_over():
        move_count += 1
        if move_count > MAX_MOVES_CVC:
            break

        current  = state.current_player
        is_human = (
            tipo == 1
            or (tipo == 2 and current == PLAYER_1)
            or (tipo == 3 and current == PLAYER_2)
        )
        ai_type = ai1_type if current == PLAYER_1 else ai2_type
        diff    = diff1    if current == PLAYER_1 else diff2

        if is_human:
            move = get_human_move(screen, state, move_count, clock)
        else:
            move = get_computer_move(screen, state, ai_type, diff, move_count, clock)

        if move is None:
            tracemalloc.stop()
            return None, None, None, move_count, 0.0

        # Drop animation before state change
        if move[0] == "drop":
            animate_drop(screen, state, move[1], move_count, clock)

        state = state.make_move(move)

        fill_bg(screen)
        draw_board(screen, state, -1, None, move_count, False)
        draw_quit_hint(screen)

        # CvC speed hint (bottom-centre, above status bar)
        if tipo == 4:
            spd_idx = CVC_SPEEDS.index(None if cvc_step else cvc_delay) \
                      if (None if cvc_step else cvc_delay) in CVC_SPEEDS else 1
            spd_txt = mono(8).render(
                f"speed:  1\u00b7fast  2\u00b7normal  3\u00b7slow  SPC\u00b7step"
                f"   \u2192  {CVC_SPEED_LBL[spd_idx]}",
                True, C_DIM)
            screen.blit(spd_txt, (SCREEN_W // 2 - spd_txt.get_width() // 2,
                                  SCREEN_H - 16))

        pygame.display.flip()

        if tipo == 4:
            if cvc_step:
                # Wait for SPACE (or handle speed key presses)
                waiting = True
                while waiting:
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            pygame.quit(); sys.exit()
                        if ev.type == pygame.KEYDOWN:
                            if ev.key == pygame.K_SPACE:  waiting = False
                            if ev.key == pygame.K_1:      cvc_delay, cvc_step = 0.05,  False; waiting = False
                            if ev.key == pygame.K_2:      cvc_delay, cvc_step = 0.25,  False; waiting = False
                            if ev.key == pygame.K_3:      cvc_delay, cvc_step = 0.8,   False; waiting = False
                            if ev.key == pygame.K_q:
                                tracemalloc.stop()
                                return None, None, None, move_count, 0.0
                    clock.tick(30)
            else:
                # Normal timed delay — still process speed keys
                t0 = time.time()
                while time.time() - t0 < cvc_delay:
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            pygame.quit(); sys.exit()
                        if ev.type == pygame.KEYDOWN:
                            if ev.key == pygame.K_1:  cvc_delay, cvc_step = 0.05,  False; break
                            if ev.key == pygame.K_2:  cvc_delay, cvc_step = 0.25,  False; break
                            if ev.key == pygame.K_3:  cvc_delay, cvc_step = 0.8,   False; break
                            if ev.key == pygame.K_SPACE:  cvc_step = True; break
                            if ev.key == pygame.K_q:
                                tracemalloc.stop()
                                return None, None, None, move_count, 0.0
                    clock.tick(30)

    # Final pause with win-cell highlight
    win_cells = find_winning_cells(state.board)
    fill_bg(screen)
    draw_board(screen, state, -1, None, move_count, False, win_cells=win_cells)
    draw_quit_hint(screen)
    pygame.display.flip()
    time.sleep(0.8)

    elapsed = time.time() - t_start
    p1_lbl  = make_player_label(tipo, PLAYER_1, ai1_type, ai2_type, diff1, diff2)
    p2_lbl  = make_player_label(tipo, PLAYER_2, ai1_type, ai2_type, diff1, diff2)

    print(f"\n── Game stats ──────────────────────────────")
    print(f"  Yellow (P1)  : {p1_lbl}")
    print(f"  Purple (P2)  : {p2_lbl}")
    print(f"  Moves played : {move_count}")
    print(f"  Time elapsed : {elapsed:.2f}s")
    print(f"  CPU          : {psutil.cpu_percent():.1f}%")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"  Memory peak  : {peak / 1024 / 1024:.2f} MB")
    print(f"────────────────────────────────────────────")

    return state.get_winner(), p1_lbl, p2_lbl, move_count, elapsed


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("PopOut")

    last_config = None
    replay      = False

    while True:
        if replay and last_config is not None:
            tipo, diff1, diff2, ai1_type, ai2_type = last_config
        else:
            tipo = menu_main(screen)
            diff1 = diff2 = 2
            ai1_type = ai2_type = AI_MCTS

            # ── Mode 5: ID3 vs MCTS preset (no AI-picker menus) ─────────────
            if tipo == 5:
                ai1_type = AI_ID3
                ai2_type = AI_MCTS
                diff1    = 2
                d = menu_difficulty(screen, "Computer (Purple) — MCTS")
                if d is None: continue
                diff2 = d
                tipo  = 4     # use CvC game logic

            else:
                # ── Player 1 (Yellow) — computer if tipo 3 or 4 ─────────────
                if tipo in (3, 4):
                    lbl = "Computer (Yellow)"
                    ai1_type = menu_ai_type(screen, lbl)
                    if ai1_type is None: continue
                    if ai1_type == AI_MCTS:
                        d = menu_difficulty(screen, lbl)
                        if d is None: continue
                        diff1 = d

                # ── Player 2 (Purple) — computer if tipo 2 or 4 ─────────────
                if tipo in (2, 4):
                    lbl = "Computer (Purple)"
                    ai2_type = menu_ai_type(screen, lbl)
                    if ai2_type is None: continue
                    if ai2_type == AI_MCTS:
                        d = menu_difficulty(screen, lbl)
                        if d is None: continue
                        diff2 = d

            last_config = (tipo, diff1, diff2, ai1_type, ai2_type)

        winner, p1_lbl, p2_lbl, mc, elapsed = game_loop(
            screen, tipo, diff1, diff2, ai1_type, ai2_type
        )

        if winner is None and p1_lbl is None:
            replay = False
            continue

        decision = menu_post_game(
            screen, winner,
            p1_lbl or "Yellow", p2_lbl or "Purple",
            mc, elapsed
        )
        replay = (decision == "again")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit()
