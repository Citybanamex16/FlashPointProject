import random
from mesa import Model
from mesa.space import MultiGrid
from core_types import EstadoFuego, TipoPOI, POI, Nodo, Muro, Puerta

class FlashPointModel(Model):
    def __init__(self, numAgents, width, height):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False) # Grid de vectores2D
        self.bolsa_poi = []

        # 1. Crear matriz de Nodos
        self.mapa_nodos = {} 
        for x in range(width):
            for y in range(height):
                nodo = Nodo(pos=(x, y))
                self.mapa_nodos[(x, y)] = nodo

        # 2. Inicializamos relaciones ortogonales
        self._conectar_vecinos_base(width, height)

        # 3. Colocar Muros y Puertas 
        self._cargar_infraestructura_tablero()
        
        # 4. Preparar Setup Familiar
        self._preparar_juego_familiar()

    def _conectar_vecinos_base(self, width, height):
        for (x, y), nodo in self.mapa_nodos.items():
            direcciones = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
            for nx, ny in direcciones:
                if 0 <= nx < width and 0 <= ny < height:
                    nodo_vecino = self.mapa_nodos[(nx, ny)]
                    nodo.vecinos[nodo_vecino] = None 

    def _colocar_borde(self, pos_a, pos_b, objeto_arista):
        nodo_a = self.mapa_nodos[pos_a]
        nodo_b = self.mapa_nodos[pos_b]
        nodo_a.vecinos[nodo_b] = objeto_arista
        nodo_b.vecinos[nodo_a] = objeto_arista

    def _cargar_infraestructura_tablero(self):
        lista_muros = [
            ((0,1), (1,1)), ((0,2), (1,2)), ((0,3), (1,3)), ((0,5), (1,5)), ((0,6), (1,6)),
            ((1,0), (1,1)), ((2,0), (2,1)),
            ((4,0), (4,1)), ((5,0), (5,1)), ((6,0), (6,1)), ((7,0), (7,1)), ((8,0), (8,1)),
            ((1,6), (1,7)), ((2,6), (2,7)), ((3,6), (3,7)), ((4,6), (4,7)), ((5,6), (5,7)), ((7,6), (7,7)), ((8,6), (8,7)),
            ((8,1), (9,1)), ((8,2), (9,2)), ((8,4), (9,4)), ((8,5), (9,5)), ((8,6), (9,6)),
            ((5,2), (6,2)), ((7,2), (8,2)), ((2,3), (3,3)), ((6,4), (7,4)), ((3,5), (4,5)), ((5,6), (6,6)), 
            ((1,2), (1,3)), ((2,2), (2,3)), ((3,2), (3,3)), ((5,2), (5,3)), ((6,2), (6,3)), ((7,2), (7,3)), ((8,2), (8,3)),
            ((3,4), (3,5)), ((4,4), (4,5)), ((5,4), (5,5)), ((6,4), (6,5)), ((7,4), (7,5))
        ]
        
        lista_puertas = [
            ((3,0), (3,1)), ((0,4), (1,4)), ((6,6), (6,7)), ((8,3), (9,3)), 
            ((7,1), (8,1)), ((5,1), (6,1)), ((4,2), (4,3)), ((6,3), (7,3)), 
            ((2,4), (3,4)), ((8,4), (8,5)), ((3,6), (4,6)), ((5,5), (6,5)) 
        ]

        for pos_a, pos_b in lista_muros:
            if pos_a in self.mapa_nodos and pos_b in self.mapa_nodos:
                self._colocar_borde(pos_a, pos_b, Muro())

        for pos_a, pos_b in lista_puertas:
             if pos_a in self.mapa_nodos and pos_b in self.mapa_nodos:
                self._colocar_borde(pos_a, pos_b, Puerta())

    def _preparar_juego_familiar(self):
        fuegos_iniciales = [(2,2), (2,3), (3,2), (3,4), (4,4), (5,5), (6,5), (7,6), (4,2), (5,3)]
        for pos in fuegos_iniciales:
            if pos in self.mapa_nodos:
                self.mapa_nodos[pos].estado_fuego = EstadoFuego.FUEGO
                
        self.bolsa_poi = [TipoPOI.VICTIMA] * 10 + [TipoPOI.FALSA_ALARMA] * 5
        random.shuffle(self.bolsa_poi)
        
        pois_iniciales = [(2,4), (5,1), (7,4)]
        for pos in pois_iniciales:
            if pos in self.mapa_nodos:
                tipo_poi = self.bolsa_poi.pop()
                self.mapa_nodos[pos].contenido.append(POI(tipo_poi))

    # ==== Sistema de DTO Python -> Unity === #
    def _exportar_nodos_dto(self):
        nodos_lista = []
        for nodo in self.mapa_nodos.values():
            x, y = nodo.pos 
            
            poi_dto = None
            for item in nodo.contenido:
                if isinstance(item, POI):
                    poi_dto = {
                        "tipo": item.tipo.name,      
                        "revelado": item.revelado    
                    }
                    break 
            
            nodo_dto = {
                "x": x,
                "y": y,
                "fuego": nodo.estado_fuego.name, 
                "poi": poi_dto
            }
            nodos_lista.append(nodo_dto)
            
        return nodos_lista

    def _exportar_aristas_dto(self):
        aristas_lista = []
        procesados = set() 
        
        for nodo in self.mapa_nodos.values():
            pos_a = nodo.pos 
            
            for nodo_vecino, arista in nodo.vecinos.items():
                if arista is not None and arista not in procesados:
                    procesados.add(arista) 
                    pos_b = nodo_vecino.pos 
                    
                    arista_dto = {
                        "posA": {"x": pos_a[0], "y": pos_a[1]},
                        "posB": {"x": pos_b[0], "y": pos_b[1]},
                        "tipo": arista.tipo.name  
                    }
                    
                    if isinstance(arista, Puerta):
                        arista_dto["cerrado"] = arista.cerrado
                    elif isinstance(arista, Muro):
                        arista_dto["hp"] = arista.hp
                    
                    aristas_lista.append(arista_dto)
                    
        return aristas_lista

    def get_setup_dto(self):
        return {
            "width": self.grid.width,
            "height": self.grid.height,
            "nodes": self._exportar_nodos_dto(),
            "edges": self._exportar_aristas_dto()
        }

    ## === Visualizacion DEBUG === ##
    def imprimir_tablero_debug(self):
        print("\n" + "=" * 48)
        print("             DEBUG: MAPA DE FLASH POINT")
        print("    [ ]=Limpio [H]=Humo [F]=Fuego | ? = POI Oculto")
        print("    ║/═ Muro (2HP) | │/─ Muro (1HP) | D/d Puerta")
        print("=" * 48 + "\n")

        for y in range(self.grid.height - 1, -1, -1):
            linea_horizontal = "  "
            for x in range(self.grid.width):
                nodo_actual = self.mapa_nodos[(x, y)]
                nodo_arriba = self.mapa_nodos.get((x, y + 1))
                if nodo_arriba and nodo_arriba in nodo_actual.vecinos:
                    borde = nodo_actual.vecinos[nodo_arriba]
                    linea_horizontal += self._simbolo_borde_horizontal(borde) 
                else:
                    linea_horizontal += "─────"
            print(linea_horizontal)

            linea_nodos = f"{y} "
            for x in range(self.grid.width):
                nodo_actual = self.mapa_nodos[(x, y)]
                nodo_derecha = self.mapa_nodos.get((x + 1, y))

                simbolo_fuego = " "
                if nodo_actual.estado_fuego == EstadoFuego.FUEGO: simbolo_fuego = "F"
                elif nodo_actual.estado_fuego == EstadoFuego.HUMO: simbolo_fuego = "H"
                
                simbolo_poi = "?" if any(isinstance(c, POI) for c in nodo_actual.contenido) else " "
                linea_nodos += f"[{simbolo_fuego}{simbolo_poi}]"

                if nodo_derecha and nodo_derecha in nodo_actual.vecinos:
                    borde = nodo_actual.vecinos[nodo_derecha]
                    linea_nodos += self._simbolo_borde_vertical(borde)
                else:
                    linea_nodos += " "
            print(linea_nodos)

        print("  " + "─────" * self.grid.width)
        eje_x = "  " + "".join(f"  {x}  " for x in range(self.grid.width))
        print(eje_x + "\n")

    def _simbolo_borde_horizontal(self, borde):
        if borde is None: return "     " 
        if isinstance(borde, Muro):
            if borde.hp == 2: return "════ "
            elif borde.hp == 1: return "──── "
            return "     " 
        if isinstance(borde, Puerta):
            return "  D  " if borde.cerrado else "  d  "
        return "     "

    def _simbolo_borde_vertical(self, borde):
        if borde is None: return " "
        if isinstance(borde, Muro):
            if borde.hp == 2: return "║"
            elif borde.hp == 1: return "│"
            return " "  
        if isinstance(borde, Puerta):
            return "D" if borde.cerrado else "d"
        return " "