PythonScriptPath = "UCG_Creater.py"

Set objShell = CreateObject("WScript.Shell")

strCommand = "cmd /c python " & PythonScriptPath

objShell.Run strCommand, 0, False

Set objShell = Nothing