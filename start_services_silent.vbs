' Background Silent Launcher for Waifu on Telegram Bot
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = ScriptDir

' 1. Start Music Server if present
If FSO.FileExists(ScriptDir & "\music_player_server.js") Then
    WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && node music_player_server.js", 0, False
End If

' 2. Start Python Bot
WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && python bot.py", 0, False
