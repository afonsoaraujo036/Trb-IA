"""
PopOut Game Interface – Pygame GUI
===================================
Supports: Human vs Human | Human vs Computer | Computer vs Human | Computer vs Computer
Computer uses MCTS algorithm with Easy / Medium / Hard presets.

Controls (Human moves):
  ↓  – click the GREEN CIRCLE above a column  → DROP a piece
  ↑  – click the GREEN CIRCLE below a column  → POP your piece from the bottom
  (hovering highlights the indicator in white before clicking)
"""

import pygame
import sys
import time
import os
import tracemalloc
import psutil

from PopOut import PopOutState, PLAYER_1, PLAYER_2, ROWS, COLS, EMPTY
from MCTS import MCTS as MCTSAlgo

pygame.init()

# ── Screen  ────────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 720

# ── Board layout  ──────────────────────────────────────────────────────────────
CELL = 82

BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL

DROP_ZONE_H = 52
POP_ZONE_H  = 52
GAP         = 8
MARGIN_TOP  = (SCREEN_H - DROP_ZONE_H - GAP - BOARD_H - GAP - POP_ZONE_H - 60) // 2

DROP_TOP  = MARGIN_TOP
BOARD_TOP = DROP_TOP + DROP_ZONE_H + GAP
POP_TOP   = BOARD_TOP + BOARD_H + GAP
STATUS_Y  = POP_TOP + POP_ZONE_H + 8

BOARD_LEFT = (SCREEN_W - BOARD_W) // 2

# ── Assets ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
BG_PATH    = os.path.join(ASSETS_DIR, "Background.png")
FONT1_PATH = os.path.join(ASSETS_DIR, "font1.otf")
FONT2_PATH = os.path.join(ASSETS_DIR, "font2.otf")

# ── Colours ────────────────────────────────────────────────────────────────────
C_BASE   = (239, 222, 198)
C_HOVER  = (100,  12,  63)
C_TEXT   = (251,  90,  72)
C_P1     = (208, 173,  45)
C_P2     = (140,  20,  60)
C_BOARD  = ( 25,  70, 155)
C_EMPTY  = (  8,   8,   8)
C_GREEN  = ( 50, 210,  80)
C_GREY   = ( 70,  70,  70)
C_WHITE  = (255, 255, 255)
C_BLACK  = (  0,   0,   0)

# ── MCTS difficulty presets ────────────────────────────────────────────────────
DIFFICULTY = {
    1: {"max_simulations": 200,  "max_time": 0.5},
    2: {"max_simulations": 500,  "max_time": 1.0},
    3: {"max_simulations": 1000, "max_time": 2.0},
}
DIFFICULTY_LABELS = {1: "Easy", 2: "Medium", 3: "Hard"}

MAX_MOVES_CVC = 250


# ═══════════════════════════════════════════════════════════════════════════════
#  Asset helpers
# ═══════════════════════════════════════════════════════════════════════════════

def load_bg():
    if os.path.exists(BG_PATH):
        bg = pygame.image.load(BG_PATH)
        return pygame.transform.scale(bg, (SCREEN_W, SCREEN_H))
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    surf.fill((20, 20, 60))
    return surf


def load_btn_images():
    imgs = []
    for i in range(1, 4):
        path = os.path.join(ASSETS_DIR, f"Rect{i}.png")
        if os.path.exists(path):
            imgs.append(pygame.image.load(path))
        else:
            s = pygame.Surface((300, 50))
            s.fill(C_BASE)
            imgs.append(s)
    return imgs


# ═══════════════════════════════════════════════════════════════════════════════
#  Button widget
# ═══════════════════════════════════════════════════════════════════════════════

class Button:
    def __init__(self, image, pos, text, font,
                 color_base=C_BASE, color_hover=C_HOVER, size=(300, 50)):
        self.img   = pygame.transform.scale(image, size) if image is not None else None
        self.cx, self.cy = pos
        self.font  = font
        self.cb    = color_base
        self.ch    = color_hover
        self.label = text
        self.rect  = pygame.Rect(0, 0, *size)
        self.rect.center = pos

    def draw(self, screen, mouse_pos):
        if self.img:
            screen.blit(self.img, self.rect)
        color = self.ch if self.rect.collidepoint(mouse_pos) else self.cb
        surf  = self.font.render(self.label, True, color)
        screen.blit(surf, surf.get_rect(center=(self.cx, self.cy)))

    def hit(self, pos):
        return self.rect.collidepoint(pos)


