using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

public class PythonApiService
{
    private const string URL = "http://127.0.0.1:5000/api/process";

      public async Task<SetupDTO> requestSetupDTO(){

        // 1. Preparamos la petición HTTP POST
        using (UnityWebRequest request = new UnityWebRequest(URL, "GET"))
        {
            // 2. Enviamos y esperamos asíncronamente (sin congelar el juego a 60 FPS)
            var operation = request.SendWebRequest();
            while (!operation.isDone)
            {
                await Task.Yield(); // Cede el control en cada frame hasta completar
            }

            // 3. Verificamos errores de red
            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[API Error]: {request.error}");
                return null;
            }

            // 5. Convertimos el JSON de respuesta devuelto por Python en nuestro Modelo C#
            string jsonResponse = request.downloadHandler.text;
            return JsonUtility.FromJson<SetupDTO>(jsonResponse);
        }
    }
}