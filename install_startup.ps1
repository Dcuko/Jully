# Creates a shortcut in the Startup folder so Jully opens with Windows.
$root = $PSScriptRoot
$pythonw = if (Test-Path "$root\.venv\Scripts\pythonw.exe") { "$root\.venv\Scripts\pythonw.exe" } else { (Get-Command pythonw).Source }
$shortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "Jully.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
$s.TargetPath = $pythonw
$s.Arguments = "`"$root\main.py`" --hidden"
$s.WorkingDirectory = $root
$s.Save()
Write-Host "Shortcut created at $shortcut"
