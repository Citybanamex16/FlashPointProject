using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class BoardManager : MonoBehaviour{

    [Header("Referencias de Componentes")]
    [SerializeField] private PythonApiService apiService;

    [Header("Configuración de Simulación")]
    [SerializeField] public float stepDelay = 2.0f;
    [SerializeField] public bool autoStep = true;

    // Diccionarios de referencia a las Vistas de la escena
    private Dictionary<Vector2Int, NodeView> _nodeViews;
    private Dictionary<string, EdgeView> _edgeViews;

    /// <summary>
    /// Llamado por el GameMaster/GameController tras recibir el SetupDTO inicial.
    /// </summary>

    public void InitializeSimulation(Dictionary<Vector2Int, NodeView> nodesMap, Dictionary<string, EdgeView> edgesMap){
        print("Initializing Simulation");
        _nodeViews = nodesMap;
        _edgeViews = edgesMap;

        // 2. Iniciamos el bucle de ticks HTTP
        if (autoStep)
        {
            StartCoroutine(SimulationLoop());
        }
    }

    private IEnumerator SimulationLoop(){
        while (autoStep)
        {
            yield return new WaitForSeconds(stepDelay);

            // Petición HTTP asíncrona hacia Python para procesar el paso
            yield return apiService.RequestStepDTO((stepDTO) => 
            {
                if (stepDTO != null)
                {
                    ApplyStepUpdates(stepDTO);
                }
            });
        }
    }

    /// <summary>
    /// Sincroniza la vista de Unity con los cambios del StepDTO de Python.
    /// </summary>
    private void ApplyStepUpdates(SetupDTO stepDTO)
    {
        // 1. Actualizamos estado de casillas 
        foreach (var nodeData in stepDTO.nodes)
        {
            Vector2Int key = new Vector2Int(nodeData.x, nodeData.y);
            if (_nodeViews.TryGetValue(key, out NodeView view))
            {
                view.UpdateState(nodeData);
            }
        }

        // 2. Actualizamos estado de aristas (salud de muros, estado de puertas)
        foreach (var edgeData in stepDTO.edges)
        {
            string key = boardBuilder.GetEdgeKey(edgeData.posA.x, edgeData.posA.y, edgeData.posB.x, edgeData.posB.y);
            if (_edgeViews.TryGetValue(key, out EdgeView view))
            {
                view.UpdateState(edgeData);
            }
        }
    }
}
