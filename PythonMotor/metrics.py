"""
metrics.py - Medición y ejecución de múltiples partidas.
"""

import random

import pandas as pd
from mesa.datacollection import DataCollector

from core_types import EstadoFuego, POI, Muro, Puerta
from agents import AgentAction, AgentStatus, Role
from model import FlashPointModel


# ============================================================
# CONTADORES
# ============================================================

def _contar_estado_fuego(model, estado):
    return sum(
        1
        for nodo in model.mapa_nodos.values()
        if nodo.estado_fuego == estado
    )


def _iterar_aristas_unicas(model):
    procesadas = set()

    for nodo in model.mapa_nodos.values():
        for _vecino, arista in nodo.vecinos.items():
            if arista is not None and arista not in procesadas:
                procesadas.add(arista)
                yield arista


def _contar_paredes(model):
    intactos = 0
    danados = 0
    destruidos = 0

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
    abiertas = 0
    cerradas = 0

    for arista in _iterar_aristas_unicas(model):
        if isinstance(arista, Puerta):
            if arista.cerrado:
                cerradas += 1
            else:
                abiertas += 1

    return abiertas, cerradas


def _contar_pois(model):
    activos = 0
    revelados = 0

    for nodo in model.mapa_nodos.values():
        for item in nodo.contenido:
            if isinstance(item, POI):
                activos += 1

                if item.revelado:
                    revelados += 1

    return activos, revelados


def _contar_accion(agente, accion):
    return sum(
        1 for accion_turno in agente.acciones_turno
        if accion_turno == accion
    )


def _contar_roles(model, role):
    return sum(1 for agente in model.agents if agente.role == role)


def _contar_estados(model, estado):
    return sum(1 for agente in model.agents if agente.estado == estado)


def _totales_acciones(model):
    agent_data = model.datacollector.get_agent_vars_dataframe()
    if agent_data.empty:
        return {}

    action_columns = {
        "TotalMoves": "MovesThisTurn",
        "TotalExtinguishes": "ExtinguishesThisTurn",
        "TotalPickups": "PickupsThisTurn",
        "TotalRescues": "RescuesThisTurn",
        "TotalKnockdowns": "KnockdownsThisTurn",
    }
    return {
        total_name: int(agent_data[column].sum())
        for total_name, column in action_columns.items()
    }


def _motivo_fin(model):
    if model.estado_juego == "VICTORIA":
        return "VICTORIA"
    if model.marcadores_dano <= 0:
        return "COLAPSO"
    if model.victimas_perdidas >= 4:
        return "VICTIMAS_PERDIDAS"
    return "LIMITE"


# ============================================================
# DATA COLLECTOR
# ============================================================

def build_collector():

    def _walls(model):
        return _contar_paredes(model)

    def _pois(model):
        return _contar_pois(model)

    return DataCollector(
        model_reporters={
            "Steps": lambda m: m.steps,
            "FireAdvances": lambda m: m.fire_advances,
            "AgentTurns": lambda m: m.fire_advances,
            "DamageMarkers": lambda m: m.marcadores_dano,
            "VictimsSaved": lambda m: m.victimas_salvadas,
            "VictimsLost": lambda m: m.victimas_perdidas,
            "GameState": lambda m: m.estado_juego,
            "FireCells": lambda m: _contar_estado_fuego(
                m,
                EstadoFuego.FUEGO
            ),
            "SmokeCells": lambda m: _contar_estado_fuego(
                m,
                EstadoFuego.HUMO
            ),
            "CleanCells": lambda m: _contar_estado_fuego(
                m,
                EstadoFuego.LIMPIO
            ),
            "WallsDestroyed": lambda m: _walls(m)[2],
            "WallsDamaged": lambda m: _walls(m)[1],
            "DoorsOpen": lambda m: _contar_puertas(m)[0],
            "DoorsClosed": lambda m: _contar_puertas(m)[1],
            "ActivePOIs": lambda m: _pois(m)[0],
            "RevealedPOIs": lambda m: _pois(m)[1],
            "Searchers": lambda m: _contar_roles(m, Role.SEARCHER),
            "Soldiers": lambda m: _contar_roles(m, Role.SOLDIER),
            "KnockedDown": lambda m: _contar_estados(
                m,
                AgentStatus.KNOCKED_DOWN
            ),
            "CarryingVictims": lambda m: sum(
                1 for agente in m.agents if agente.llevando_victima
            ),
        },

        agent_reporters={
            "Role": lambda a: a.role.value,
            "Status": lambda a: a.estado.value,
            "RoleLocked": lambda a: a.role_bloqueado,
            "TurnsWithoutProgress": lambda a: getattr(
                a,
                "turns_without_progress",
                0
            ),
            "CarryingVictim": lambda a: a.llevando_victima,
            "AP_Remaining": lambda a: a.ap,
            "Saved_AP": lambda a: a.saved_ap,
            "APMoving": lambda a: a.ap_gastado_moviendo,
            "APActing": lambda a: a.ap_gastado_actuando,
            "KnockedDownCarrying": lambda a: a.knocked_down_carrying_victim,
            "MovesThisTurn": lambda a: _contar_accion(
                a,
                AgentAction.MOVE
            ),
            "ExtinguishesThisTurn": lambda a: _contar_accion(
                a,
                AgentAction.EXTINGUISH
            ),
            "PickupsThisTurn": lambda a: _contar_accion(
                a,
                AgentAction.PICK_UP_VICTIM
            ),
            "RescuesThisTurn": lambda a: _contar_accion(
                a,
                AgentAction.RESCUE_VICTIM
            ),
            "KnockdownsThisTurn": lambda a: _contar_accion(
                a,
                AgentAction.KNOCKED_DOWN
            ),
        }
    )


