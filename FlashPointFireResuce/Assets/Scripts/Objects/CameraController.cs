using UnityEngine;

[RequireComponent(typeof(Camera))]
public class CameraController : MonoBehaviour
{
    [Header("Configuración de Ajuste")]
    [SerializeField] private float padding = 1.0f; // Espacio extra alrededor del tablero
    
    private Camera _cam;

    private void Awake()
    {
        _cam = GetComponent<Camera>();
        _cam.orthographic = true; // Aseguramos que la cámara sea ortográfica
    }

    /// <summary>
    /// Centra y escala la cámara según las dimensiones del mapa DTO.
    /// </summary>
    public void AdjustCameraToBoard(int width, int height, float cellSize){
        float centerX = ((width - 1) * cellSize) / 2.0f;
        float centerZ = ((height - 1) * cellSize) / 2.0f;

        // 1. Inclinación deseada (ej. 60 grados hacia abajo)
        float cameraAngleX = 120f; 
        
        // 2. Posicionamos la cámara sobre el centro pero retrasada en Z para compensar la inclinación
        float heightY = 12f; 
        float offsetZ = centerZ - (heightY / Mathf.Tan(cameraAngleX * Mathf.Deg2Rad));

        transform.position = new Vector3(centerX, heightY, offsetZ);
        transform.rotation = Quaternion.Euler(cameraAngleX, 0f, 0f);

        // 3. Ajuste de zoom ortográfico con margen
        float totalWorldWidth = width * cellSize;
        float totalWorldDepth = height * cellSize;

        float halfDepth = totalWorldDepth / 2.0f;
        float halfWidth = (totalWorldWidth / 2.0f) / _cam.aspect;

        _cam.orthographicSize = Mathf.Max(halfDepth, halfWidth) + padding;
    }
}