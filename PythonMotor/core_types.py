from enum import Enum

# ==== Enums de Estado ==== #
class EstadoFuego(Enum):
    LIMPIO = 0
    HUMO = 1
    FUEGO = 2

class TipoArista(Enum):
    MURO = 1
    PUERTA = 2

class TipoPOI(Enum):
    VICTIMA = 1
    FALSA_ALARMA = 2

# ==== Objetos de Juego ==== #
class POI():
    def __init__(self, tipo):
        self.tipo = tipo # TipoPOI (Victima o Falsa Alarma)
        self.revelado = False # Comienza boca abajo

# ==== Clases de modelo ==== #
class Nodo():
    def __init__(self, pos):
        self.pos = pos # Vector2D de posicion (x,y)
        self.estado_fuego = EstadoFuego.LIMPIO # Estado del hazard
        self.contenido = [] # Lista para almacenar Firefighters, POIs, etc.
        self.vecinos = {} # Diccionario de vecinos {Nodo: Arista}

class Arista():
    def __init__(self, tipo):
        self.tipo = tipo 

class Puerta(Arista):
    def __init__(self):
        super().__init__(TipoArista.PUERTA)
        self.cerrado = True

    def abrir(self):
        self.cerrado = False
        
    def destruir(self):
        self.cerrado = False # En el juego, una puerta destruida cuenta como espacio abierto

class Muro(Arista):
    def __init__(self):
        super().__init__(TipoArista.MURO)
        self.hp = 2

    def golpear(self):
        if self.hp > 0:
            self.hp -= 1