class MeasuredFlashPointModel(FlashPointModel):
    """Modelo FlashPoint con recolección de métricas."""

    def __init__(self, **kwargs):
        # No imprimir eventos durante batch runs
        kwargs["verbose"] = False

        super().__init__(**kwargs)

        self.fire_advances = 0

        self.datacollector = build_collector()
        self.datacollector.collect(self)

    def avanzar_fuego(self):
        self.fire_advances += 1
        super().avanzar_fuego()

    def step(self):
        super().step()
        self.datacollector.collect(self)


# ============================================================
# EJECUTAR UNA PARTIDA
# ============================================================

def ejecutar_partida(
    game_number,
    total_games,
    max_steps=300,
    seed=None
):
    """
    Ejecuta una partida completa y muestra su resultado.
    """ 

    if seed is not None:
        random.seed(seed)

    model = MeasuredFlashPointModel(
        numAgents=6,
        width=10,
        height=8,
    )

    steps = 0

    while (
        model.estado_juego == "EN_CURSO"
        and steps < max_steps
    ):
        model.step()
        steps += 1

    # Determinar resultado
    estado = model.estado_juego

    if estado == "VICTORIA":
        resultado = "VICTORIA"
    elif estado == "DERROTA":
        resultado = "DERROTA"
    else:
        resultado = "LIMITE"

    # print(
    #     f"Game {game_number:>2}/{total_games} | "
    #     f"{resultado:<8} | "
    #     f"{steps:>3} turns | "
    #     f"Saved: {model.victimas_salvadas} | "
    #     f"Lost: {model.victimas_perdidas}"
    # )

    return model


# ============================================================
# BATCH RUN
# ============================================================

