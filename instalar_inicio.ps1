# Cria um atalho na pasta Inicializar para a Jully abrir junto com o Windows.
$raiz = $PSScriptRoot
$pythonw = if (Test-Path "$raiz\.venv\Scripts\pythonw.exe") { "$raiz\.venv\Scripts\pythonw.exe" } else { (Get-Command pythonw).Source }
$atalho = Join-Path ([Environment]::GetFolderPath("Startup")) "Jully.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($atalho)
$s.TargetPath = $pythonw
$s.Arguments = "`"$raiz\main.py`" --oculto"
$s.WorkingDirectory = $raiz
$s.Save()
Write-Host "Atalho criado em $atalho"
