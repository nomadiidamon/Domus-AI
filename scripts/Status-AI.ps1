Write-Host ""
Write-Host "====== AI STATUS ======"
Write-Host ""


# Ollama server

$server =
Get-Process ollama -ErrorAction SilentlyContinue


if($server){

Write-Host "Ollama Server: RUNNING"

}
else{

Write-Host "Ollama Server: STOPPED"

}



Write-Host ""

Write-Host "Loaded Models:"
ollama ps


Write-Host ""

Write-Host "CPU Usage:"

Get-Counter `
'\Processor(_Total)\% Processor Time' |
Select -ExpandProperty CounterSamples |
Select CookedValue



Write-Host ""

Write-Host "GPU Usage:"

Get-Counter `
'\GPU Engine(*)\Utilization Percentage' |
Select -ExpandProperty CounterSamples |
Measure CookedValue -Average



Write-Host ""

Write-Host "Memory:"

Get-Counter `
'\Memory\Available MBytes'