using System;

// [Serializable] le indica a Unity que esta clase se puede convertir a JSON string
[Serializable]
public class PlayerDataPayload
{
    public string playerName;
    public int score;
}

[Serializable]
public class PythonResponse
{
    public string status;
    public string playerName;
    public int calculatedLevel;
    public string message;
}