using UnityEngine;

public class EdgeView : MonoBehaviour
{
    [Header("Referencias 3D/2D")]
    [SerializeField] private GameObject modeloPuertaCerrada;
    [SerializeField] private GameObject modeloPuertaAbierta;
    [SerializeField] private GameObject modeloMuroDestruido;

    public void SetInitialState(EdgeDTO dto) => UpdateState(dto);

    public void UpdateState(EdgeDTO dto)
    {
        if (dto.tipo == "PUERTA")
        {
            // Oculta/muestra el modelo 3D de la puerta según el estado booleano
            modeloPuertaCerrada.SetActive(dto.cerrado);
            modeloPuertaAbierta.SetActive(!dto.cerrado);
        }
        else if (dto.tipo == "MURO")
        {
            // Si la salud del muro llegó a 0, mostramos la versión destruida
            if (dto.hp <= 0 && modeloMuroDestruido != null)
            {
                modeloMuroDestruido.SetActive(true);
            }
        }
    }
}