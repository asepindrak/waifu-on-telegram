' Background Silent Launcher for AI Girlfriend Telegram Bot
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' 1. Start Music Server if present
If FSO.FileExists(ScriptDir & "\music_player_server.js") Then
    WshShell.Run "cmd /c node """ & ScriptDir & "\music_player_server.js""", 0, False
End If

' 2. Start Python Bot
WshShell.Run "cmd /c python """ & ScriptDir & "\bot.py""", 0, False
