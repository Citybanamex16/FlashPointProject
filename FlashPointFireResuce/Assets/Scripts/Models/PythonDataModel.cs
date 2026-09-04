using System;
using System.Collections.Generic;

// ==========================================
// 1. ESTRUCTURAS AUXILIARES / PRIMITIVOS
// ==========================================

[Serializable]
public class Vector2DTO
{
    public int x;
    public int y;
}

[Serializable]
public class PoiDTO
{
    public string tipo;      // "VICTIMA" o "FALSA_ALARMA"
    public bool revelado;
}

// ==========================================
// 2. ELEMENTOS DEL TABLERO (NODOS Y ARISTAS)
// ==========================================

[Serializable]
public class NodeDTO
{
    public int x;
    public int y;
    public string fuego;     // "LIMPIO", "HUMO", "FUEGO"
    public PoiDTO poi;       // Objeto anidado (null si no hay POI)
}

[Serializable]
public class EdgeDTO
{
    public Vector2DTO posA;  // {"x": 0, "y": 1}
    public Vector2DTO posB;  // {"x": 1, "y": 1}
    public string tipo;      // "MURO" o "PUERTA"
    
    // Propiedades opcionales según el tipo de arista
    public bool cerrado;     // Solo para Puertas
    public int hp;           // Solo para Muros
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
}