# ═══════════════════════════════════════════════════════════════════════════════
#  Back-to-menu button (usado durante o jogo)
# ═══════════════════════════════════════════════════════════════════════════════

def make_back_btn(img_btn, font):
    """Cria o botão 'Menu' no canto inferior esquerdo."""
    return Button(img_btn[2], (100, SCREEN_H - 35), "Quit Game", font,
                  color_base=C_BASE, color_hover=C_HOVER, size=(160, 44))


def draw_back_btn(screen, btn, mouse_pos):
    btn.draw(screen, mouse_pos)


# ═══════════════════════════════════════════════════════════════════════════════
#  Board rendering
# ═══════════════════════════════════════════════════════════════════════════════

def draw_board(screen, state, hover_col, hover_zone, font_small):
    board       = state.board
    valid_moves = state.get_valid_moves()
    valid_drops = {col for t, col in valid_moves if t == "drop"}
    valid_pops  = {col for t, col in valid_moves if t == "pop"}

    frame = pygame.Rect(BOARD_LEFT - 6, BOARD_TOP - 6, BOARD_W + 12, BOARD_H + 12)
    pygame.draw.rect(screen, C_BOARD, frame, border_radius=12)

    for row in range(ROWS):
        for col in range(COLS):
            cx = BOARD_LEFT + col * CELL + CELL // 2
            cy = BOARD_TOP  + row * CELL + CELL // 2
            r  = CELL // 2 - 5

            cell  = board[row][col]
            color = C_P1 if cell == PLAYER_1 else (C_P2 if cell == PLAYER_2 else C_EMPTY)
            pygame.draw.circle(screen, color, (cx, cy), r)

            if row == ROWS - 1 and col in valid_pops and cell != EMPTY:
                pygame.draw.circle(screen, C_GREEN, (cx, cy), r, 3)

    ind_r = CELL // 2 - 18

    for col in range(COLS):
        cx = BOARD_LEFT + col * CELL + CELL // 2
        cy = DROP_TOP + DROP_ZONE_H // 2

        if col in valid_drops:
            hovered = (col == hover_col and hover_zone == "drop")
            fill    = C_WHITE if hovered else C_GREEN
            pygame.draw.circle(screen, fill, (cx, cy), ind_r)
            arrow = font_small.render("↓", True, C_BLACK)
            screen.blit(arrow, arrow.get_rect(center=(cx, cy)))
        else:
            pygame.draw.circle(screen, C_GREY, (cx, cy), ind_r, 2)

    for col in range(COLS):
        cx = BOARD_LEFT + col * CELL + CELL // 2
        cy = POP_TOP + POP_ZONE_H // 2

        if col in valid_pops:
            hovered = (col == hover_col and hover_zone == "pop")
            fill    = C_WHITE if hovered else C_GREEN
            pygame.draw.circle(screen, fill, (cx, cy), ind_r)
            arrow = font_small.render("↑", True, C_BLACK)
            screen.blit(arrow, arrow.get_rect(center=(cx, cy)))


def draw_status(screen, state, font_status, extra_msg=None):
    name  = "Yellow (X)" if state.current_player == PLAYER_1 else "Purple (O)"
    color = C_P1          if state.current_player == PLAYER_1 else C_P2

    prefix = font_status.render("Turn: ", True, C_TEXT)
    player = font_status.render(name,     True, color)

    total_w = prefix.get_width() + player.get_width()
    x = (SCREEN_W - total_w) // 2
    screen.blit(prefix, (x, STATUS_Y))
    screen.blit(player, (x + prefix.get_width(), STATUS_Y))

    if extra_msg:
        hint = font_status.render(extra_msg, True, C_TEXT)
        screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, STATUS_Y + 34)))


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


# ═══════════════════════════════════════════════════════════════════════════════
#  Menus
# ═══════════════════════════════════════════════════════════════════════════════

