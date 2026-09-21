$d = Get-PnpDevice -FriendlyName 'BT5.4 Mouse' | Select-Object -First 1
Get-PnpDeviceProperty -InstanceId $d.InstanceId | Where-Object {$_.Data -ne $null} | Select-Object KeyName, Data | ConvertTo-Json
