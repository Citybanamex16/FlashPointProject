"""
metrics.py — Medición de resultados para FlashPointModel.

Este módulo NO modifica model.py ni core_types.py. Se conecta desde afuera,
usando el DataCollector de Mesa, así que funciona hoy (sin agents.py) y
seguirá funcionando sin cambios cuando tu compañero agregue los Firefighter:

- Los "model_reporters" leen atributos que YA existen en FlashPointModel
  (marcadores_dano, victimas_salvadas, etc.) o recorren mapa_nodos, así que
  no dependen de que haya agentes.
- Los "agent_reporters" recorren `model.agents` (un AgentSet que Mesa llena
  solo cuando un Agent se registra). Hoy está vacío -> Mesa simplemente no
  genera filas de agentes, sin errores. En cuanto agents.py cree Firefighter
  agents (heredando de mesa.Agent), esas filas van a aparecer solas.

Cosas a confirmar con tu compañero cuando escriba agents.py (ver
FIREFIGHTER_ATTR_FALLBACKS más abajo): los nombres de atributos que va a
usar para "victimas rescatadas" y "celdas visitadas". El código ya asume
`llevando_victima` porque ese nombre ya se usa en model.py.
"""

import random
from collections import Counter

import numpy as np
import pandas as pd
from mesa.datacollection import DataCollector

from core_types import EstadoFuego, TipoArista, POI, Muro, Puerta


# =========================================================================
# 1. HELPERS DE LECTURA DEL TABLERO (operan sobre mapa_nodos, no sobre agentes)
# =========================================================================

def _contar_estado_fuego(model, estado):
    return sum(1 for n in model.mapa_nodos.values() if n.estado_fuego == estado)


def _iterar_aristas_unicas(model):
    """Cada arista (Muro/Puerta) vive duplicada en los .vecinos de sus 2 nodos.
    Recorremos una sola vez, igual que hace _exportar_aristas_dto en model.py."""
    procesadas = set()
    for nodo in model.mapa_nodos.values():
        for _vecino, arista in nodo.vecinos.items():
            if arista is not None and arista not in procesadas:
                procesadas.add(arista)
                yield arista


def _contar_paredes(model):
    intactos = danados = destruidos = 0
    for arista in _iterar_aristas_unicas(model):
        if isinstance(arista, Muro):
            if arista.hp == 2:
                intactos += 1
            elif arista.hp == 1:
                danados += 1
            else:
                destruidos += 1
    return intactos, danados, destruidos


def _contar_puertas(model):
    abiertas = cerradas = 0
    for arista in _iterar_aristas_unicas(model):
        if isinstance(arista, Puerta):
            if arista.cerrado:
                cerradas += 1
            else:
                abiertas += 1
    return abiertas, cerradas


def _contar_pois(model):
    activos = revelados = 0
    for nodo in model.mapa_nodos.values():
        for item in nodo.contenido:
            if isinstance(item, POI):
                activos += 1
                if item.revelado:
                    revelados += 1
    return activos, revelados


# =========================================================================
# 2. MODEL REPORTERS  (nivel partida — funcionan con o sin agentes)
# =========================================================================

def _model_reporters():
    def _walls(model):
        return _contar_paredes(model)

    def _doors(model):
        return _contar_puertas(model)

    def _pois(model):
        return _contar_pois(model)

    return {
        "Steps": lambda m: m.steps,
        "DamageMarkers": lambda m: m.marcadores_dano,
        "DamageTaken": lambda m: 24 - m.marcadores_dano,
        "VictimsSaved": lambda m: m.victimas_salvadas,
        "VictimsLost": lambda m: m.victimas_perdidas,
        "GameState": lambda m: m.estado_juego,
        "FireCells": lambda m: _contar_estado_fuego(m, EstadoFuego.FUEGO),
        "SmokeCells": lambda m: _contar_estado_fuego(m, EstadoFuego.HUMO),
        "CleanCells": lambda m: _contar_estado_fuego(m, EstadoFuego.LIMPIO),
        "WallsIntact": lambda m: _walls(m)[0],
        "WallsDamaged": lambda m: _walls(m)[1],
        "WallsDestroyed": lambda m: _walls(m)[2],
        "DoorsOpen": lambda m: _doors(m)[0],
        "DoorsClosed": lambda m: _doors(m)[1],
        "ActivePOIs": lambda m: _pois(m)[0],
        "RevealedPOIs": lambda m: _pois(m)[1],
        "POIsInBag": lambda m: len(m.bolsa_poi),
        "NumAgents": lambda m: len(m.agents),
    }


