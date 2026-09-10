using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

// ==========================================
// 1. ESTRUCTURAS AUXILIARES / PRIMITIVOS
// ==========================================

[Serializable]
public class Vector2DTO
{
    public int x;
    public int y;

    public override string ToString() => $"({x}, {y})";
}

[Serializable]
public class PoiDTO
{
    public string tipo;// "VICTIMA" o "FALSA_ALARMA"
    public bool revelado;

    public override string ToString() => $"{tipo} (Revelado: {revelado})";
}

// ==========================================
// 2. ELEMENTOS DEL TABLERO (NODOS Y ARISTAS)
// ==========================================

[Serializable]
public class NodeDTO
{
    public int x;
    public int y;
    public string fuego;// "LIMPIO", "HUMO", "FUEGO"
    public PoiDTO poi;// Objeto anidado (null si no hay POI)

    public override string ToString()
    {
        string poiStr = (poi != null) ? $" | POI: {poi}" : "";
        return $"[Nodo ({x},{y})] Fuego: {fuego}{poiStr}";
    }
}

[Serializable]
public class EdgeDTO
{
    public Vector2DTO posA;// {"x": 0, "y": 1}
    public Vector2DTO posB;// {"x": 1, "y": 1}
    public string tipo;// "MURO" o "PUERTA"
    
    // Propiedades opcionales según el tipo de arista
    public bool cerrado;// Solo para Puertas
    public int hp;// Solo para Muros

    public override string ToString()
    {
        string detalle = (tipo == "PUERTA") ? $"Cerrado: {cerrado}" : $"HP: {hp}";
        return $"[{tipo}] Entre {posA} y {posB} -> {detalle}";
    }
}


[Serializable]
public class DiceRollDTO
{
    public int x;
    public int y;

    public override string ToString() => $"Dado X: {x}, Dado Y: {y}";
}

// ==========================================
// 3. EL DTO PRINCIPAL (SETUP)
// ==========================================

[Serializable]
public class SetupDTO
{
    public int width;
    public int height;
    public List<NodeDTO> nodes;
    public List<EdgeDTO> edges;

    /// <summary>
    /// Imprime en la Consola de Unity un resumen detallado y con formato del Setup.
    /// </summary>
    public void ImprimirResumen()
    {
        StringBuilder sb = new StringBuilder();

        sb.AppendLine("=========================================");
        sb.AppendLine($"   🔥 FLASHPOINT MAP SETUP DTO ({width}x{height}) 🔥");
        sb.AppendLine("=========================================");

        // --- SECCIÓN NODOS ---
        int totalNodos = nodes != null ? nodes.Count : 0;
        sb.AppendLine($"\n--- NODOS REGISTRADOS ({totalNodos}) ---");
        
        if (nodes != null && totalNodos > 0)
        {
            foreach (var node in nodes)
            {
                sb.AppendLine($"  • {node}");
            }
        }
        else
        {
            sb.AppendLine("  (Sin nodos registrados)");
        }

        // --- SECCIÓN ARISTAS ---
        int totalAristas = edges != null ? edges.Count : 0;
        sb.AppendLine($"\n--- ARISTAS REGISTRADAS ({totalAristas}) ---");

        if (edges != null && totalAristas > 0)
        {
            foreach (var edge in edges)
            {
                sb.AppendLine($"  • {edge}");
            }
        }
        else
        {
            sb.AppendLine("  (Sin aristas registradas)");
        }

        sb.AppendLine("=========================================");

        // Enviamos el bloque completo a la Consola de Unity
        Debug.Log(sb.ToString());
    }
}


// ==========================================
// 4. DTO DE ACTUALIZACIÓN DEL TICK (STEP)
// ==========================================

[Serializable]
public class StepDTO
{
    // Estado Global del Juego (Para la UI)
    public string estado_juego;// "EN_CURSO", "VICTORIA", "DERROTA"
    public int marcadores_dano;
    public int victimas_salvadas;
    public int victimas_perdidas;
    public DiceRollDTO tirada_dados;

    // Listas con los Deltas
    public List<NodeDTO> nodes;
    public List<EdgeDTO> edges;

    /// <summary>
    /// Imprime un resumen de los cambios procesados en el tick.
    /// </summary>
    public void ImprimirResumenStep()
    {
        StringBuilder sb = new StringBuilder();
        sb.AppendLine("=========================================");
        sb.AppendLine($"   ⏱️ STEP TICK UPDATE [{estado_juego}] ⏱️");
        sb.AppendLine($"   Daño: {marcadores_dano} | Salvadas: {victimas_salvadas} | Perdidas: {victimas_perdidas}");
        if (tirada_dados != null) sb.AppendLine($"   🎲 {tirada_dados}");
        sb.AppendLine("=========================================");

        int cambiosNodos = nodes != null ? nodes.Count : 0;
        int cambiosAristas = edges != null ? edges.Count : 0;

        sb.AppendLine($"  • Nodos modificados: {cambiosNodos}");
        sb.AppendLine($"  • Aristas modificadas: {cambiosAristas}");
        sb.AppendLine("=========================================");

        Debug.Log(sb.ToString());
    }
}