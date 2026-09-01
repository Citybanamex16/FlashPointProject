using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

public class PythonApiService
{
    private const string URL = "http://127.0.0.1:5000/api/process";

    public async Task<PythonResponse> SendDataToPythonAsync(PlayerDataPayload payload)
    {
        // 1. Convertimos el objeto C# a String JSON
        string jsonString = JsonUtility.ToJson(payload);
        byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonString);

        // 2. Preparamos la petición HTTP POST
        using (UnityWebRequest request = new UnityWebRequest(URL, "POST"))
        {
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            // 3. Enviamos y esperamos asíncronamente (sin congelar el juego a 60 FPS)
            var operation = request.SendWebRequest();
            while (!operation.isDone)
            {
                await Task.Yield(); // Cede el control en cada frame hasta completar
            }

            // 4. Verificamos errores de red
            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[API Error]: {request.error}");
                return null;
            }

            // 5. Convertimos el JSON de respuesta devuelto por Python en nuestro Modelo C#
            string jsonResponse = request.downloadHandler.text;
            return JsonUtility.FromJson<PythonResponse>(jsonResponse);
        }
    }
}