# =========================================================================
# 3. AGENT REPORTERS  (nivel bombero — vacíos hasta que exista agents.py,
#    pero listos para llenarse solos. Ajusta FIREFIGHTER_ATTR_FALLBACKS a
#    los nombres reales que use tu compañero.)
# =========================================================================

FIREFIGHTER_ATTR_FALLBACKS = {
    # ya usado en model.py -> confirmado
    "carrying_victim": ("llevando_victima", "carrying_victim", "cargando_victima"),
    # nombres candidatos, ajustar cuando exista agents.py
    "victims_rescued": ("victimas_rescatadas", "rescates", "victims_rescued"),
    "cells_visited": ("celdas_visitadas", "pasos_dados", "cells_visited"),
    "actions_taken": ("acciones_tomadas", "acciones", "actions_taken"),
    "knockdowns": ("veces_derribado", "knockdowns", "derribos"),
}


def _first_attr(agent, names, default=None):
    for name in names:
        if hasattr(agent, name):
            return getattr(agent, name)
    return default


def _agent_reporters():
    return {
        "AgentType": lambda a: type(a).__name__,
        "Position": lambda a: getattr(a, "pos", None),
        "CarryingVictim": lambda a: _first_attr(
            a, FIREFIGHTER_ATTR_FALLBACKS["carrying_victim"], False
        ),
        "VictimsRescued": lambda a: _first_attr(
            a, FIREFIGHTER_ATTR_FALLBACKS["victims_rescued"], 0
        ),
        "CellsVisited": lambda a: _first_attr(
            a, FIREFIGHTER_ATTR_FALLBACKS["cells_visited"], 0
        ),
        "ActionsTaken": lambda a: _first_attr(
            a, FIREFIGHTER_ATTR_FALLBACKS["actions_taken"], 0
        ),
        "Knockdowns": lambda a: _first_attr(
            a, FIREFIGHTER_ATTR_FALLBACKS["knockdowns"], 0
        ),
    }


def build_collector():
    """Crea un DataCollector nuevo. Se llama una vez por partida."""
    return DataCollector(
        model_reporters=_model_reporters(),
        agent_reporters=_agent_reporters(),
    )


# =========================================================================
# 4. UNA PARTIDA COMPLETA
# =========================================================================

def run_single_game(model, max_steps=300, collector=None, verbose=False):
    """Corre `model` hasta que termine (VICTORIA/DERROTA) o se alcance
    max_steps, recolectando estado en cada paso. No modifica model.py:
    llama a model.step() desde afuera, como cualquier script normal.

    Devuelve (model, collector).
    """
    collector = collector or build_collector()
    collector.collect(model)  # estado inicial, antes del turno 1

    if not verbose:
        import io
        import contextlib
        sink = io.StringIO()

    while model.running and model.steps < max_steps:
        if verbose:
            model.step()
        else:
            with contextlib.redirect_stdout(sink):
                model.step()
        collector.collect(model)

    return model, collector


def summarize_run(model, collector):
    """Convierte una partida ya corrida en una sola fila de métricas finales."""
    df = collector.get_model_vars_dataframe()
    final = df.iloc[-1]

    if model.estado_juego == "VICTORIA":
        causa_fin = "VICTORIA"
    elif model.victimas_perdidas >= 4:
        causa_fin = "DERROTA_VICTIMAS"
    elif model.marcadores_dano <= 0:
        causa_fin = "DERROTA_COLAPSO"
    else:
        causa_fin = "TIMEOUT"  # llegó a max_steps sin resolverse (normal sin agentes)

    return {
        "Win": model.estado_juego == "VICTORIA",
        "CausaFin": causa_fin,
        "StepsTotales": int(final["Steps"]),
        "DañoRestante": int(final["DamageMarkers"]),
        "DañoTomado": int(final["DamageTaken"]),
        "VictimasSalvadas": int(final["VictimsSaved"]),
        "VictimasPerdidas": int(final["VictimsLost"]),
        "FuegoFinal": int(final["FireCells"]),
        "HumoFinal": int(final["SmokeCells"]),
        "ParedesDestruidas": int(final["WallsDestroyed"]),
        "PuertasAbiertas": int(final["DoorsOpen"]),
    }


