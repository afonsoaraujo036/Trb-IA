import math
import time
import os
import random
import copy
from os import system
import sys, pygame
import psutil
import tracemalloc
pygame.init()

# O que faz: cria o ficheiro connect4_moves.csv (na mesma pasta de ConnectFour.py) e escreve só uma vez o cabeçalho c0,…,c41,player,move.

import csv

# Define a pasta e o nome do CSV na mesma pasta do script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE  = os.path.join(SCRIPT_DIR, 'connect4_pairs.csv')

# Se o CSV não existir, cria-o e escreve o header
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        header = [f'c{i}' for i in range(42)] + ['move']
        writer.writerow(header)



# Pega o diretório onde está este arquivo .py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define assets como subpasta de BASE_DIR
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


#adicionei a partir daqui

# Melhorias de estética:
# - Fundo personalizado
# - Fontes atualizadas
# - Botões com cores personalizadas

# Cores e fontes
BACKGROUND_IMAGE = os.path.join(ASSETS_DIR, "Background.png")
FONT_MAIN_MENU = os.path.join(ASSETS_DIR, "font1.otf")
FONT_OTHER = os.path.join(ASSETS_DIR, "font2.otf")
COLOR_BASE = (239, 222, 198)  # #efdec6
COLOR_HOVER = (100, 12, 63)  # #640c3f
COLOR_TEXT = (251, 90, 72)  # #fb5a48
COLOR_NEW = (208, 173, 45)  # #d0ad2d



# Carregar a imagem de fundo dos botões
# Carrega dinamicamente Rect1.png, Rect2.png e Rect3.png
IMG_BUTTONS = [
    pygame.image.load(os.path.join(ASSETS_DIR, f"Rect{i}.png"))
    for i in range(1, 4)
]

# Se você ainda precisar de variáveis nomeadas:
IMG_BUTTON1, IMG_BUTTON2, IMG_BUTTON3 = IMG_BUTTONS



# Função para carregar a imagem de fundo
def carregar_fundo():
    fundo = pygame.image.load(BACKGROUND_IMAGE)
    fundo = pygame.transform.scale(fundo, (1280, 720))  
    return fundo

# Função para desenhar o fundo
def desenhar_fundo(screen, fundo):
    screen.blit(fundo, (0, 0))


class Button():
    def __init__(self, image, pos, text_input, font, base_color, hovering_color, size=(300, 50)):
        self.image = image
        self.x_pos = pos[0]
        self.y_pos = pos[1]
        self.font = font
        self.base_color, self.hovering_color = base_color, hovering_color
        self.text_input = text_input
        self.text = self.font.render(self.text_input, True, self.base_color)
        self.size = size

        # Ajustar o tamanho da imagem para caber no botão
        if self.image is not None:
            self.image = pygame.transform.scale(self.image, self.size)  
        else:
            self.image = self.text

        self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

    def update(self, screen):
        if self.image is not None:
            screen.blit(self.image, self.rect)
        screen.blit(self.text, self.text_rect)

    def checkForInput(self, position):
        return self.rect.collidepoint(position)

    def changeColor(self, position):
        if self.rect.collidepoint(position):
            self.text = self.font.render(self.text_input, True, self.hovering_color)
        else:
            self.text = self.font.render(self.text_input, True, self.base_color)




def menu_tipo_jogo(screen):
    font_titulo = pygame.font.Font(FONT_MAIN_MENU, 110)
    font_menu = pygame.font.Font(FONT_MAIN_MENU, 50) 
    font_select = pygame.font.Font(FONT_OTHER, 32)
    font_botoes = pygame.font.Font(FONT_OTHER, 25)
    fundo = carregar_fundo()

    botoes = [
        Button(IMG_BUTTON1, (640, 310), "Human VS Human", font_botoes, COLOR_BASE, COLOR_HOVER),
        Button(IMG_BUTTON2, (640, 375), "Human VS Computer", font_botoes, COLOR_BASE, COLOR_HOVER),
        Button(IMG_BUTTON2, (640, 440), "Computer VS Human", font_botoes, COLOR_BASE, COLOR_HOVER),
        Button(IMG_BUTTON3, (640, 505), "Computer VS Computer", font_botoes, COLOR_BASE, COLOR_HOVER),
        # Botão "Back" com tamanho personalizado
        Button(IMG_BUTTON3, (200, 650), "Back", font_botoes, COLOR_HOVER, COLOR_NEW, size=(150, 40))
    ]

    while True:
        desenhar_fundo(screen, fundo)
        
        # Título principal
        titulo_main = font_titulo.render("MAIN", True, COLOR_BASE)
        titulo_main_rect = titulo_main.get_rect(center=(640, 80))
        screen.blit(titulo_main, titulo_main_rect)

        titulo_menu = font_menu.render("MENU", True, COLOR_BASE)
        titulo_menu_rect = titulo_menu.get_rect(center=(640, 160))
        screen.blit(titulo_menu, titulo_menu_rect)

        # Subtítulo
        titulo_select = font_select.render("Select a game mode", True, COLOR_TEXT)
        titulo_select_rect = titulo_menu.get_rect(center=(567, 250))
        screen.blit(titulo_select, titulo_select_rect)

        # Atualizar botões
        mouse_pos = pygame.mouse.get_pos()
        for botao in botoes:
            botao.changeColor(mouse_pos)
            botao.update(screen)

        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, botao in enumerate(botoes):
                    if botao.checkForInput(mouse_pos):
                        return i + 1

        pygame.display.update()



    

