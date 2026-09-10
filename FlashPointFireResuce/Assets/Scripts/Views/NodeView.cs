using UnityEngine;

public class NodeView : MonoBehaviour
{
    [Header("Referencias a Assets Visuales")]
    [SerializeField] private GameObject zombieRender;
    [SerializeField] private GameObject cordycepsRender;
    [SerializeField] private GameObject victimaIcono;
    [SerializeField] private GameObject falsaAlarmaIcono;


    void Awake(){
        cordycepsRender.gameObject.SetActive(false);
        zombieRender.gameObject.SetActive(false);
        victimaIcono.SetActive(false);
        falsaAlarmaIcono.SetActive(false);
    }

    public void SetInitialState(NodeDTO dto)
    {
        UpdateState(dto);
    }

    public void UpdateState(NodeDTO dto)
    {
        // 1. Manejo de Infección (Fuego -> Esporas/Zombies)
        
        switch (dto.fuego)
        {
            case "LIMPIO":
                cordycepsRender.gameObject.SetActive(false);
                zombieRender.gameObject.SetActive(false);
                break;
            case "HUMO": // Primer nivel: Esporas en el aire
                cordycepsRender.gameObject.SetActive(true);
                //cordycepsRender.color = new Color(0.6f, 0.8f, 0.2f, 0.6f); // Tinte verde tóxico translúcido
                zombieRender.gameObject.SetActive(false);
                break;
            case "FUEGO": // Segundo nivel: Brote activo / Horda
                cordycepsRender.gameObject.SetActive(false);
                //cordycepsRender.color = new Color(0.6f, 0.1f, 0.1f, 0.9f); // Tinte rojizo oscuro (infección severa)
                zombieRender.gameObject.SetActive(true);
                break;
        }

        // 2. Manejo de Puntos de Interés (Víctimas)
        victimaIcono.SetActive(false);
        falsaAlarmaIcono.SetActive(false);

        if (dto.poi != null && !string.IsNullOrEmpty(dto.poi.tipo))
        {
            print(dto);

            if (!dto.poi.revelado)
            {
                victimaIcono.SetActive(true);
                print("setting victima Icon en " + gameObject.name);
            }
            else
            {
             print("Error");
        }
    }
}

}