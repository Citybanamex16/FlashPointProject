import heapq
from enum import Enum
from mesa import Agent
from core_types import EstadoFuego, TipoPOI, POI, Muro, Puerta

class Role(Enum):
    SEARCHER = "Searcher"
    WALLBREAKER = "Wallbreaker"
    SOLDIER = "Soldier"

class Rescuer(Agent):
    def __init__(self, unique_id, model, role=Role.SEARCHER):
        super().__init__(unique_id, model)
        self.role = role
        self.ap = 4  # AP para el turno actual
        self.saved_ap = 0  # AP guardados para el siguiente turno
        self.llevando_victima = False

    def step(self):
        # Turno del agente: asignar AP, ejecutar FSM, y almacenar AP sobrante
        # 1. Asignar AP para el turno actual (máximo 8, incluyendo guardados)
        self.ap = min(8, 4 + self.saved_ap)
        self.saved_ap = 0

        # 2. Ejecutar FSM hasta que se agoten los APs
        while self.ap > 0:
            self._interactuar_celda_actual()

            if self.llevando_victima:
                action_taken = self._ejecutar_estado_escape()
            else:
                action_taken = self._ejecutar_estado_search()

            if not action_taken:
                break

        # 3. Guardar AP sobrante para el siguiente turno (máximo 4)
        self.saved_ap = min(4, self.ap)

    def _obtener_costo_real_arista(self, arista):
        # Calcula el costo físico real en AP para interactuar con una arista (puerta o muro).
        if arista is None:
            return 0
        if isinstance(arista, Puerta):
            return 1 if arista.cerrado else 0
        if isinstance(arista, Muro):
            return arista.hp * 2  # 2 AP por golpe para romper un muro
        return 0

    def _obtener_costo_real_nodo(self, nodo):
        # Calcula el costo físico real en AP para moverse
        costo = 1  # Costo base de movimiento
        if nodo.estado_fuego == EstadoFuego.HUMO:
            costo = 2
        elif nodo.estado_fuego == EstadoFuego.FUEGO:
            costo = 3

        if self.llevando_victima:
            costo += 1  # Costo adicional por cargar una víctima

        return costo

    def _obtener_peso_percibido_arista(self, arista):
        # Calcula el peso percibido para una arista (puerta o muro) según la rol del agente
        if arista is None:
            return 0
        if isinstance(arista, Puerta):
            return 1 if arista.cerrado else 0
        if isinstance(arista, Muro):
            if arista.hp <= 0:
                return 0
            
            # Evita romper muros si la preservación estructural está activa
            if self._es_preservacion_estructural_activa():
                return 99  # Costo muy alto para evitar romper muros

            # Percepción de rol
            if self.role == Role.WALLBREAKER:
                return arista.hp * 1.0  # Prefiere romper muros
            elif self.role == Role.SEARCHER:
                return arista.hp * 6.0  # Evita romper muros a menos que sea necesario
            else:
                return arista.hp * 2.0  # Costo moderado estandard

        return 0

    def _obtener_peso_percibido_nodo(self, nodo):
        # Calcula el peso percibido para un nodo según la rol del agente
        peso_base = self._obtener_costo_real_nodo(nodo)

        # Ajustes de peso según el rol y el estado del fuego
        if self.role == Role.SEARCHER and nodo.estado_fuego != EstadoFuego.LIMPIO:
            peso_base += 4.0  # Evita moverse hacia/atravesar peligros
        elif self.role == Role.SOLDIER and nodo.estado_fuego != EstadoFuego.LIMPIO:
            peso_base -= 0.5  # Soldados tienden a acercarse a amenazas para suprimirlas

        return max(1.0, peso_base)

    def _es_preservacion_estructural_activa(self):
        # Determina si la preservación estructural está activa (cuando el daño acumulado es >= 18).
        dano_acumulado = 24 - self.model.marcadores_dano
        return dano_acumulado >= 18

    def _es_salida(self, pos):
        # Determina si una posición dada es una salida.
        x, y = pos
        return x == 0 or x == self.model.grid.width - 1 or y == 0 or y == self.model.grid.height - 1

    def _obtener_pois_activos(self):
        # Obtiene todas las coordenadas de POIs activos (no revelados o víctimas no recogidas).
        return [pos for pos, nodo in self.model.mapa_nodos.items() if any(isinstance(c, POI) for c in nodo.contenido)]

    def _obtener_salidas(self):
        # Obtiene todas las coordenadas de salidas.
        return [pos for pos in self.model.mapa_nodos.keys() if self._es_salida(pos)]

    def _encontrar_ruta_optima(self, destinos):
        # Implementacion de Dijkstra para encontrar la ruta optima (basado en roles)
        if not destinos:
            return None, float('inf')

        start = self.pos
        queue = [(0, start, [])]
        visited = set()

        while queue:
            (cost, current, path) = heapq.heappop(queue)

            if current in visited:
                continue
            visited.add(current)

            if current in destinos:
                return path + [current], cost

            nodo_actual = self.model.mapa_nodos[current]
            for nodo_vecino, arista in nodo_actual.vecinos.items():
                pos_vecino = nodo_vecino.pos
                if pos_vecino in visited:
                    continue

                peso_paso = self._obtener_peso_percibido_arista(arista) + self._obtener_peso_percibido_nodo(nodo_vecino)
                heapq.heappush(queue, (cost + peso_paso, pos_vecino, path + [current]))

        return None, float('inf')

    def _interactuar_celda_actual(self):
        # Interactúa con la celda actual: revela POIs, recoge víctimas y completa rescates si es posible.
        nodo_actual = self.model.mapa_nodos[self.pos]

        # 1. Revelar POIs y recoger víctimas 
        for item in list(nodo_actual.contenido):
            if isinstance(item, POI):
                item.revelado = True
                if item.tipo == TipoPOI.FALSA_ALARMA:
                    nodo_actual.contenido.remove(item)
                elif item.tipo == TipoPOI.VICTIMA and not self.llevando_victima:
                    nodo_actual.contenido.remove(item)
                    self.llevando_victima = True

        # 2. Completar rescate 
        if self.llevando_victima and self._es_salida(self.pos):
            self.llevando_victima = False
            self.model.victimas_salvadas += 1

    def _avanzar_hacia(self, siguiente_pos):
        # Avanza hacia la posición objetivo, manejando obstáculos y costos de movimiento.
        nodo_actual = self.model.mapa_nodos[self.pos]
        nodo_destino = self.model.mapa_nodos[siguiente_pos]
        arista = nodo_actual.vecinos.get(nodo_destino)

        # 1. Interactuar con la arista (puerta o muro) si es necesario
        if arista is not None:
            if isinstance(arista, Puerta) and arista.cerrado:
                if self.ap >= 1:
                    arista.abrir()
                    self.ap -= 1
                    return True
                return False

            if isinstance(arista, Muro) and arista.hp > 0:
                if self.ap >= 2:  # 2 AP para golpear un muro
                    arista.golpear()
                    self.model.marcadores_dano -= 1
                    self.ap -= 2
                    return True
                return False

        # 2. Moverse al nodo destino si hay AP suficientes
        costo_real = self._obtener_costo_real_nodo(nodo_destino)
        if self.ap >= costo_real:
            self.ap -= costo_real
            self.model.grid.move_agent(self, siguiente_pos)
            return True

        return False

    def _ejecutar_estado_search(self):
        # SEARCH Mode: Prioriza la búsqueda de POIs activos y rescate de víctimas.
        # Acción específica de rol: Extinguir amenaza adyacente si es SOLDIER
        if self.role == Role.SOLDIER and self._extinguir_amenaza_adjacente():
            return True

        # Buscar POIs activos y moverse hacia el más cercano
        pois = self._obtener_pois_activos()
        if not pois:
            return self._extinguir_amenaza_adjacente()  # Si no hay POIs, intentar suprimir amenazas adyacentes

        ruta, costo = self._encontrar_ruta_optima(pois)
        if not ruta or len(ruta) < 2:
            return self._extinguir_amenaza_adjacente()

        return self._avanzar_hacia(ruta[1])

    def _ejecutar_estado_escape(self):
        # ESCAPE Mode: Prioriza moverse hacia la salida más cercana.
        salidas = self._obtener_salidas()
        ruta, costo = self._encontrar_ruta_optima(salidas)
        if not ruta or len(ruta) < 2:
            return False

        return self._avanzar_hacia(ruta[1])

    def _extinguir_amenaza_adjacente(self):
        # Extingue amenazas en nodos adyacentes si hay AP suficientes.
        nodo_actual = self.model.mapa_nodos[self.pos]
        
        for nodo_vecino, arista in nodo_actual.vecinos.items():
            if isinstance(arista, Muro) and arista.hp > 0:
                continue
            if isinstance(arista, Puerta) and arista.cerrado:
                continue

            if nodo_vecino.estado_fuego == EstadoFuego.FUEGO and self.ap >= 2:
                nodo_vecino.estado_fuego = EstadoFuego.HUMO
                self.ap -= 2
                return True
            elif nodo_vecino.estado_fuego == EstadoFuego.HUMO and self.ap >= 1:
                nodo_vecino.estado_fuego = EstadoFuego.LIMPIO
                self.ap -= 1
                return True

        return False