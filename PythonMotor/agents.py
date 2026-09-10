import heapq
from enum import Enum
from mesa import Agent
from core_types import EstadoFuego, TipoPOI, POI, Muro, Puerta

class Role(Enum):
    SEARCHER = "Searcher"
    WALLBREAKER = "Wallbreaker"
    SOLDIER = "Soldier"

class Rescuer(Agent):
    def __init__(self, model, role=Role.SEARCHER): 
        super().__init__(model) 
        self.role = role
        self.ap = 4 
        self.saved_ap = 0  
        self.llevando_victima = False

    def step(self):
        self._iniciar_turno()

        # Ejecutar hasta agotar AP o quedarse sin acciones viables
        while self.ap > 0:
            self._interactuar_celda_actual()

            if self.llevando_victima:
                action_taken = self._ejecutar_estado_escape()
            else:
                action_taken = self._ejecutar_estado_search()

            if not action_taken:
                break

        self._terminar_turno()

    def _iniciar_turno(self):
        self.ap = min(8, self.saved_ap + 4)
        self.saved_ap = 0

    def _terminar_turno(self):
        self.saved_ap = min(4, self.ap)
        self.ap = 0

    def _gastar_ap(self, costo):
        if costo < 0 or self.ap < costo:
            return False
        self.ap -= costo
        return True

    def _obtener_costo_real_arista(self, arista):
        # Costo en AP para cruzar/destruir obstáculos
        if arista is None:
            return 0
        if isinstance(arista, Puerta):
            return 1 if arista.cerrado else 0
        if isinstance(arista, Muro):
            return arista.hp * 2
        return 0

    def _obtener_costo_real_nodo(self, nodo):
        # Costo base en AP para moverse a una celda
        if self.llevando_victima or nodo.estado_fuego == EstadoFuego.FUEGO:
            return 2
        return 1

    def _obtener_peso_percibido_arista(self, arista):
        # Peso de pathfinding para obstáculos según rol
        if arista is None:
            return 0
        if isinstance(arista, Puerta):
            return 1 if arista.cerrado else 0
        if isinstance(arista, Muro):
            if arista.hp <= 0:
                return 0
            
            # Evitar muros si hay riesgo de colapso
            if self._es_preservacion_estructural_activa():
                return 99  

            # Modificadores por rol
            if self.role == Role.WALLBREAKER:
                return arista.hp * 1.0  
            elif self.role == Role.SEARCHER:
                return arista.hp * 6.0  
            else:
                return arista.hp * 3.0  

        return 0

    def _obtener_peso_percibido_nodo(self, nodo):
        # Peso de pathfinding para celdas según rol
        peso_base = self._obtener_costo_real_nodo(nodo)

        if self.role == Role.SEARCHER and nodo.estado_fuego != EstadoFuego.LIMPIO:
            peso_base += 4.0
        elif self.role == Role.SOLDIER and nodo.estado_fuego != EstadoFuego.LIMPIO:
            peso_base -= 0.5 

        return max(1.0, peso_base)

    def _es_preservacion_estructural_activa(self):
        return self.model.marcadores_dano <= 12

    def _es_salida(self, pos):
        x, y = pos
        return x == 0 or x == self.model.grid.width - 1 or y == 0 or y == self.model.grid.height - 1

    def _obtener_pois_activos(self):
        # Coordenadas de POIs ocultos o víctimas en el mapa
        return [pos for pos, nodo in self.model.mapa_nodos.items() if any(isinstance(c, POI) for c in nodo.contenido)]

    def _obtener_salidas(self):
        return [pos for pos in self.model.mapa_nodos.keys() if self._es_salida(pos)]

    def _encontrar_ruta_optima(self, destinos):
        # Dijkstra con pesos percibidos según el rol
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
        # Revela POIs, levanta víctimas o escapa si está en una salida
        nodo_actual = self.model.mapa_nodos[self.pos]

        for item in list(nodo_actual.contenido):
            if isinstance(item, POI):
                item.revelado = True
                if item.tipo == TipoPOI.FALSA_ALARMA:
                    nodo_actual.contenido.remove(item)
                elif item.tipo == TipoPOI.VICTIMA and not self.llevando_victima:
                    nodo_actual.contenido.remove(item)
                    self.llevando_victima = True

        if self.llevando_victima and self._es_salida(self.pos):
            self.llevando_victima = False
            self.model.victimas_salvadas += 1

    def _avanzar_hacia(self, siguiente_pos):
        # Intenta moverse a un nodo adyacente
        nodo_actual = self.model.mapa_nodos[self.pos]
        nodo_destino = self.model.mapa_nodos[siguiente_pos]
        arista = nodo_actual.vecinos.get(nodo_destino)

        # Manejar obstáculos primero
        if arista is not None:
            if isinstance(arista, Puerta) and arista.cerrado:
                return self.alternar_puerta(siguiente_pos)
            if isinstance(arista, Muro) and arista.hp > 0:
                return self.cortar_muro(siguiente_pos)

        # Prohibido entrar al fuego con víctima
        if self.llevando_victima and nodo_destino.estado_fuego == EstadoFuego.FUEGO:
            return False

        costo_real = self._obtener_costo_real_nodo(nodo_destino)
        if self._gastar_ap(costo_real):
            # Sincronizar posición en ambos grafos (Mesa y red interna)
            if self in nodo_actual.contenido:
                nodo_actual.contenido.remove(self)
                
            self.model.grid.move_agent(self, siguiente_pos)
            nodo_destino.contenido.append(self)
            
            return True

        return False

    def alternar_puerta(self, siguiente_pos):
        nodo_actual = self.model.mapa_nodos[self.pos]
        nodo_destino = self.model.mapa_nodos[siguiente_pos]
        arista = nodo_actual.vecinos.get(nodo_destino)

        if not isinstance(arista, Puerta) or arista.destruida:
            return False

        if self._gastar_ap(1):
            arista.abrir() if arista.cerrado else arista.cerrar()
            return True
        return False

    def cortar_muro(self, siguiente_pos):
        nodo_actual = self.model.mapa_nodos[self.pos]
        nodo_destino = self.model.mapa_nodos[siguiente_pos]
        arista = nodo_actual.vecinos.get(nodo_destino)

        if not isinstance(arista, Muro) or arista.hp <= 0:
            return False

        if self._gastar_ap(2):
            arista.golpear()
            self.model.marcadores_dano -= 1
            return True
        return False

    def extinguir(self, objetivo_pos=None, completamente=False):
        # Apaga fuego/humo en la celda actual o una adyacente
        if objetivo_pos is None:
            objetivo_pos = self.pos
            
        nodo_actual = self.model.mapa_nodos[self.pos]
        nodo_objetivo = self.model.mapa_nodos.get(objetivo_pos)

        if nodo_objetivo is None:
            return False

        # Bloquear acción si hay muro intacto o puerta cerrada entre celdas
        if objetivo_pos != self.pos:
            arista = nodo_actual.vecinos.get(nodo_objetivo)
            if isinstance(arista, Muro) and arista.hp > 0:
                return False
            if isinstance(arista, Puerta) and arista.cerrado:
                return False

        if nodo_objetivo.estado_fuego == EstadoFuego.HUMO:
            if self._gastar_ap(1):
                nodo_objetivo.estado_fuego = EstadoFuego.LIMPIO
                return True

        if nodo_objetivo.estado_fuego == EstadoFuego.FUEGO:
            costo = 2 if completamente else 1
            if self._gastar_ap(costo):
                nodo_objetivo.estado_fuego = EstadoFuego.LIMPIO if completamente else EstadoFuego.HUMO
                return True

        return False

    def _ejecutar_estado_search(self):
        # Estado SEARCH: Buscar POIs o atacar fuego (SOLDIER)
        if self.role == Role.SOLDIER and self._extinguir_amenaza_adjacente():
            return True

        pois = self._obtener_pois_activos()
        if not pois:
            return self._extinguir_amenaza_adjacente() 

        ruta, _ = self._encontrar_ruta_optima(pois)
        if not ruta or len(ruta) < 2:
            return self._extinguir_amenaza_adjacente()

        return self._avanzar_hacia(ruta[1])

    def _ejecutar_estado_escape(self):
        # Estado ESCAPE: Dirigirse a la salida más cercana
        salidas = self._obtener_salidas()
        ruta, _ = self._encontrar_ruta_optima(salidas)
        
        if not ruta or len(ruta) < 2:
            return False

        return self._avanzar_hacia(ruta[1])

    def _extinguir_amenaza_adjacente(self):
        # Revisa primero la celda actual y luego las vecinas accesibles
        if self.extinguir():
            return True

        nodo_actual = self.model.mapa_nodos[self.pos]
        for nodo_vecino, arista in nodo_actual.vecinos.items():
            if isinstance(arista, Muro) and arista.hp > 0:
                continue
            if isinstance(arista, Puerta) and arista.cerrado:
                continue

            if self.extinguir(nodo_vecino.pos):
                return True

        return False