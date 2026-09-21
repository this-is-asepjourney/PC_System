[Windows.Devices.Enumeration.DeviceInformation, Windows.Devices.Enumeration, ContentType = WindowsRuntime] | Out-Null
$reqProps = New-Object System.Collections.Generic.List[string]
$reqProps.Add("System.Devices.Aep.Bluetooth.Le.BatteryLevel")
$reqProps.Add("System.Devices.Aep.DeviceAddress")
$devices = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync("System.Devices.Aep.ProtocolId:=`"{e0cbf06c-cd8b-4647-bb8a-263b43f0f974}`"", $reqProps).GetResults()
$results = @()
foreach ($d in $devices) {
    if ($d.Properties.ContainsKey("System.Devices.Aep.Bluetooth.Le.BatteryLevel")) {
        $battery = $d.Properties["System.Devices.Aep.Bluetooth.Le.BatteryLevel"]
        if ($null -ne $battery) {
            $results += [PSCustomObject]@{Name=$d.Name; Battery=$battery}
        }
    }
}
$results | ConvertTo-Json
