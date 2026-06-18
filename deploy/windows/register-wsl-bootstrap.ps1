param(
    [string]$TaskName = "WTTJ WSL Bootstrap",
    [string]$Distro = "",
    [string]$User = "seb"
)

$wslArgs = if ($Distro) {
    "-d `"$Distro`" --user `"$User`" --exec true"
} else {
    "--user `"$User`" --exec true"
}

$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument $wslArgs
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Starts WSL after Windows login so the WTTJ systemd user timer can catch up." `
    -Force
