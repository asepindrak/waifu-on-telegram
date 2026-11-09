' Background Silent Launcher for Waifu on Telegram Bot
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = ScriptDir

Dim pyCmd
pyCmd = "python"
If FSO.FileExists(ScriptDir & "\.python_path") Then
    Dim pStream
    On Error Resume Next
    Set pStream = FSO.OpenTextFile(ScriptDir & "\.python_path", 1)
    If Not pStream.AtEndOfStream Then
        Dim customPy
        customPy = Trim(pStream.ReadLine)
        If FSO.FileExists(customPy) Then
            pyCmd = customPy
        End If
    End If
    pStream.Close
    On Error GoTo 0
ElseIf FSO.FileExists("C:\Python315\python.exe") Then
    pyCmd = "C:\Python315\python.exe"
End If

' 1. Start KoboldCPP Engine if present & model available & Smart Idle is EXPLICITLY disabled
Dim smartIdleDisabled
smartIdleDisabled = False
If FSO.FileExists(ScriptDir & "\.env") Then
    Dim envStream, envLine
    On Error Resume Next
    Set envStream = FSO.OpenTextFile(ScriptDir & "\.env", 1)
    Do Until envStream.AtEndOfStream
        envLine = LCase(Trim(envStream.ReadLine))
        If InStr(envLine, "smart_idle_enabled=false") > 0 Or InStr(envLine, "smart_idle_enabled=0") > 0 Or InStr(envLine, "smart_idle_enabled=no") > 0 Then
            smartIdleDisabled = True
            Exit Do
        End If
    Loop
    envStream.Close
    On Error GoTo 0
End If

If smartIdleDisabled And FSO.FileExists(ScriptDir & "\tools\koboldcpp.exe") Then
    Dim modelFile, mmprojFile, mmprojArg
    modelFile = ""
    mmprojFile = ""
    mmprojArg = ""
    If FSO.FileExists(ScriptDir & "\models\Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf") Then
        modelFile = ScriptDir & "\models\Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf"
    ElseIf FSO.FileExists(ScriptDir & "\models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf") Then
        modelFile = ScriptDir & "\models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
    ElseIf FSO.FolderExists(ScriptDir & "\models") Then
        For Each f In FSO.GetFolder(ScriptDir & "\models").Files
            If LCase(FSO.GetExtensionName(f.Name)) = "gguf" And InStr(LCase(f.Name), "mmproj") = 0 Then
                modelFile = f.Path
                Exit For
            End If
        Next
    End If

    If InStr(LCase(modelFile), "stheno") = 0 And InStr(LCase(modelFile), "llama") = 0 Then
        If FSO.FileExists(ScriptDir & "\models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf") Then
            mmprojFile = ScriptDir & "\models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf"
        ElseIf FSO.FileExists(ScriptDir & "\models\mmproj-model-bf16.gguf") Then
            mmprojFile = ScriptDir & "\models\mmproj-model-bf16.gguf"
        ElseIf FSO.FolderExists(ScriptDir & "\models") Then
            For Each f In FSO.GetFolder(ScriptDir & "\models").Files
                If LCase(FSO.GetExtensionName(f.Name)) = "gguf" And InStr(LCase(f.Name), "mmproj") > 0 Then
                    mmprojFile = f.Path
                    Exit For
                End If
            Next
        End If
    End If

    If mmprojFile <> "" Then
        mmprojArg = " --mmproj """ & mmprojFile & """"
    End If

    If modelFile <> "" Then
        Dim koboldRunning
        koboldRunning = WshShell.Run("powershell -NoProfile -Command ""if (Get-Process koboldcpp -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }""", 0, True)
        If koboldRunning <> 0 Then
            Dim portCheck
            portCheck = WshShell.Run("powershell -NoProfile -Command ""$t = New-Object System.Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1', 5001); $t.Close(); exit 0 } catch { exit 1 }""", 0, True)
            If portCheck <> 0 Then
                WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && tools\koboldcpp.exe --model """ & modelFile & """" & mmprojArg & " --gpulayers 99 --port 5001 --contextsize 4096 --smartcontext --threads 4 --usecublas normal --quiet", 0, False
                WScript.Sleep 4000
            End If
        End If
    End If
End If

' 2. Start ComfyUI Generator if present and not on-demand
Dim comfyRunning
comfyRunning = WshShell.Run("powershell -NoProfile -Command ""if ((Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' -and $_.CommandLine -like '*8188*' }) -or (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -InformationLevel Quiet -WarningAction SilentlyContinue)) { exit 0 } else { exit 1 }""", 0, True)
If comfyRunning <> 0 Then
    Dim comfyCheck
    comfyCheck = WshShell.Run(pyCmd & " -c ""import os, asset_manager; from dotenv import load_dotenv; load_dotenv(); exit(1 if os.environ.get('COMFYUI_ON_DEMAND','true').lower() in ('1','true','yes') else (0 if asset_manager.get_comfyui_launch_spec() else 1))""", 0, True)
    If comfyCheck = 0 Then
        WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && " & pyCmd & " -c ""import asset_manager, subprocess; spec = asset_manager.get_comfyui_launch_spec(); subprocess.run(spec['cmd'], cwd=spec['cwd'])"" >> comfyui.log 2>&1", 0, False
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
WshShell.Run "cmd /c cd /d """ & ScriptDir & """ && """ & pyCmd & """ bot.py >> bot.log 2>&1", 0, False
