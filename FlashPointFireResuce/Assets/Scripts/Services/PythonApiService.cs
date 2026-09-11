using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

public class PythonApiService
{
    private const string INIT_URL = "http://127.0.0.1:5000/api/init";
    private const string STEP_URL = "http://127.0.0.1:5000/api/step";

     public async Task<SetupDTO> requestSetupDTO(){
        using (UnityWebRequest request = UnityWebRequest.Get(INIT_URL)){
            // 1. Enviamos y esperamos asíncronamente
            var operation = request.SendWebRequest();
            while (!operation.isDone)
            {
                await Task.Yield(); 
            }

            // 2. Verificamos SI HUBO ERRORES (de red, de conexión, o si Python explotó)
            if (request.result == UnityWebRequest.Result.ConnectionError || 
                request.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"❌ [API Error de Red/Servidor]: {request.error}");
                return null;
            }

            // 3. Si todo salió bien, ahora SÍ es seguro leer el texto
            string jsonResponse = request.downloadHandler.text;
            
            // Imprimimos en consola para que se vea el JSON real que mandó Python
            Debug.Log($"⬇️ JSON RECIBIDO CON ÉXITO: {jsonResponse}");

            // 4. Convertimos el JSON a la clase de C#
            return JsonUtility.FromJson<SetupDTO>(jsonResponse);
        }
    }

    public async Task<StepDTO> requestStepDTO(){
        using (UnityWebRequest request = UnityWebRequest.Get(STEP_URL)){
            var operation = request.SendWebRequest();
            while (!operation.isDone)
            {
                await Task.Yield(); 
            }

            if (request.result == UnityWebRequest.Result.ConnectionError || 
                request.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"❌ [API Error de Red/Servidor]: {request.error}");
                return null;
            }

            // 3. Si todo salió bien, ahora SÍ es 100% seguro leer el texto
            string jsonResponse = request.downloadHandler.text;
            
            // Imprimimos en consola para que veas el JSON real que mandó Python
            //Debug.Log($"⬇️ JSON RECIBIDO CON ÉXITO: {jsonResponse}");

            // 4. Convertimos el JSON a tu clase de C#
            return JsonUtility.FromJson<StepDTO>(jsonResponse);
        }
    }

}