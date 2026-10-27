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

' 2. Start ComfyUI Generator if present and port 8188 not active
Dim portCheck8188
portCheck8188 = WshShell.Run("powershell -NoProfile -Command ""$t = New-Object System.Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1', 8188); $t.Close(); exit 0 } catch { exit 1 }""", 0, True)
If portCheck8188 <> 0 Then
    Dim comfyCheck
    comfyCheck = WshShell.Run("python -c ""import asset_manager; spec = asset_manager.get_comfyui_launch_spec(); exit(0 if spec else 1)""", 0, True)
    If comfyCheck = 0 Then
        WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && python -c ""import asset_manager, subprocess; spec = asset_manager.get_comfyui_launch_spec(); subprocess.run(spec['cmd'], cwd=spec['cwd'])""", 0, False
        WScript.Sleep 4000
    End If
End If

' 3. Start Music Server if present
Dim nodeCmd
nodeCmd = "node"
If FSO.FileExists(ScriptDir & "\tools\nodejs\node.exe") Then
    nodeCmd = """" & ScriptDir & "\tools\nodejs\node.exe"""
End If
If FSO.FileExists(ScriptDir & "\music_player_server.js") Then
    WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && " & nodeCmd & " music_player_server.js", 0, False
End If

' 4. Start Python Bot
WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && python bot.py", 0, False
