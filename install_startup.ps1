# Creates a shortcut in the Startup folder so Jully opens with Windows (with the Jully icon).
$root = $PSScriptRoot
$exe = Join-Path $root "Jully.exe"
$shortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "Jully.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
if (Test-Path $exe) {
    $s.TargetPath = $exe
    $s.Arguments = "--hidden"
} else {
    $pythonw = if (Test-Path "$root\.venv\Scripts\pythonw.exe") { "$root\.venv\Scripts\pythonw.exe" } else { (Get-Command pythonw).Source }
    $s.TargetPath = $pythonw
    $s.Arguments = "`"$root\main.py`" --hidden"
}
$s.WorkingDirectory = $root
$s.IconLocation = "$root\assets\icon.ico"
$s.Save()
Write-Host "Shortcut created at $shortcut"