def menu_main(screen, bg, img_btn):
    f_title = pygame.font.Font(FONT1_PATH, 100)
    f_sel   = pygame.font.Font(FONT2_PATH, 30)
    f_btn   = pygame.font.Font(FONT2_PATH, 23)

    btns = [
        Button(img_btn[0], (640, 310), "Human vs Human",      f_btn),
        Button(img_btn[1], (640, 375), "Human vs Computer",    f_btn),
        Button(img_btn[1], (640, 440), "Computer vs Human",    f_btn),
        Button(img_btn[2], (640, 505), "Computer vs Computer", f_btn),
    ]

    while True:
        screen.blit(bg, (0, 0))

        t1 = f_title.render("POP", True, C_BASE)
        t2 = f_title.render("OUT", True, C_TEXT)
        tw = t1.get_width() + t2.get_width()
        bx = (SCREEN_W - tw) // 2
        screen.blit(t1, (bx, 55))
        screen.blit(t2, (bx + t1.get_width(), 55))

        sel = f_sel.render("Select a game mode", True, C_TEXT)
        screen.blit(sel, sel.get_rect(center=(640, 255)))

        mp = pygame.mouse.get_pos()
        for btn in btns:
            btn.draw(screen, mp)
        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for i, btn in enumerate(btns):
                    if btn.hit(mp):
                        return i + 1


def menu_difficulty(screen, bg, img_btn, player_num):
    f_title = pygame.font.Font(FONT2_PATH, 32)
    f_sub   = pygame.font.Font(FONT2_PATH, 22)
    f_btn   = pygame.font.Font(FONT2_PATH, 23)

    btns = [
        Button(img_btn[0], (640, 320), "Easy   (0.5s)", f_btn),
        Button(img_btn[1], (640, 390), "Medium (1.0s)", f_btn),
        Button(img_btn[2], (640, 460), "Hard   (2.0s)", f_btn),
    ]
    back = Button(img_btn[2], (180, 650), "Back", f_btn, C_HOVER, C_P1, size=(150, 40))

    while True:
        screen.blit(bg, (0, 0))

        title = f_title.render(f"Player {player_num}  ·  MCTS Difficulty", True, C_TEXT)
        screen.blit(title, title.get_rect(center=(640, 210)))
        hint = f_sub.render("Higher difficulty = stronger moves, but slower", True, C_BASE)
        screen.blit(hint, hint.get_rect(center=(640, 258)))

        mp = pygame.mouse.get_pos()
        for btn in btns:
            btn.draw(screen, mp)
        back.draw(screen, mp)
        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if back.hit(mp):
                    return None
                for i, btn in enumerate(btns):
                    if btn.hit(mp):
                        return i + 1


def menu_post_game(screen, bg, img_btn, winner):
    f_win = pygame.font.Font(FONT1_PATH, 68)
    f_btn = pygame.font.Font(FONT2_PATH, 23)

    if winner == PLAYER_1:
        label, color = "Yellow Wins!", C_P1
    elif winner == PLAYER_2:
        label, color = "Red Wins!", C_P2
    else:
        label, color = "Draw!", C_TEXT

    btns = [
        Button(img_btn[0], (640, 390), "Play Again", f_btn),
        Button(img_btn[1], (640, 460), "Main Menu",  f_btn),
        Button(img_btn[2], (640, 530), "Quit",       f_btn),
    ]

    while True:
        screen.blit(bg, (0, 0))
        title = f_win.render(label, True, color)
        screen.blit(title, title.get_rect(center=(640, 255)))

        mp = pygame.mouse.get_pos()
        for btn in btns:
            btn.draw(screen, mp)
        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if btns[0].hit(mp): return "again"
                if btns[1].hit(mp): return "menu"
                if btns[2].hit(mp):
                    pygame.quit(); sys.exit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Move getters
# ═══════════════════════════════════════════════════════════════════════════════

def get_human_move(screen, bg, state, font_small, font_status, back_btn):
    valid_moves = state.get_valid_moves()
    valid_drops = {col for t, col in valid_moves if t == "drop"}
    valid_pops  = {col for t, col in valid_moves if t == "pop"}

    hint = "↓ Click above to Drop  |  ↑ Click below to Pop"

    while True:
        mp = pygame.mouse.get_pos()
        hover_col, hover_zone = get_col_and_zone(*mp)

        screen.blit(bg, (0, 0))
        draw_board(screen, state, hover_col, hover_zone, font_small)
        draw_status(screen, state, font_status, hint)
        draw_back_btn(screen, back_btn, mp)
        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                # botão de voltar ao menu
                if back_btn.hit(ev.pos):
                    return None

                col, zone = get_col_and_zone(*ev.pos)
                if col == -1:
                    continue

                if zone in ("drop", "board") and col in valid_drops:
                    return ("drop", col)

                if zone == "pop" and col in valid_pops:
                    return ("pop", col)


