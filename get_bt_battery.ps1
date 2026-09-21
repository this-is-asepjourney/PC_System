$devices = Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'}
$results = @()
foreach ($dev in $devices) {
    $batteryProp = Get-PnpDeviceProperty -InstanceId $dev.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' -ErrorAction SilentlyContinue
    if ($null -ne $batteryProp -and $null -ne $batteryProp.Data) {
        $results += [PSCustomObject]@{
            Name = $dev.FriendlyName
            Battery = $batteryProp.Data
        }
    }
}
$results | ConvertTo-Json