# =========================================================================
# 5. BATCH DE PARTIDAS
# =========================================================================
#
# Hoy (sin agentes) esto sirve para medir la dinámica del fuego/tablero
# solo: p. ej. cuántos pasos tarda en colapsar el edificio, qué tan seguido
# se pierden víctimas por el fuego solo, etc. Cuando exista agents.py, esto
# mismo sirve para comparar estrategias/número de bomberos: solo hay que
# pasar distintos valores de numAgents (o cualquier otro parámetro que
# agregue tu compañero al constructor) por model_kwargs.
#
# Para sweeps de parámetros más adelante (varios valores de numAgents a la
# vez, corridas en paralelo, etc.) esto se puede reemplazar por
# mesa.batchrunner.batch_run, que ya es compatible con este modelo porque
# Mesa rastrea solo `model.steps` y `model.running`. Ejemplo comentado al
# final del archivo.


def run_batch(model_cls, n_iterations=30, max_steps=300, seed=None, **model_kwargs):
    """Corre n_iterations partidas independientes y devuelve un DataFrame
    con una fila de resumen por partida (para pandas/seaborn, como en el
    notebook de RobotSweep)."""
    if seed is not None:
        random.seed(seed)

    filas = []
    for i in range(n_iterations):
        model = model_cls(**model_kwargs)
        model, collector = run_single_game(model, max_steps=max_steps)
        fila = summarize_run(model, collector)
        fila["Iteracion"] = i
        filas.append(fila)

    return pd.DataFrame(filas)


def batch_summary_stats(df_batch):
    """Estadísticas agregadas rápidas sobre un DataFrame de run_batch()."""
    stats = {
        "n_partidas": len(df_batch),
        "win_rate": df_batch["Win"].mean(),
        "steps_promedio": df_batch["StepsTotales"].mean(),
        "steps_std": df_batch["StepsTotales"].std(),
        "daño_tomado_promedio": df_batch["DañoTomado"].mean(),
        "victimas_perdidas_promedio": df_batch["VictimasPerdidas"].mean(),
        "distribucion_causa_fin": Counter(df_batch["CausaFin"]),
    }
    return stats


# =========================================================================
# Ejemplo de uso (ejecutar este archivo directamente):
# =========================================================================
if __name__ == "__main__":
    from model import FlashPointModel

    # --- Una sola partida, con el detalle paso a paso ---
    modelo = FlashPointModel(numAgents=0, width=10, height=8)
    modelo, collector = run_single_game(modelo, max_steps=200)

    df_pasos = collector.get_model_vars_dataframe()
    print(df_pasos.tail())
    print("\nResumen de la partida:")
    print(summarize_run(modelo, collector))

    # --- Batch de varias partidas ---
    df_batch = run_batch(FlashPointModel, n_iterations=20, max_steps=200,
                          numAgents=0, width=10, height=8)
    print("\nBatch de 20 partidas:")
    print(df_batch.head())
    print("\nEstadísticas agregadas:")
    print(batch_summary_stats(df_batch))

    # --- Ejemplo (para más adelante, con mesa.batchrunner.batch_run) ---
    # from mesa.batchrunner import batch_run
    # resultados = batch_run(
    #     FlashPointModel,
    #     parameters={"numAgents": [2, 4, 6], "width": 10, "height": 8},
    #     iterations=20,
    #     max_steps=200,
    #     number_processes=1,
    #     data_collection_period=-1,  # solo el último paso de cada corrida
    # )
    # df_sweep = pd.DataFrame(resultados)