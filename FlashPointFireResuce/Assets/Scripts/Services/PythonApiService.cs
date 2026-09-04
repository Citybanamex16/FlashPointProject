using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

public class PythonApiService
{
    private const string URL = "http://127.0.0.1:5000/api/process";

     public async Task<SetupDTO> requestSetupDTO(){
        using (UnityWebRequest request = UnityWebRequest.Get(URL)){
            // 1. Enviamos y esperamos asíncronamente
            var operation = request.SendWebRequest();
            while (!operation.isDone)
            {
                await Task.Yield(); 
            }

            // 2. Verificamos SI HUBO ERRORES (de red, de conexión, o si Python explotó)
            // Usamos la forma moderna de Unity para checar errores
            if (request.result == UnityWebRequest.Result.ConnectionError || 
                request.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"❌ [API Error de Red/Servidor]: {request.error}");
                return null;
            }

            // 3. Si todo salió bien, ahora SÍ es 100% seguro leer el texto
            string jsonResponse = request.downloadHandler.text;
            
            // Imprimimos en consola para que veas el JSON real que mandó Python
            Debug.Log($"⬇️ JSON RECIBIDO CON ÉXITO: {jsonResponse}");

            // 4. Convertimos el JSON a tu clase de C#
            return JsonUtility.FromJson<SetupDTO>(jsonResponse);
        }
    }

}