#requires -Version 5.1
<#
    Fluxckore - asistente de restauracion.

    Windows (Smart App Control o el antivirus) puede bloquear o eliminar
    Fluxckore.exe por no tener reputacion. La aplicacion no puede avisar de
    eso porque, cuando pasa, el .exe ya no se ejecuta: este asistente hace de
    puente y abre el Historial de proteccion de Windows, que es el unico sitio
    donde se puede pulsar "Restaurar".

    Nunca restaura nada por su cuenta ni toca la configuracion de seguridad:
    solo explica que ha pasado y lleva al usuario al sitio correcto.
#>
param(
    [ValidateSet("missing", "failed", "manual")]
    [string]$Reason = "manual",
    [string]$AppDir = "",
    [string]$LogPath = ""
)

$ErrorActionPreference = "SilentlyContinue"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

if (-not $AppDir) {
    $AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $LogPath) {
    $LogPath = Join-Path $AppDir "fluxckore-startup.log"
}
$exe = Join-Path $AppDir "Fluxckore.exe"

# ---------------------------------------------------------------------------
# Cuando lo llama el lanzador: solo avisar si el .exe no llego a ejecutarse.
# Si el proceso vive, o el registro de arranque crecio, la app si arranco.
# ---------------------------------------------------------------------------
if ($Reason -eq "failed") {
    $before = -1
    if (Test-Path -LiteralPath $LogPath) {
        $before = (Get-Item -LiteralPath $LogPath).Length
    }
    Start-Sleep -Seconds 25

    $running = @(Get-Process -Name "Fluxckore" -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) { exit 0 }

    $after = -1
    if (Test-Path -LiteralPath $LogPath) {
        $after = (Get-Item -LiteralPath $LogPath).Length
    }
    if ($after -ne $before) { exit 0 }

    $Reason = "missing"
}

# ---------------------------------------------------------------------------
# Estado de Smart App Control (solo lectura).
#   0 = desactivado, 1 = activado, 2 = en evaluacion
# ---------------------------------------------------------------------------
$sacState = -1
try {
    $policy = Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -Name "VerifiedAndReputablePolicyState"
    $sacState = [int]$policy.VerifiedAndReputablePolicyState
} catch { }

$sacText = switch ($sacState) {
    0 { "desactivado" }
    1 { "activado" }
    2 { "en evaluacion" }
    default { "no se pudo comprobar" }
}

# ---------------------------------------------------------------------------
# Texto segun el caso.
# ---------------------------------------------------------------------------
$title = "Fluxckore"
if ($Reason -eq "missing") {
    $title = "Fluxckore - Windows lo bloqueo"
    $body = @"
El archivo Fluxckore.exe ya no esta en esta carpeta.

Windows lo bloqueo o lo elimino por seguridad (Smart App Control o el
antivirus) porque la aplicacion todavia no tiene reputacion. No es un fallo
de Fluxckore y no hay ninguna licencia que restaurar: lo que Windows guarda
es el archivo bloqueado.

Para recuperarlo:

  1. Pulsa "Abrir Historial de proteccion".
  2. Busca la deteccion de Fluxckore y elige "Restaurar"
     (o "Permitir en el dispositivo").
  3. Vuelve a abrir Fluxckore.
"@
} else {
    $title = "Fluxckore - restaurar"
    $body = @"
Si Fluxckore no abre, o Windows dice que no puede ejecutarse, este asistente
te lleva al sitio donde se restaura.

  1. Pulsa "Abrir Historial de proteccion".
  2. Busca la deteccion de Fluxckore y elige "Restaurar"
     (o "Permitir en el dispositivo").
  3. Vuelve a abrir Fluxckore.
"@
}

$sacNote = "Smart App Control: $sacText."
if ($sacState -eq 1) {
    $sacNote += "`nCon Smart App Control activado, Windows puede volver a bloquear la aplicacion aunque la restaures. Se desactiva en Configuracion > Privacidad y seguridad > Seguridad de Windows > Control de aplicaciones y navegador (y no se puede volver a activar sin reinstalar Windows)."
}

# ---------------------------------------------------------------------------
# Ventana.
# ---------------------------------------------------------------------------
$form = New-Object System.Windows.Forms.Form
$form.Text = $title
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(12, 12, 16)
$form.ForeColor = [System.Drawing.Color]::FromArgb(236, 236, 244)
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)
$form.ClientSize = New-Object System.Drawing.Size(620, 400)

$iconPath = Join-Path $AppDir "Fluxckore.exe"
if (Test-Path -LiteralPath $iconPath) {
    try { $form.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($iconPath) } catch { }
}

$header = New-Object System.Windows.Forms.Label
$header.Text = $title
$header.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 13)
$header.ForeColor = [System.Drawing.Color]::FromArgb(120, 190, 255)
$header.AutoSize = $false
$header.SetBounds(24, 18, 570, 32)
$form.Controls.Add($header)

$text = New-Object System.Windows.Forms.Label
$text.Text = $body.Trim()
$text.AutoSize = $false
$text.SetBounds(24, 58, 570, 190)
$form.Controls.Add($text)

$note = New-Object System.Windows.Forms.Label
$note.Text = $sacNote
$note.AutoSize = $false
$note.ForeColor = [System.Drawing.Color]::FromArgb(160, 160, 176)
$note.SetBounds(24, 250, 570, 100)
$form.Controls.Add($note)

$buttonFont = New-Object System.Drawing.Font("Segoe UI Semibold", 9.5)

$restore = New-Object System.Windows.Forms.Button
$restore.Text = "Abrir Historial de proteccion"
$restore.Font = $buttonFont
$restore.SetBounds(24, 352, 214, 32)
$restore.Add_Click({
    try {
        Start-Process "windowsdefender://threat"
    } catch {
        Start-Process "windowsdefender://"
    }
})
$form.Controls.Add($restore)

$retry = New-Object System.Windows.Forms.Button
$retry.Text = "Volver a intentar"
$retry.SetBounds(248, 352, 130, 32)
$retry.Enabled = Test-Path -LiteralPath $exe
$retry.Add_Click({
    if (Test-Path -LiteralPath $exe) {
        Start-Process -FilePath $exe -WorkingDirectory $AppDir
        $form.Close()
    }
})
$form.Controls.Add($retry)

$openFolder = New-Object System.Windows.Forms.Button
$openFolder.Text = "Abrir carpeta"
$openFolder.SetBounds(388, 352, 110, 32)
$openFolder.Add_Click({ Start-Process -FilePath "explorer.exe" -ArgumentList "`"$AppDir`"" })
$form.Controls.Add($openFolder)

$close = New-Object System.Windows.Forms.Button
$close.Text = "Cerrar"
$close.SetBounds(508, 352, 88, 32)
$close.Add_Click({ $form.Close() })
$form.Controls.Add($close)

$form.AcceptButton = $restore
$form.CancelButton = $close

[void]$form.ShowDialog()