def menu_estrategia(screen, jogador):
    font_titulo = pygame.font.Font(FONT_MAIN_MENU, 48)
    font_botoes = pygame.font.Font(FONT_OTHER, 25)
    font_select = pygame.font.Font(FONT_OTHER, 32)
    fundo = carregar_fundo()

    titulo_txt = f"Player Strategy {jogador}"

    botoes = [
    Button(IMG_BUTTON1, (640, 310), "Minimax", font_botoes, COLOR_BASE, COLOR_HOVER),
    Button(IMG_BUTTON2, (640, 375), "Alfa-Beta", font_botoes, COLOR_BASE, COLOR_HOVER),
    Button(IMG_BUTTON2, (640, 440), "Monte Carlo", font_botoes, COLOR_BASE, COLOR_HOVER),
    Button(IMG_BUTTON3, (200, 650), "Back", font_botoes, COLOR_HOVER, COLOR_NEW, size=(150, 40))
]

    while True:
        desenhar_fundo(screen, fundo)
        titulo = font_select.render(titulo_txt, True, COLOR_TEXT)
        titulo_rect = titulo.get_rect(center=(640, 200))
        screen.blit(titulo, titulo_rect)


        mouse_pos = pygame.mouse.get_pos()
        for botao in botoes:
            botao.changeColor(mouse_pos)
            botao.update(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, botao in enumerate(botoes):
                    if botao.checkForInput(mouse_pos):
                        return i + 1

        pygame.display.update()


def menu_dificuldade(screen, jogador):
    font_titulo = pygame.font.Font(FONT_MAIN_MENU, 48)
    font_botoes = pygame.font.Font(FONT_OTHER, 25)
    font_select = pygame.font.Font(FONT_OTHER, 32)
    fundo = carregar_fundo()

    titulo_txt = f"Player Difficulty {jogador}"
    
    botoes = [
        Button(IMG_BUTTON1, (640, 310), "Easy", font_botoes, COLOR_BASE, COLOR_HOVER),
        Button(IMG_BUTTON2, (640, 375), "Intermediate", font_botoes, COLOR_BASE, COLOR_HOVER),
        Button(IMG_BUTTON2, (640, 440), "Hard", font_botoes, COLOR_BASE, COLOR_HOVER),
        Button(IMG_BUTTON3, (200, 650), "Back", font_botoes, COLOR_HOVER, COLOR_NEW, size=(150, 40))
    ]

    while True:
        desenhar_fundo(screen, fundo)
        titulo = font_select.render(titulo_txt, True, COLOR_TEXT)
        titulo_rect = titulo.get_rect(center=(640, 200))
        screen.blit(titulo, titulo_rect)

        mouse_pos = pygame.mouse.get_pos()
        for botao in botoes:
            botao.changeColor(mouse_pos)
            botao.update(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, botao in enumerate(botoes):
                    if botao.checkForInput(mouse_pos):
                        return i + 1

        pygame.display.update()

def menu_pos_jogo(screen, vencedor):
    font_titulo = pygame.font.Font(FONT_MAIN_MENU, 48)
    font_botoes = pygame.font.Font(FONT_OTHER, 25)
    fundo = carregar_fundo()

    # Determinar o texto e a cor com base no vencedor
    if vencedor == 1:
        titulo_text = "Winner: Yellow"
        titulo_color = COLOR_NEW  # Amarelo
    elif vencedor == 2:
        titulo_text = "Winner: Purple"
        titulo_color = COLOR_HOVER  # Roxo
    else:
        titulo_text = "Winner: Draw"
        titulo_color = COLOR_TEXT  # Cor padrão para empate

    botoes = [
        Button(None, (640, 350), "Play Again", font_botoes, COLOR_TEXT, COLOR_HOVER),
        Button(None, (640, 400), "Main Menu", font_botoes, COLOR_TEXT, COLOR_HOVER),
        Button(None, (640, 500), "Quit", font_botoes, COLOR_TEXT, COLOR_HOVER)
    ]

    while True:
        desenhar_fundo(screen, fundo)
        
        # Renderizar o texto com a cor correta
        texto = font_botoes.render(titulo_text, True, titulo_color)
        screen.blit(texto, (640 - texto.get_width() // 2, 230))

        # Atualizar botões
        mouse_pos = pygame.mouse.get_pos()
        for botao in botoes:
            botao.changeColor(mouse_pos)
            botao.update(screen)

        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if botoes[0].checkForInput(mouse_pos):
                    return "reiniciar"
                elif botoes[1].checkForInput(mouse_pos):
                    return "menu"
                elif botoes[2].checkForInput(mouse_pos):
                    pygame.quit()
                    sys.exit()

        pygame.display.update()



def menu_confirmar_jogo(screen):
    font_titulo = pygame.font.Font(FONT_MAIN_MENU, 48)
    font_botoes = pygame.font.Font(FONT_OTHER, 25)
    fundo = carregar_fundo()

    titulo = font_botoes.render("Are you ready to start the game?", True, COLOR_TEXT)
    titulo_rect = titulo.get_rect(center=(650, 230))

    botoes = [
        Button(None, (640, 350), "Play", font_botoes, COLOR_TEXT, COLOR_HOVER),
        Button(None, (640, 400), "Quit", font_botoes, COLOR_TEXT, COLOR_HOVER),
        Button(None, (640, 550), "Back", font_botoes, COLOR_TEXT, COLOR_HOVER)
    ]

    while True:
        desenhar_fundo(screen, fundo)
        screen.blit(titulo, titulo_rect)

        mouse_pos = pygame.mouse.get_pos()
        for botao in botoes:
            botao.changeColor(mouse_pos)
            botao.update(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if botoes[0].checkForInput(mouse_pos):
                    return True
                elif botoes[1].checkForInput(mouse_pos):
                    pygame.quit()
                    sys.exit()
                elif botoes[2].checkForInput(mouse_pos):
                    return "voltar"

        pygame.display.update()




# até aqui

class ConnectFourState:
    def __init__(self, board, vazios, current_player, last_move=None):
        # guarda cópias para não partilhar referência
        self.board = [row[:] for row in board]
        self.vazios = list(vazios)
        self.current_player = current_player
        self.last_move = last_move

    def get_current_player(self):
        return self.current_player

    def get_legal_moves(self):
        # devolve todas as colunas que ainda têm espaço em cima
        return [col for col in range(7) if self.vazios[col] >= 0]

    def make_move(self, move):
        new_board = [row[:] for row in self.board]
        new_vazios = list(self.vazios)
        row = new_vazios[move]
        new_board[row][move] = self.current_player
        new_vazios[move] -= 1
        next_player = Metodos.outroJog(self.current_player)
        return ConnectFourState(new_board, new_vazios, next_player, last_move=move)

    def is_game_over(self):
        # usa o teu método estático para detetar vitória/empate
        return Metodos.fim_jogo(self.board, self.current_player) != -1

    def get_winner(self):
        # devolve 0,1 ou 2 conforme o jogo acabou
        return Metodos.fim_jogo(self.board, self.current_player)


# Pure Monte Carlo Tree Search Implementation
class Node:
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried_moves = state.get_legal_moves()

    def select_child(self):
        # UCB1 formula for selection
        C = math.sqrt(2)  # Exploration parameter
        choices = [(child, (child.wins / child.visits) + C * math.sqrt(math.log(self.visits) / child.visits)) 
                  for child in self.children if child.visits > 0]
        if not choices:
            return random.choice(self.children) if self.children else None
        return max(choices, key=lambda x: x[1])[0]

    def expand(self):
        if not self.untried_moves:
            return None
        move = random.choice(self.untried_moves)
        self.untried_moves.remove(move)
        new_state = self.state.make_move(move)
        child = Node(new_state, self)
        self.children.append(child)
        return child

    def is_terminal(self):
        return self.state.is_game_over()

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def update(self, result):
        self.visits += 1
        self.wins += result

class PureMCTS:    
    def __init__(self, state, player, time_limit=2):
        self.root_state = state
        self.player = player
        self.time_limit = time_limit
        self.max_iterations = 1000  # Number of MCTS iterations

    def get_best_move(self):
        root = Node(self.root_state)
        
        end_time = time.time() + self.time_limit  # Use configured time limit
        iterations = 0
        
        while time.time() < end_time and iterations < self.max_iterations:
            iterations += 1
            
            # 1. Selection
            node = root
            while not node.is_terminal() and node.is_fully_expanded():
                child = node.select_child()
                if not child:
                    break
                node = child

            # 2. Expansion
            if not node.is_terminal() and node.untried_moves:
                node = node.expand()
                if not node:
                    continue

            # 3. Simulation
            result = self.simulate(node.state)

            # 4. Backpropagation
            while node:
                node.update(result)
                node = node.parent

        # Choose the move that led to the most visited child
        if not root.children:
            legal_moves = root.state.get_legal_moves()
            return random.choice(legal_moves) if legal_moves else None
        
        # … blocos de Selection, Expansion, Simulation, Backpropagation
        best_child = max(root.children, key=lambda c: c.visits)



        
        # ─── Antes de devolver o movimento, regista o par (estado, move) ───
        flat_state = sum(self.root_state.board, [])              
        # só grava o movimento, não o jogador
        row        = flat_state + [best_child.state.last_move]
        with open(CSV_FILE, 'a', newline='') as f:
            csv.writer(f).writerow(row)


        # Finalmente, devolve o movimento
        return best_child.state.last_move


    def simulate(self, state):
        current_state = copy.deepcopy(state)
        
        while not current_state.is_game_over():
            legal_moves = current_state.get_legal_moves()
            if not legal_moves:
                break
            move = random.choice(legal_moves)
            current_state = current_state.make_move(move)
        
        winner = current_state.get_winner()
        if winner == 0:  # Draw
            return 0.5
        return 1.0 if winner == self.player else 0.0

    @staticmethod  
    def get_opponent(player):
        return 3 - player  # 1 -> 2, 2 -> 1
        

#Constantes utilizadas
class Constantes:
    BLACK = (0,0,0)
    WHITE = (255,255,255)
    RED = (255,0,0)
    GREEN = (0,255,0)
    YELLOW = (255,255,0)
    BLUE = (0,0,255)
    COLOR_BASE = (239, 222, 198)  # #efdec6
    COLOR_HOVER = (100, 12, 63)  # #640c3f
    COLOR_TEXT = (251, 90, 72)  # #fb5a48
    COLOR_NEW = (208, 173, 45)  # #d0ad2d   

#Operadores
class movimento:
    def __init__(self, x = 0, y = 0, jog = 0):
        self.x = x #coordenadas
        self.y = y
        self.jog = jog

#Estado do Jogo/Tabuleiro
class Metodos:
    nMovs = 0
    vazios = [5, 5, 5, 5, 5, 5, 5]
    screen = pygame.Surface((0, 0))
    screen_width, screen_height = 1280, 720
    sq = min(screen_width // 7, screen_height // 6)  # Tamanho da célula baseado na altura

    #Faz a cópia de um tabuleiro
    @staticmethod
    def copia(tabuleiro):
       return copy.deepcopy(tabuleiro)
    
    @staticmethod
    def outroJog(jog):
        # se for 1, devolve 2; senão devolve 1
        return 2 if jog == 1 else 1



    @staticmethod
    def assinala(tabuleiro, tipo):
        # tipo==1: branco; 0: apaga (preto)
        cor = COLOR_TEXT if tipo==1 else Constantes.BLACK
        margin_x = (Metodos.screen_width  - 7*Metodos.sq)//2
        margin_y = (Metodos.screen_height - 6*Metodos.sq)//2

        for col in range(7):
            row = Metodos.vazios[col]
            if row >= 0:   # ainda cabe nesta coluna
                cx = margin_x + col*Metodos.sq + Metodos.sq//2
                cy = margin_y + row*Metodos.sq + Metodos.sq//2
                pygame.draw.circle(
                    Metodos.screen, cor,
                    (cx, cy),
                    (Metodos.sq//2)-2, 2
                )



    @staticmethod
    def fim_jogo(tabuleiro, jog):
        # 1) horizontal
        for row in range(6):
            for col in range(4):
                seg = [tabuleiro[row][col + i] for i in range(4)]
                if seg.count(1) == 4: return 1
                if seg.count(2) == 4: return 2

        # 2) vertical
        for col in range(7):
            for row in range(3):
                seg = [tabuleiro[row + i][col] for i in range(4)]
                if seg.count(1) == 4: return 1
                if seg.count(2) == 4: return 2

        # 3) diagonal “\”
        for row in range(3):
            for col in range(4):
                seg = [tabuleiro[row + i][col + i] for i in range(4)]
                if seg.count(1) == 4: return 1
                if seg.count(2) == 4: return 2

        # 4) diagonal “/”
        for row in range(3, 6):
            for col in range(4):
                seg = [tabuleiro[row - i][col + i] for i in range(4)]
                if seg.count(1) == 4: return 1
                if seg.count(2) == 4: return 2

        # 5) continua?
        for r in tabuleiro:
            if 0 in r:
                return -1   # ainda há casas vazias

        return 0  # empate


    # Mostra o tabuleiro em modo grafico
    @staticmethod
    
    def mostra_tabul(tabuleiro):
        
        Metodos.screen.fill(COLOR_BASE)

        margin_x = (Metodos.screen_width - (7 * Metodos.sq)) // 2
        margin_y = (Metodos.screen_height - (6 * Metodos.sq)) // 2

        # pinta o “fundo” do tabuleiro na cor #efdec6
        pygame.draw.rect(
            Metodos.screen,
            COLOR_BASE,                    # (239,222,198) == #efdec6
            (margin_x, margin_y, 
            7 * Metodos.sq, 6 * Metodos.sq)
        )

        for i in range(6):
            for j in range(7):
                cor = Constantes.BLACK
                pygame.draw.circle(
                    Metodos.screen, cor,
                    (margin_x + j * Metodos.sq + Metodos.sq // 2, margin_y + i * Metodos.sq + Metodos.sq // 2),
                    (Metodos.sq // 2) - 2
                )
                if tabuleiro[i][j] == 1 or tabuleiro[i][j] == 2:
                    cor = Constantes.COLOR_NEW if tabuleiro[i][j] == 1 else Constantes.COLOR_HOVER
                    pygame.draw.circle(
                        Metodos.screen, cor,
                        (margin_x + j * Metodos.sq + Metodos.sq // 2, margin_y + i * Metodos.sq + Metodos.sq // 2),
                        (Metodos.sq // 2) - 2
                    )

        Metodos.assinala(tabuleiro, 1)   # desenha os círculos brancos nas colunas válidas

        pygame.display.flip()





    # Pede ao utlizador que escolha um dos modos de jogo possíveis
    @staticmethod
    def tipo():
        return int(input("Jogo Connect Four\nEscolha o modo de jogo: \n1-Hum/Hum, 2-Hum/Computador, 3-Computador/Hum, 4-Computador/Computador\n"))

    # Pede ao utlizador que escolha uma das estrategias de jogo possíveis
    @staticmethod
    def tipo_jogo(jog):
        return int(input("\nEscolha a estratégia do jogador %d: \n1-Minimax, 2-Alfa-Beta, 3-MonteCarlo\n" %jog))

    # Pede ao utlizador que escolha a dificuldade do jogo
    @staticmethod
    def dificuldade(jog):
        return int(input("\nEscolha a dificuldade do jogador " + str(jog) + ": \n1-Fácil, 2-Intermédio, 3-Díficil\n")) #caso se tenha escolhido a opção 2, 3 ou 4


    # Finaliza o jogo indicando quem venceu ou se foi empate
    @staticmethod
    def finaliza(venc):
        Metodos.screen.fill(Constantes.BLACK)
        pygame.display.update()
        font = pygame.font.SysFont(None, 24)
        img = pygame.Surface((0,0))

        if venc == 0:
            print("Empate!!!\n")
            img = font.render("Empate!!!\n", True, Constantes.GREEN)
        elif venc == 1:
            print("Venceu o Jogador 1 - Amarelo!")
            img = font.render("Venceu o Jogador 1 - Amarelo!", True, Constantes.COLOR_NEW)
        else:
            print("Venceu o Jogador 2 - Vermelho!")
            img = font.render("Venceu o Jogador 2 - Vermelho!", True, Constantes.COLOR_HOVER)
        Metodos.screen.blit(img, (700/2-100, 700/2))
        pygame.display.update()

    # Indica se (x,y) está dentro do tabuleiro
    @staticmethod
    def dentro(x, y):
        return (x>=0 and x<=7-1 and y>=0 and y<=6-1)

    #indica se mov é um movimento valido
    @staticmethod
    def movimento_valido(mov):
        if not Metodos.dentro(mov.x, mov.y):
            return False #fora do tabuleiro
        if Metodos.vazios[mov.x]==mov.y:
            return True
        return False

    #Heurística
    def conta_pontos(tabuleiro, jogador):
        total_pontos = 0

        # Verifica se houve vitória
        if Metodos.fim_jogo(tabuleiro, jogador) != -1:
            if Metodos.fim_jogo(tabuleiro, jogador) == jogador:
                return 512
            elif Metodos.fim_jogo(tabuleiro, jogador) == Metodos.outroJog(jogador):
                return -512
            else:
                return 0

        # avalia segmentos na horizontal
        for linha in tabuleiro:
            for i in range(0, 4):
                segmento = linha[i:i+4]
                total_pontos += Metodos.avaliar_segmento(segmento, jogador)

        # avalia segmentos na vertical
        for coluna in range(0, 7):
            for i in range(0, 3):
                segmento = [tabuleiro[i][coluna], tabuleiro[i+1][coluna], tabuleiro[i+2][coluna], tabuleiro[i+3][coluna]]
                total_pontos += Metodos.avaliar_segmento(segmento, jogador)

        # avalia segmentos na diagonal \
        for i in range(0, 4):
            for j in range(0, 3):
                segmento = [tabuleiro[j][i], tabuleiro[j+1][i+1], tabuleiro[j+2][i+2], tabuleiro[j+3][i+3]]
                total_pontos += Metodos.avaliar_segmento(segmento, jogador)

        # avalia segmentos na diagonal /
        for i in range(0, 4):
            for j in range(3, 6):
                segmento = [tabuleiro[j][i], tabuleiro[j-1][i+1], tabuleiro[j-2][i+2], tabuleiro[j-3][i+3]]
                total_pontos += Metodos.avaliar_segmento(segmento, jogador)

        return total_pontos

    #Função de avaliação
    def avaliar_segmento(segmento, jogador):
        contador_jogador = segmento.count(jogador)
        contador_adversario = segmento.count(Metodos.outroJog(jogador))
        if contador_adversario == 0:
            if contador_jogador == 3:
                return +50
            elif contador_jogador == 2:
                return +10
            elif contador_jogador == 1:
                return +1
            else:
                return 0
        elif contador_jogador == 0:
            if contador_adversario == 3:
                return -50
            elif contador_adversario == 2:
                return -10
            elif contador_adversario == 1:
                return -1
            else:
                return 0
        else:
            return 0

    #Determina se o jogador ainda tem jogadas válidas
    @staticmethod
    def jogadas_validas():
        for i in range(7):
            if Metodos.vazios[i]!=-1:
                return True
        return False

    #retorna a lista com as posições possiveis em que se pode jogar
    def jogadas_possiveis(tabuleiro):
        lista = []
        for posicao in range(7):
            if tabuleiro[0][posicao] == 0:
                lista.append(posicao)
        return lista

    

    # Jogada do Humano
    
    def jogada_Humano(tabuleiro, jog):
        mov = movimento(0, 0, jog)
        px = 0
        py = 0
        condition = True
        margin_x = (Metodos.screen_width - (7 * Metodos.sq)) // 2
        margin_y = (Metodos.screen_height - (6 * Metodos.sq)) // 2

        while condition:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    px = (pos[0] - margin_x) // Metodos.sq
                    
                    # Verificação de limites da coluna
                    if px < 0 or px >= 7:
                        continue
                    
                    py = Metodos.vazios[px]  # Obter a próxima posição vazia na coluna
                    
                    if py < 0:
                        print("Coluna cheia, escolha outra.")
                        continue
                    
                    mov = movimento(px, py, jog)
                    
                    # Verificar se o movimento é válido
                    if Metodos.movimento_valido(mov):
                        tabuleiro[py][px] = jog
                        Metodos.vazios[px] -= 1
                        Metodos.mostra_tabul(tabuleiro)  # Atualiza o tabuleiro após a jogada
                        pygame.display.update()  # Atualiza a tela
                        condition = False
                        break
            pygame.display.update()
            time.sleep(0.1)
        
        @staticmethod
        def fim_jogo(tabuleiro, jog):
            # 1) horizontal
            for row in range(6):
                for col in range(4):
                    seg = [tabuleiro[row][col + i] for i in range(4)]
                    if seg.count(1) == 4: return 1
                    if seg.count(2) == 4: return 2

            # 2) vertical
            for col in range(7):
                for row in range(3):
                    seg = [tabuleiro[row + i][col] for i in range(4)]
                    if seg.count(1) == 4: return 1
                    if seg.count(2) == 4: return 2

            # 3) diagonal “\”
            for row in range(3):
                for col in range(4):
                    seg = [tabuleiro[row + i][col + i] for i in range(4)]
                    if seg.count(1) == 4: return 1
                    if seg.count(2) == 4: return 2

            # 4) diagonal “/”
            for row in range(3, 6):
                for col in range(4):
                    seg = [tabuleiro[row - i][col + i] for i in range(4)]
                    if seg.count(1) == 4: return 1
                    if seg.count(2) == 4: return 2

            # 5) continua?
            for r in tabuleiro:
                if 0 in r:
                    return -1   # ainda há vazios

            return 0  # empate



    #jogada minimax
    # Função para realizar a jogada do computador com Minimax
    def jogada_pc_minimax(tabuleiro, jog, dificuldade):
        bestmov = Metodos.minimax(jog, tabuleiro, dificuldade)
        if bestmov is not None and bestmov != -1:
            py = Metodos.vazios[bestmov]
            if py >= 0:
                tabuleiro[py][bestmov] = jog
                Metodos.vazios[bestmov] -= 1
                Metodos.mostra_tabul(tabuleiro)
                pygame.display.update()


    #retorna a melhor jogada possível com minimax
    def minimax(jog, tabuleiro, dificuldade):
        _ , move = Metodos.maximo(jog, tabuleiro, dificuldade, None)
        return move

    #função maximo para o minimax
    def maximo(jog, tabuleiro, dificuldade, move):
        if Metodos.fim_jogo(tabuleiro, jog)!=-1 or dificuldade==0:
            tabuleiro_cp = Metodos.copia(tabuleiro)
            py = Metodos.vazios[move]
            tabuleiro_cp[py][move] = jog
            return Metodos.conta_pontos(tabuleiro_cp, jog),move

        max_value = float("-inf")
        for s in Metodos.jogadas_possiveis(tabuleiro):
            tabuleiro_cp = Metodos.copia(tabuleiro)
            py = Metodos.vazios[s]
            tabuleiro_cp[py][s] = jog
            value, _ = Metodos.minimo(jog, tabuleiro_cp, dificuldade - 1, s)
            if  value>max_value:
                max_value=value
                move=s

        return max_value,move

    #função minimo para o minimax
    def minimo(jog, tabuleiro, dificuldade, move):
        if Metodos.fim_jogo(tabuleiro, jog)!=-1 or dificuldade==0:
            tabuleiro_cp = Metodos.copia(tabuleiro)
            py = Metodos.vazios[move]
            tabuleiro_cp[py][move] = jog
            return Metodos.conta_pontos(tabuleiro_cp, jog),move

        min_value = float("inf")
        for s in Metodos.jogadas_possiveis(tabuleiro):
            tabuleiro_cp = Metodos.copia(tabuleiro)
            py = Metodos.vazios[s]
            tabuleiro_cp[py][s] = jog
            value, _ = Metodos.maximo(jog, tabuleiro_cp, dificuldade - 1, s)
            if value<min_value:
                min_value=value
                move = s

        return min_value,move    #jogada minimax com corte alfa-beta
    def jogada_pc_alphabeta(tabuleiro, jog, dificuldade):
        bestmov = Metodos.alphabeta(jog, tabuleiro, dificuldade)
        if bestmov is not None and bestmov != -1:
            py = Metodos.vazios[bestmov]
            if py >= 0:
                tabuleiro[py][bestmov] = jog
                Metodos.vazios[bestmov] -= 1
                Metodos.mostra_tabul(tabuleiro)
                pygame.display.update()

    #retorna a melhor jogada possível com minimax com cortes alfa-beta
    def alphabeta(jog, tabuleiro, dificuldade):
        alfa = float("-inf")
        beta = float("inf")
        valor, move = Metodos.maximo_alphabeta(jog, tabuleiro, dificuldade, alfa, beta)
        return move

    #função maximo para o minimax com cortes alfa-beta
    def maximo_alphabeta(jog, tabuleiro, dificuldade, alfa, beta):
        # Verifica se é um estado terminal ou se atingiu a profundidade máxima
        if Metodos.fim_jogo(tabuleiro, jog) != -1 or dificuldade == 0:
            return Metodos.conta_pontos(tabuleiro, jog), None

        max_value = float("-inf")
        best_move = None
        possiveis_jogadas = Metodos.jogadas_possiveis(tabuleiro)

        for s in possiveis_jogadas:
            # Cria uma cópia do tabuleiro e faz a jogada
            tabuleiro_cp = Metodos.copia(tabuleiro)
            py = Metodos.vazios[s]
            tabuleiro_cp[py][s] = jog
            
            # Chama o nível mínimo com o outro jogador
            value, _ = Metodos.minimo_alphabeta(Metodos.outroJog(jog), tabuleiro_cp, dificuldade - 1, alfa, beta)
            
            if value > max_value:
                max_value = value
                best_move = s
            
            alfa = max(alfa, max_value)
            if beta <= alfa:  # Corte beta
                break

        return max_value, best_move

    #função minimo para o minimax com cortes alfa-beta
    def minimo_alphabeta(jog, tabuleiro, dificuldade, alfa, beta):
        # Verifica se é um estado terminal ou se atingiu a profundidade máxima
        if Metodos.fim_jogo(tabuleiro, jog) != -1 or dificuldade == 0:
            return Metodos.conta_pontos(tabuleiro, jog), None

        min_value = float("inf")
        best_move = None
        possiveis_jogadas = Metodos.jogadas_possiveis(tabuleiro)

        for s in possiveis_jogadas:
            # Cria uma cópia do tabuleiro e faz a jogada
            tabuleiro_cp = Metodos.copia(tabuleiro)
            py = Metodos.vazios[s]
            tabuleiro_cp[py][s] = jog
            
            # Chama o nível máximo com o outro jogador
            value, _ = Metodos.maximo_alphabeta(Metodos.outroJog(jog), tabuleiro_cp, dificuldade - 1, alfa, beta)
            
            if value < min_value:
                min_value = value
                best_move = s
            
            beta = min(beta, min_value)
            if beta <= alfa:  # Corte alfa
                break

        return min_value, best_move
    
    @staticmethod
    def jogada_pc_montecarlo(tabuleiro, jog, dificuldade):
        # Create initial state
        initial_state = ConnectFourState(tabuleiro, Metodos.vazios, jog)
        
        # Set time limit based on difficulty
        if dificuldade == 1:  # Easy
            time_limit = 1
        elif dificuldade == 2:  # Intermediate
            time_limit = 1.5
        else:  # Hard
            time_limit = 2
            
        # Initialize MCTS with appropriate time limit
        mcts = PureMCTS(initial_state, jog, time_limit)
        
        # Get best move
        bestmov = mcts.get_best_move()

        # Apply the move if valid
        if bestmov is not None:
            py = Metodos.vazios[bestmov]
            if py >= 0:
                tabuleiro[py][bestmov] = jog
                Metodos.vazios[bestmov] -= 1
                Metodos.mostra_tabul(tabuleiro)
                pygame.display.update()


    @staticmethod
    def mostrar_jogador_atual(screen, jog):
        font = pygame.font.Font(FONT_OTHER, 25)

        # Texto "Current Player:" com cor padrão
        texto_prefixo = "Current Player:"
        render_prefixo = font.render(texto_prefixo, True, COLOR_TEXT)

        # Texto com o nome do jogador e cor correspondente
        cor = COLOR_NEW if jog == 1 else COLOR_HOVER
        texto_jogador = "Yellow" if jog == 1 else "Purple"
        render_jogador = font.render(texto_jogador, True, cor)

        # Desenhar na tela: "Current Player:" e na linha seguinte o nome do jogador
        screen.blit(render_prefixo, (20, 20))
        screen.blit(render_jogador, (20, 50))  # Ajuste de posição para ficar na linha seguinte



# GameSettings class for storing game configuration
class GameSettings:
    def __init__(self):
        self.tipo = 0
        self.estrategia1 = 0
        self.estrategia2 = 0
        self.dificuldade1 = 0
        self.dificuldade2 = 0

    def copy_from(self, other):
        if other:
            self.tipo = other.tipo
            self.estrategia1 = other.estrategia1
            self.estrategia2 = other.estrategia2
            self.dificuldade1 = other.dificuldade1
            self.dificuldade2 = other.dificuldade2

    def reset(self):
        self.tipo = 0
        self.estrategia1 = 0
        self.estrategia2 = 0
        self.dificuldade1 = 0
        self.dificuldade2 = 0

# Função principal 
# Função principal corrigida
def main():
    tracemalloc.start()
    settings = GameSettings()
    last_settings = None
    resultado = None
    
    # Inicialização da tela
    screen_width, screen_height = 1280, 720
    Metodos.screen = pygame.display.set_mode((screen_width, screen_height))
    Metodos.screen_width = screen_width
    Metodos.screen_height = screen_height
    Metodos.sq = min(screen_width // 7, screen_height // 6)
    pygame.display.set_caption('Connect Four')

    while True:
        # Reinicializa variáveis de controle e estado do jogo
        Metodos.vazios = [5, 5, 5, 5, 5, 5, 5]
        Metodos.nMovs = 0
        jog = 0
        fim = -1
        tabuleiro = [[0] * 7 for _ in range(6)]
        
        # Se for "Play Again", use as configurações anteriores
        if resultado == "reiniciar" and last_settings is not None:
            settings.copy_from(last_settings)
            tipo = settings.tipo
            estrategia1 = settings.estrategia1
            estrategia2 = settings.estrategia2
            dificuldade1 = settings.dificuldade1
            dificuldade2 = settings.dificuldade2
        else:
            # Escolha do tipo de jogo e estratégias
            settings.reset()
            tipo = menu_tipo_jogo(Metodos.screen)
            if tipo == 5:  # Botão Back
                continue
            
            settings.tipo = tipo
            estrategia1 = estrategia2 = dificuldade1 = dificuldade2 = 0

            if tipo == 2:
                estrategia2 = menu_estrategia(Metodos.screen, 2)
                if estrategia2 == 4:
                    continue
                dificuldade2 = menu_dificuldade(Metodos.screen, 2)
                if dificuldade2 == 4:
                    continue
                settings.estrategia2 = estrategia2
                settings.dificuldade2 = dificuldade2

            elif tipo == 3:
                estrategia1 = menu_estrategia(Metodos.screen, 1)
                if estrategia1 == 4:
                    continue
                dificuldade1 = menu_dificuldade(Metodos.screen, 1)
                if dificuldade1 == 4:
                    continue
                settings.estrategia1 = estrategia1
                settings.dificuldade1 = dificuldade1

            elif tipo == 4:
                estrategia1 = menu_estrategia(Metodos.screen, 1)
                if estrategia1 == 4:
                    continue
                dificuldade1 = menu_dificuldade(Metodos.screen, 1)
                if dificuldade1 == 4:
                    continue
                estrategia2 = menu_estrategia(Metodos.screen, 2)
                if estrategia2 == 4:
                    continue
                dificuldade2 = menu_dificuldade(Metodos.screen, 2)
                if dificuldade2 == 4:
                    continue
                settings.estrategia1 = estrategia1
                settings.dificuldade1 = dificuldade1
                settings.estrategia2 = estrategia2
                settings.dificuldade2 = dificuldade2

        # Store the current settings for potential "Play Again"
        last_settings = GameSettings()
        last_settings.copy_from(settings)

        # Confirmar início do jogo
        iniciar = menu_confirmar_jogo(Metodos.screen)
        if iniciar != True:
            continue

        # Game loop
        inicio = time.time()
        condition = True

        while condition:
            Metodos.nMovs += 1
            jog = Metodos.outroJog(jog)

            # Atualiza o tabuleiro e o jogador atual na tela
            Metodos.mostra_tabul(tabuleiro)
            Metodos.mostrar_jogador_atual(Metodos.screen, jog)
            pygame.display.update()

            # Verifica eventos e ações do jogador
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # Escolha da jogada conforme o modo de jogo
            if tipo == 1:
                Metodos.jogada_Humano(tabuleiro, jog)
                Metodos.mostra_tabul(tabuleiro)
                pygame.display.update()

            elif tipo == 2:
                if jog == 1:
                    Metodos.jogada_Humano(tabuleiro, jog)
                    Metodos.mostra_tabul(tabuleiro)
                    pygame.display.update()
                else:
                    if estrategia2 == 1:
                        Metodos.jogada_pc_minimax(tabuleiro, jog, dificuldade2)
                    elif estrategia2 == 2:
                        Metodos.jogada_pc_alphabeta(tabuleiro, jog, dificuldade2)
                    elif estrategia2 == 3:
                        Metodos.jogada_pc_montecarlo(tabuleiro, jog, dificuldade2)
                    # Atualiza o tabuleiro após a jogada do computador
                    Metodos.mostra_tabul(tabuleiro)
                    pygame.display.update()

            elif tipo == 3:
                if jog == 1:
                    if estrategia1 == 1:
                        Metodos.jogada_pc_minimax(tabuleiro, jog, dificuldade1)
                    elif estrategia1 == 2:
                        Metodos.jogada_pc_alphabeta(tabuleiro, jog, dificuldade1)
                    elif estrategia1 == 3:
                        Metodos.jogada_pc_montecarlo(tabuleiro, jog, dificuldade1)
                    # Atualiza o tabuleiro após a jogada do computador
                    Metodos.mostra_tabul(tabuleiro)
                    pygame.display.update()
                else:
                    Metodos.jogada_Humano(tabuleiro, jog)
                    Metodos.mostra_tabul(tabuleiro)
                    pygame.display.update()

            elif tipo == 4:
                if jog == 1:
                    if estrategia1 == 1:
                        Metodos.jogada_pc_minimax(tabuleiro, jog, dificuldade1)
                    elif estrategia1 == 2:
                        Metodos.jogada_pc_alphabeta(tabuleiro, jog, dificuldade1)
                    elif estrategia1 == 3:
                        Metodos.jogada_pc_montecarlo(tabuleiro, jog, dificuldade1)
                    # Atualiza o tabuleiro após a jogada do computador
                    Metodos.mostra_tabul(tabuleiro)
                    pygame.display.update()
                else:
                    if estrategia2 == 1:
                        Metodos.jogada_pc_minimax(tabuleiro, jog, dificuldade2)
                    elif estrategia2 == 2:
                        Metodos.jogada_pc_alphabeta(tabuleiro, jog, dificuldade2)
                    elif estrategia2 == 3:
                        Metodos.jogada_pc_montecarlo(tabuleiro, jog, dificuldade2)
                    # Atualiza o tabuleiro após a jogada do computador
                    Metodos.mostra_tabul(tabuleiro)
                    pygame.display.update()

            # Verificar se o jogo terminou
            fim = Metodos.fim_jogo(tabuleiro, jog)
            condition = (fim == -1)

        # Atualiza a tela com o resultado
        Metodos.mostra_tabul(tabuleiro)
        pygame.display.update()
        time.sleep(1)

        # Calcular tempo de execução
        fim_tempo = time.time()
        tempo = fim_tempo - inicio
        print(f"Tempo de execução: {tempo:.2f} segundos")
        print('Percentagem de CPU utilizada:', psutil.cpu_percent(), '%')
        print('Percentagem de memória RAM utilizada:', psutil.virtual_memory()[2], '%')

        # Monitorização de memória com tracemalloc
        current, peak = tracemalloc.get_traced_memory()
        print(f"Memória atual usada: {current / 1024 / 1024:.2f} MB; Memória máxima: {peak / 1024 / 1024:.2f} MB")
        tracemalloc.stop()

        # Menu pós-jogo com opções
        resultado = menu_pos_jogo(Metodos.screen, fim)
        if resultado == "reiniciar":
            continue
        elif resultado == "menu":
            continue
        elif resultado == "sair":
            pygame.quit()
            sys.exit()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit()




