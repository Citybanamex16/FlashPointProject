import random
from mesa import Model
from mesa.space import MultiGrid
from core_types import EstadoFuego, TipoPOI, POI, Nodo, Muro, Puerta
import matplotlib.patches as patches
import matplotlib.pyplot as plt

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
        fuegos_iniciales = [(6,1), (6,2), (7,2), (4,3),(2,4),(3,4),(4,4),(5,4),(2,5),(3,5)]
        for pos in fuegos_iniciales:
            if pos in self.mapa_nodos:
                self.mapa_nodos[pos].estado_fuego = EstadoFuego.FUEGO
                
        self.bolsa_poi = [TipoPOI.VICTIMA] * 10 + [TipoPOI.FALSA_ALARMA] * 5
        random.shuffle(self.bolsa_poi)
        
        pois_iniciales = [(1,2), (8,2), (4,5)]
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

    # otra visualizacion debug pero mas nice
    def visualizar_matplot(self, figsize=(10, 8)):
        fig, ax = plt.subplots(figsize=figsize)

        color_fuego = {
            EstadoFuego.LIMPIO: "#E0E0E0",  # Gris claro (exterior/limpio)
            EstadoFuego.HUMO: "#808080",  # Gris oscuro
            EstadoFuego.FUEGO: "#FF4500",  # Rojo anaranjado
        }

        # 1. Dibujar el fondo de cada Celda y Hazards
        for (x, y), nodo in self.mapa_nodos.items():
            color = color_fuego.get(nodo.estado_fuego, "#FFFFFF")
            rect = patches.Rectangle(
                (x, y), 1, 1, facecolor=color, edgecolor="#D3D3D3", lw=0.5
            )
            ax.add_patch(rect)

            # Marcador de POI
            if any(isinstance(c, POI) for c in nodo.contenido):
                ax.text(
                    x + 0.5,
                    y + 0.5,
                    "?",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color="black",
                )

        # 2. Dibujar Muros y Puertas en los bordes
        procesados = set()
        for (x, y), nodo in self.mapa_nodos.items():
            for vecino, arista in nodo.vecinos.items():
                if arista is None or arista in procesados:
                    continue
                procesados.add(arista)

                nx, ny = vecino.pos

                # Determinar coordenadas del segmento entre celdas
                if nx == x + 1:  # Borde vertical (Derecha)
                    line_x, line_y = [x + 1, x + 1], [y, y + 1]
                elif nx == x - 1:  # Borde vertical (Izquierda)
                    line_x, line_y = [x, x], [y, y + 1]
                elif ny == y + 1:  # Borde horizontal (Arriba)
                    line_x, line_y = [x, x + 1], [y + 1, y + 1]
                else:  # Borde horizontal (Abajo)
                    line_x, line_y = [x, x + 1], [y, y]

                # Estilizar según tipo y estado
                if isinstance(arista, Muro):
                    if arista.hp == 2:
                        ax.plot(
                            line_x,
                            line_y,
                            color="black",
                            lw=4,
                            solid_capstyle="round",
                        )
                    elif arista.hp == 1:
                        ax.plot(
                            line_x,
                            line_y,
                            color="#8B4513",
                            lw=2.5,
                            linestyle="--",
                        )
                elif isinstance(arista, Puerta):
                    color_p = "#0000FF" if arista.cerrado else "#32CD32"
                    ax.plot(line_x, line_y, color=color_p, lw=3, linestyle=":")

        # 3. Ajustes de vista y ejes
        ax.set_xlim(0, self.grid.width)
        ax.set_ylim(0, self.grid.height)
        ax.set_xticks(range(self.grid.width + 1))
        ax.set_yticks(range(self.grid.height + 1))
        ax.set_aspect("equal")
        ax.grid(False)
        plt.title("Flash Point: Fire Rescue - Tablero")
        plt.show()

