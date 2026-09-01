using UnityEngine;

public class GameController : MonoBehaviour
{
    [SerializeField] private GameView view; // Referencia a la Vista en escena
    private PythonApiService _apiService;

    private void Awake()
    {
        _apiService = new PythonApiService();
    }

    public async void requestPythonDataUpdate()
    {
        // 1. Leemos los datos de la Vista
        PlayerDataPayload payload = new PlayerDataPayload
        {
            playerName = view.PlayerName,
            score = view.Score
        };

        // 2. Activamos Spinner
        view.SetLoadingState(true);

        // 3. Solicitamos el servicio de red
        PythonResponse response = await _apiService.SendDataToPythonAsync(payload);

        // 4. Quitamos el Spinner
        view.SetLoadingState(false);

        if (response != null)
        {
            view.DisplayStatus(response.message);
        }
        else
        {
            view.DisplayStatus("Error al conectar con Python.");
        }
    }
}
