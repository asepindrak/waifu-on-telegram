' Background Silent Launcher for Waifu on Telegram Bot
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = ScriptDir

' 1. Start KoboldCPP Engine if present & model available
If FSO.FileExists(ScriptDir & "\tools\koboldcpp.exe") Then
    Dim modelFile
    modelFile = ""
    If FSO.FileExists(ScriptDir & "\models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf") Then
        modelFile = ScriptDir & "\models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
    ElseIf FSO.FolderExists(ScriptDir & "\models") Then
        For Each f In FSO.GetFolder(ScriptDir & "\models").Files
            If LCase(FSO.GetExtensionName(f.Name)) = "gguf" And InStr(LCase(f.Name), "mmproj") = 0 Then
                modelFile = f.Path
                Exit For
            End If
        Next
    End If
    If modelFile <> "" Then
        Dim portCheck
        portCheck = WshShell.Run("powershell -NoProfile -Command ""$t = New-Object System.Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1', 5001); $t.Close(); exit 0 } catch { exit 1 }""", 0, True)
        If portCheck <> 0 Then
            WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && tools\koboldcpp.exe --model """ & modelFile & """ --gpulayers 99 --port 5001 --usecublas normal --quiet", 0, False
            WScript.Sleep 4000
        End If
    End If
End If

' 2. Start Music Server if present
If FSO.FileExists(ScriptDir & "\music_player_server.js") Then
    WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && node music_player_server.js", 0, False
End If

' 3. Start Python Bot
WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && python bot.py", 0, False
