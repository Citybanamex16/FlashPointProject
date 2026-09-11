from enum import Enum

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

class POI():
    def __init__(self, tipo):
        self.tipo = tipo
        self.revelado = False

class Nodo():
    def __init__(self, pos):
        self.pos = pos
        self.estado_fuego = EstadoFuego.LIMPIO
        self.contenido = []
        self.vecinos = {}

class Arista():
    def __init__(self, tipo):
        self.tipo = tipo
        self.key = None

class Puerta(Arista):
    def __init__(self):
        super().__init__(TipoArista.PUERTA)
        self.cerrado = True
        self.destruida = False

    def abrir(self):
        self.cerrado = False

    def cerrar(self):
        if not self.destruida:
            self.cerrado = True
        
    def destruir(self):
        self.cerrado = False
        self.destruida = True

class Muro(Arista):
    def __init__(self):
        super().__init__(TipoArista.MURO)
        self.hp = 2

    def golpear(self):
        if self.hp > 0:
            self.hp -= 1