def ejecutar_batch(
    num_games=1000,
    max_steps=300,
    base_seed=None
):
    """
    Ejecuta múltiples partidas y muestra estadísticas generales.
    """

    print("=" * 60)
    print(f"RUNNING {num_games} GAMES")
    print(f"BASE SEED:  {base_seed}")
    print("=" * 60)

    modelos = []

    for game_number in range(1, num_games + 1):
        game_seed = (
            None
            if base_seed is None
            else base_seed + game_number - 1
        )
        model = ejecutar_partida(
            game_number,
            num_games,
            max_steps,
            seed=game_seed
        )

        modelos.append((game_seed, model))

    # --------------------------------------------------------
    # Crear DataFrame con resultados finales
    # --------------------------------------------------------

    resultados = []

    for game_seed, model in modelos:
        resultados.append({
            "Seed": game_seed,
            "Steps": model.steps,
            "DamageMarkers": model.marcadores_dano,
            "VictimsSaved": model.victimas_salvadas,
            "VictimsLost": model.victimas_perdidas,
            "GameState": model.estado_juego,
            "EndReason": _motivo_fin(model),
            "FireAdvances": model.fire_advances,
            "AgentTurns": model.fire_advances,
            "FireCells": _contar_estado_fuego(
                model,
                EstadoFuego.FUEGO
            ),
            "SmokeCells": _contar_estado_fuego(
                model,
                EstadoFuego.HUMO
            ),
            "CleanCells": _contar_estado_fuego(
                model,
                EstadoFuego.LIMPIO
            ),
            "WallsDestroyed": _contar_paredes(model)[2],
            "WallsDamaged": _contar_paredes(model)[1],
            "DoorsOpen": _contar_puertas(model)[0],
            "DoorsClosed": _contar_puertas(model)[1],
            "ActivePOIs": _contar_pois(model)[0],
            "RevealedPOIs": _contar_pois(model)[1],
            "Searchers": _contar_roles(model, Role.SEARCHER),
            "Soldiers": _contar_roles(model, Role.SOLDIER),
            "KnockedDown": _contar_estados(
                model,
                AgentStatus.KNOCKED_DOWN
            ),
            "CarryingVictims": sum(
                1 for agente in model.agents if agente.llevando_victima
            ),
        })
        resultados[-1].update(_totales_acciones(model))

    df = pd.DataFrame(resultados)

    agent_df = pd.concat(
        [m.datacollector.get_agent_vars_dataframe() for _, m in modelos],
        keys=[seed for seed, _ in modelos],
        names=["Seed", "Step", "AgentID"],
    )

    final_agents = (
        agent_df
        .groupby(level=["Seed", "AgentID"])
        .tail(1)
        .reset_index()
    )

    stuck_by_game = final_agents.groupby("Seed")[
        "TurnsWithoutProgress"
    ].max()
    df["MaxAgentTurnsWithoutProgress"] = df["Seed"].map(stuck_by_game)
    df["AvgAgentTurnsWithoutProgress"] = (
        final_agents.groupby("Seed")["TurnsWithoutProgress"]
        .mean()
        .reindex(df["Seed"])
        .values
    )

    print()
    print("TURNS WITHOUT PROGRESS (per agent, final value)")
    print(df.groupby("GameState")[[
        "MaxAgentTurnsWithoutProgress",
        "AvgAgentTurnsWithoutProgress",
    ]].mean().round(2))

    # Attach each game's final state to every final agent row, then compare
    # cumulative AP usage and carrier knockdowns by outcome.
    final_agents["GameState"] = final_agents["Seed"].map(
        df.set_index("Seed")["GameState"]
    )

    print()
    print("FINAL AGENT THROUGHPUT (per agent, cumulative)")
    print(
        final_agents.groupby("GameState")[
            ["APMoving", "APActing", "KnockedDownCarrying"]
        ].mean().round(2)
    )


    # ========================================================
    # AP NORMALIZADO POR TURNO DE AGENTE
    # ========================================================

    totals_by_game = (
        final_agents
        .groupby("Seed")[
            ["APMoving", "APActing", "KnockedDownCarrying"]
        ]
        .sum()
    )

    normalized = (
        df.set_index("Seed")
        .join(totals_by_game)
    )

    normalized["APMovingPerTurn"] = (
        normalized["APMoving"] / normalized["FireAdvances"]
    )

    normalized["APActingPerTurn"] = (
        normalized["APActing"] / normalized["FireAdvances"]
    )

    total_spent = (
        normalized["APMoving"]
        + normalized["APActing"]
    )

    normalized["MovementShare"] = (
        normalized["APMoving"] / total_spent
    )

    pickup_denominator = normalized["TotalPickups"].where(
        normalized["TotalPickups"] > 0
    )

    normalized["CarrierKOPerPickup"] = (
        normalized["KnockedDownCarrying"]
        / pickup_denominator
    )

    print()
    print("NORMALIZED THROUGHPUT")
    print(
        normalized.groupby("EndReason")[
            [
                "APMovingPerTurn",
                "APActingPerTurn",
                "MovementShare",
                "CarrierKOPerPickup",
            ]
        ].mean().round(3)
    )
    # ========================================================
    # RESUMEN
    # ========================================================

    victories = (df["GameState"] == "VICTORIA").sum()
    defeats = (df["GameState"] == "DERROTA").sum()
    limits = (df["GameState"] == "LIMITE").sum()

    win_rate = (victories / num_games) * 100

    print()
    print("=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)

    print(f"Games:       {num_games}")
    print(f"Victories:   {victories}")
    print(f"Defeats:     {defeats}")
    print(f"Limit:       {limits}")
    print(f"Win rate:    {win_rate:.1f}%")

    print()
    print(f"Avg turns:   {df['Steps'].mean():.1f}")
    print(f"Avg agent turns: {df['AgentTurns'].mean():.1f}")
    print(f"Avg saved:   {df['VictimsSaved'].mean():.2f}")
    print(f"Avg lost:    {df['VictimsLost'].mean():.2f}")
    print(f"Avg damage:  {df['DamageMarkers'].mean():.2f}")
    print(f"Avg fire:    {df['FireCells'].mean():.2f}")
    print(
        f"Avg walls destroyed: "
        f"{df['WallsDestroyed'].mean():.2f}"
    )
    print("End reasons:")
    for reason, count in df["EndReason"].value_counts().items():
        print(f"  {reason}: {count}")

    print("=" * 60)

    return df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    df_batch = ejecutar_batch(
        num_games=1000,
        max_steps=300,
        base_seed=20260910
    )

    print()
    print("FINAL RESULTS:")
    print(df_batch)