def get_computer_move(screen, bg, state, difficulty,
                      font_small, font_status, font_thinking, back_btn):
    mp = pygame.mouse.get_pos()
    screen.blit(bg, (0, 0))
    draw_board(screen, state, -1, None, font_small)
    draw_status(screen, state, font_status)
    draw_back_btn(screen, back_btn, mp)

    think = font_thinking.render("Thinking…", True, C_TEXT)
    screen.blit(think, think.get_rect(center=(SCREEN_W // 2, STATUS_Y + 38)))
    pygame.display.flip()

    for ev in pygame.event.get(pygame.QUIT):
        pygame.quit(); sys.exit()

    params = DIFFICULTY[difficulty]
    mcts   = MCTSAlgo(
        max_simulations=params["max_simulations"],
        max_time=params["max_time"]
    )
    move, _ = mcts.search(state)
    return move


# ═══════════════════════════════════════════════════════════════════════════════
#  Core game loop
# ═══════════════════════════════════════════════════════════════════════════════

def game_loop(screen, bg, img_btn, tipo, diff1, diff2):
    tracemalloc.start()
    t_start = time.time()

    f_small    = pygame.font.Font(FONT2_PATH, 22)
    f_status   = pygame.font.Font(FONT2_PATH, 26)
    f_thinking = pygame.font.Font(FONT2_PATH, 32)
    f_back     = pygame.font.Font(FONT2_PATH, 20)

    back_btn = make_back_btn(img_btn, f_back)

    state      = PopOutState()
    move_count = 0

    while not state.is_game_over():
        move_count += 1
        if move_count > MAX_MOVES_CVC:
            break

        current  = state.current_player
        is_human = (
            tipo == 1 or
            (tipo == 2 and current == PLAYER_1) or
            (tipo == 3 and current == PLAYER_2)
        )

        for ev in pygame.event.get(pygame.QUIT):
            pygame.quit(); sys.exit()

        if is_human:
            move = get_human_move(screen, bg, state, f_small, f_status, back_btn)
        else:
            diff = diff1 if current == PLAYER_1 else diff2
            move = get_computer_move(
                screen, bg, state, diff, f_small, f_status, f_thinking, back_btn
            )

        # jogador clicou em "Menu" → abandona o jogo
        if move is None:
            tracemalloc.stop()
            return None

        state = state.make_move(move)

        mp = pygame.mouse.get_pos()
        screen.blit(bg, (0, 0))
        draw_board(screen, state, -1, None, f_small)
        draw_status(screen, state, f_status)
        draw_back_btn(screen, back_btn, mp)
        pygame.display.flip()

        if tipo == 4:
            time.sleep(0.4)

    # ── Final board ────────────────────────────────────────────────────────────
    screen.blit(bg, (0, 0))
    draw_board(screen, state, -1, None, f_small)
    draw_status(screen, state, f_status)
    pygame.display.flip()
    time.sleep(1.0)

    # ── Stats ──────────────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    print(f"\n── Game stats ──────────────────────────────")
    print(f"  Moves played : {move_count}")
    print(f"  Time elapsed : {elapsed:.2f}s")
    print(f"  CPU usage    : {psutil.cpu_percent():.1f}%")
    print(f"  RAM usage    : {psutil.virtual_memory()[2]:.1f}%")
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"  Memory peak  : {peak_mem / 1024 / 1024:.2f} MB")
    print(f"────────────────────────────────────────────")

    return state.get_winner()


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("PopOut")

    bg      = load_bg()
    img_btn = load_btn_images()

    last_tipo  = None
    last_diff1 = None
    last_diff2 = None
    replay     = False

    while True:
        if replay and last_tipo is not None:
            tipo  = last_tipo
            diff1 = last_diff1
            diff2 = last_diff2
        else:
            tipo = menu_main(screen, bg, img_btn)
            diff1 = diff2 = 2

            if tipo in (3, 4):
                d = menu_difficulty(screen, bg, img_btn, 1)
                if d is None:
                    continue
                diff1 = d

            if tipo in (2, 4):
                d = menu_difficulty(screen, bg, img_btn, 2)
                if d is None:
                    continue
                diff2 = d

            last_tipo  = tipo
            last_diff1 = diff1
            last_diff2 = diff2

        winner = game_loop(screen, bg, img_btn, tipo, diff1, diff2)

        # se voltou ao menu sem terminar o jogo
        if winner is None:
            replay = False
            continue

        decision = menu_post_game(screen, bg, img_btn, winner)
        replay   = (decision == "again")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit()
