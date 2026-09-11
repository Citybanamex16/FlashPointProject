using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class GameMaster : MonoBehaviour
{
    [Header("Referencias")]
    public GameView view; // Referencia a la Vista en escena
    public BoardBuilder boardBuilder; //Ref a Manager de Setup
    public BoardManager boardManager;
    private PythonApiService _apiService;

    private bool setupStarted = false;

    private Dictionary<Vector2Int, NodeView> _nodesMapSafe;
    private Dictionary<string, EdgeView> _edgesMapSafe;
    private Dictionary<int, AgentView> _agentsMapSafe;

    private void Awake()
    {
        _apiService = new PythonApiService();
        _nodesMapSafe = new Dictionary<Vector2Int, NodeView>();
        _edgesMapSafe = new Dictionary<string, EdgeView>();
        _agentsMapSafe = new Dictionary<int, AgentView>();

    }

    private void Start(){

        InitMap();

    }



    async private void InitMap(){

        //1. Activamos Spinner
        view.SetLoadingState(true,setupStarted);

        //2. Solicitamos servicio de red 
        SetupDTO response = await _apiService.requestSetupDTO();

        if (response != null)
        {
            var (nodesMap, edgesMap, agentsMap) = boardBuilder.BuildInitialMap(response);
            _nodesMapSafe = nodesMap;
            _edgesMapSafe = edgesMap;
            _agentsMapSafe = agentsMap;
            

            setupStarted = true;

        }
        else
        {
            
            setupStarted = false;
        }

        view.SetLoadingState(false,setupStarted);

    }


    public void initSimulation(){
        //Inicializa la simulacion y las llamadas a Step del python
        view.hideButton();
        boardManager.InitializeSimulation(_nodesMapSafe,_edgesMapSafe,_agentsMapSafe);
    }

}
