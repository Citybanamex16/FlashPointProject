using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Threading.Tasks;


public class BoardManager : MonoBehaviour{

    private PythonApiService apiService;

    [Header("Configuración de Simulación")]
    public float stepDelay = 2.0f;
    public bool autoStep = true;
    public BoardBuilder boardBuilder;

    // Diccionarios de referencia a las Vistas de la escena
    private Dictionary<Vector2Int, NodeView> _nodeViews;
    private Dictionary<string, EdgeView> _edgeViews;

    private void Awake()
    {
        apiService = new PythonApiService();
    }

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
    while (autoStep){
        yield return new WaitForSeconds(stepDelay);

        // 1. Creamos la tarea de la API
        Task<StepDTO> apiTask = apiService.requestStepDTO();

        // 2. Le decimos a la corrutina que espere a que la tarea termine
        yield return new WaitUntil(() => apiTask.IsCompleted);

        // 3. Cuando llega aquí, la tarea ya terminó. Obtenemos el resultado.
        StepDTO stepDTO = apiTask.Result;

        // 4. Aplicamos los cambios si el modelo es válido
        if (stepDTO != null)
        {
            ApplyStepUpdates(stepDTO);
        }
    }
}


    /// <summary>
    /// Sincroniza la vista de Unity con los cambios del StepDTO de Python.
    /// </summary>
    private void ApplyStepUpdates(StepDTO stepDTO){
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
