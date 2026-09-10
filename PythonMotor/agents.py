import heapq
from enum import Enum
from mesa import Agent
from core_types import EstadoFuego, TipoPOI, POI, Muro, Puerta

class Role(Enum):
    SEARCHER = "Searcher"
    WALLBREAKER = "Wallbreaker"
    SOLDIER = "Soldier"


class AgentAction(Enum):
    IDLE = "IDLE"
    MOVE = "MOVE"
    OPEN_DOOR = "OPEN_DOOR"
    CLOSE_DOOR = "CLOSE_DOOR"
    BREAK_WALL = "BREAK_WALL"
    EXTINGUISH = "EXTINGUISH"
    SEARCH = "SEARCH"
    PICK_UP_VICTIM = "PICK_UP_VICTIM"
    RESCUE_VICTIM = "RESCUE_VICTIM"
    DROP_VICTIM = "DROP_VICTIM"
    KNOCKED_DOWN = "KNOCKED_DOWN"


class AgentStatus(Enum):
    ACTIVE = "ACTIVE"
    KNOCKED_DOWN = "KNOCKED_DOWN"


class Rescuer(Agent):
    def __init__(self, model, role=Role.SEARCHER): 
        super().__init__(model) 
        self.role = role
        self.ap = 4 
        self.saved_ap = 0  
        self.llevando_victima = False
        self.accion_actual = AgentAction.IDLE
        self.posicion_anterior = None
        self.posicion_objetivo = None
        self.acciones_turno = []
        self.estado = AgentStatus.ACTIVE

    def registrar_accion(self, accion, objetivo=None):
        self.accion_actual = accion
        self.posicion_objetivo = objetivo
        self.acciones_turno.append(accion)
        self.model._marcar_agente(self)

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
        self.posicion_anterior = self.pos
        self.posicion_objetivo = None
        self.accion_actual = AgentAction.IDLE
        self.acciones_turno = []
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

    def _soltar_victima(self):
        # Si el agente está llevando una víctima, la deja en la celda actual y marca el POI como revelado
        if self.llevando_victima:
            self.llevando_victima = False
            nodo_actual = self.model.mapa_nodos[self.pos]
            poi_victima = POI(TipoPOI.VICTIMA)
            poi_victima.revelado = True
            nodo_actual.contenido.append(poi_victima)
            self.registrar_accion(AgentAction.DROP_VICTIM, self.pos)

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

        # Prohibir entrar al fuego con víctima
        if self.llevando_victima and nodo.estado_fuego == EstadoFuego.FUEGO:
            return float('inf')

        if self.role == Role.SEARCHER and nodo.estado_fuego != EstadoFuego.LIMPIO:
            peso_base += 4.0
        elif self.role == Role.SOLDIER:
            if nodo.estado_fuego == EstadoFuego.FUEGO:
                return 0.5
            if nodo.estado_fuego == EstadoFuego.HUMO:
                return 0.75

        return max(1.0, peso_base)

    def _es_preservacion_estructural_activa(self):
        return self.model.marcadores_dano <= 12

    def _hay_fuego_critico(self, umbral=8):
        # Cuenta el número de celdas en estado FUEGO y compara con el umbral
        fuegos = sum(1 for n in self.model.mapa_nodos.values() if n.estado_fuego == EstadoFuego.FUEGO)
        return fuegos >= umbral

    def _obtener_fuegos_activos(self):
        return [
            pos
            for pos, nodo in self.model.mapa_nodos.items()
            if nodo.estado_fuego == EstadoFuego.FUEGO
        ]

    def _es_salida(self, pos):
        x, y = pos
        return x == 0 or x == self.model.grid.width - 1 or y == 0 or y == self.model.grid.height - 1

    def _obtener_pois_activos(self):
        # Coordenadas de POIs no reclamados por otros agentes
        pois = []
        for pos, nodo in self.model.mapa_nodos.items():
            if any(isinstance(c, POI) for c in nodo.contenido):
                agente_dueno = self.model.pois_reclamados.get(pos)
                if agente_dueno is None or agente_dueno == self:
                    pois.append(pos)
        return pois

    def _seleccionar_mejor_poi(self):
        # Selecciona el POI más cercano considerando la ruta de ida y vuelta a la salida más cercana
        pois = self._obtener_pois_activos()
        if not pois:
            return None

        salidas = self._obtener_salidas()
        mejor_poi = None
        menor_costo_total = float('inf')

        for poi_pos in pois:
            # Distancia actual -> POI
            _, costo_a_poi = self._encontrar_ruta_optima([poi_pos])
            if costo_a_poi == float('inf'):
                continue

            # Distancia POI -> Salida más cercana
            _, costo_poi_a_salida = self._encontrar_ruta_optima(salidas, origen=poi_pos)
            costo_total = costo_a_poi + costo_poi_a_salida

            if costo_total < menor_costo_total:
                menor_costo_total = costo_total
                mejor_poi = poi_pos

        if mejor_poi:
            # Marcar el POI como reclamado por este agente para evitar conflictos
            self.model.pois_reclamados[mejor_poi] = self

        return mejor_poi

    def _obtener_salidas(self):
        return [pos for pos in self.model.mapa_nodos.keys() if self._es_salida(pos)]

    def _encontrar_ruta_optima(self, destinos, origen=None):
        # Dijkstra con pesos percibidos según el rol
        if not destinos:
            return None, float('inf')

        start = origen if origen is not None else self.pos
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

                # Eliminar POI del mapa de reclamados si es falso o víctima recogida
                if self.pos in self.model.pois_reclamados:
                    del self.model.pois_reclamados[self.pos]

                if item.tipo == TipoPOI.FALSA_ALARMA:
                    nodo_actual.contenido.remove(item)
                elif item.tipo == TipoPOI.VICTIMA and not self.llevando_victima:
                    nodo_actual.contenido.remove(item)
                    self.llevando_victima = True
                    self.registrar_accion(AgentAction.PICK_UP_VICTIM, self.pos)

        if self.llevando_victima and self._es_salida(self.pos):
            self.llevando_victima = False
            self.model.victimas_salvadas += 1
            self.registrar_accion(AgentAction.RESCUE_VICTIM, self.pos)

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
            self.registrar_accion(AgentAction.MOVE, siguiente_pos)
            
            return True

        return False

    def alternar_puerta(self, siguiente_pos):
        nodo_actual = self.model.mapa_nodos[self.pos]
        nodo_destino = self.model.mapa_nodos[siguiente_pos]
        arista = nodo_actual.vecinos.get(nodo_destino)

        if not isinstance(arista, Puerta) or arista.destruida:
            return False

        if self._gastar_ap(1):
            accion = AgentAction.OPEN_DOOR if arista.cerrado else AgentAction.CLOSE_DOOR
            arista.abrir() if arista.cerrado else arista.cerrar()
            self.registrar_accion(accion, siguiente_pos)
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
            self.registrar_accion(AgentAction.BREAK_WALL, siguiente_pos)
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
                self.registrar_accion(AgentAction.EXTINGUISH, objetivo_pos)
                return True

        if nodo_objetivo.estado_fuego == EstadoFuego.FUEGO:
            costo = 2 if completamente else 1
            if self._gastar_ap(costo):
                nodo_objetivo.estado_fuego = EstadoFuego.LIMPIO if completamente else EstadoFuego.HUMO
                self.registrar_accion(AgentAction.EXTINGUISH, objetivo_pos)
                return True

        return False

    def _ejecutar_estado_search(self):
        # Estado SEARCH: Buscar POIs activos y extinguir amenazas si es necesario
        if self.role != Role.SEARCHER and self._extinguir_amenaza_adjacente():
            return True

        if self.role != Role.SEARCHER:
            fuegos = self._obtener_fuegos_activos()
            ruta_fuego, _ = self._encontrar_ruta_optima(fuegos)
            if ruta_fuego and len(ruta_fuego) >= 2:
                return self._avanzar_hacia(ruta_fuego[1])

        if self._hay_fuego_critico(umbral=4):
            if self._extinguir_amenaza_adjacente():
                return True

            fuegos = self._obtener_fuegos_activos()
            ruta_fuego, _ = self._encontrar_ruta_optima(fuegos)
            if ruta_fuego and len(ruta_fuego) >= 2:
                return self._avanzar_hacia(ruta_fuego[1])

        if self._hay_fuego_critico(umbral=4):
            if self._extinguir_amenaza_adjacente():
                return True

        poi_objetivo = self._seleccionar_mejor_poi()
        if not poi_objetivo:
            return self._extinguir_amenaza_adjacente()

        ruta, _ = self._encontrar_ruta_optima([poi_objetivo])
        if not ruta or len(ruta) < 2:
            return self._extinguir_amenaza_adjacente()

        return self._avanzar_hacia(ruta[1])

    def _ejecutar_estado_escape(self):
        # Estado ESCAPE: Llevar víctima a la salida más cercana y extinguir amenazas si es necesario
        salidas = self._obtener_salidas()
        ruta, costo = self._encontrar_ruta_optima(salidas)
        
        # Si el fuego bloquea completamente el camino a cualquier salida
        if not ruta or len(ruta) < 2 or costo == float('inf'):
            self._soltar_victima()
            return self._extinguir_amenaza_adjacente()

        exito = self._avanzar_hacia(ruta[1])
        if not exito:
            # Si el movimiento falla por obstáculo o fuego
            self._soltar_victima()
            return self._extinguir_amenaza_adjacente()

        return True

    def _extinguir_amenaza_adjacente(self):
        # Revisa primero la celda actual y luego las vecinas accesibles
        if self._extinguir_objetivo(self.pos):
            return True

        nodo_actual = self.model.mapa_nodos[self.pos]
        for nodo_vecino, arista in nodo_actual.vecinos.items():
            if isinstance(arista, Muro) and arista.hp > 0:
                continue
            if isinstance(arista, Puerta) and arista.cerrado:
                continue

            if self._extinguir_objetivo(nodo_vecino.pos):
                return True

        return False

    def _extinguir_objetivo(self, objetivo_pos):
        nodo_objetivo = self.model.mapa_nodos[objetivo_pos]
        completamente = (
            self.role == Role.SOLDIER
            and nodo_objetivo.estado_fuego == EstadoFuego.FUEGO
            and self.ap >= 2
        )
        return self.extinguir(objetivo_pos, completamente=completamente)