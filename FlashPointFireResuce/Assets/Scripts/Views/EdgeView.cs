using UnityEngine;

public class EdgeView : MonoBehaviour
{

    public void SetInitialState(EdgeDTO dto) => UpdateState(dto);

    public virtual void UpdateState(EdgeDTO dto)
    {
        print("Edge receiving update: " + dto);
    }
}