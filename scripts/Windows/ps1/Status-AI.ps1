. "$PSScriptRoot\AI-Common.ps1"

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

if($server){
    ollama ps
}
else{
    Write-Host "Ollama is stopped. No models loaded."
}


Write-Host ""
Write-Host "CPU Usage:"

$cpu = Get-Counter '\Processor(_Total)\% Processor Time'
"{0:N1}%" -f $cpu.CounterSamples.CookedValue



Write-Host ""
Write-Host "Memory Usage:"

$memory = Get-CimInstance Win32_OperatingSystem

$totalGB = [math]::Round($memory.TotalVisibleMemorySize / 1MB, 2)
$freeGB = [math]::Round($memory.FreePhysicalMemory / 1MB, 2)
$usedGB = [math]::Round($totalGB - $freeGB, 2)

Write-Host "Used: $usedGB GB / $totalGB GB"


Write-Host ""

# =========================
# GPU STATUS
# =========================

$GPUName = "Unknown"
$VRAMUsed = "Unknown"
$VRAMTotal = "Unknown"
$GPULoad = "Unknown"


# =========================
# NVIDIA
# =========================

if(Get-Command nvidia-smi -ErrorAction SilentlyContinue){

    $gpu = nvidia-smi `
        --query-gpu=name,memory.used,memory.total,utilization.gpu `
        --format=csv,noheader

    $data = $gpu -split ","

    $GPUName = $data[0].Trim()
    $VRAMUsed = $data[1].Trim()
    $VRAMTotal = $data[2].Trim()
    $GPULoad = $data[3].Trim()

}


# =========================
# AMD ROCm
# =========================

elseif(Get-Command rocm-smi -ErrorAction SilentlyContinue){

    $GPUName = "AMD ROCm GPU"

    $VRAM = rocm-smi --showmeminfo vram

    # Parsing depends on ROCm version
    $VRAMUsed = "Available from rocm-smi"
    $VRAMTotal = "Available from rocm-smi"

    $GPULoad = "Available from rocm-smi"

}


# =========================
# AMD AMDSMI
# =========================

elseif(Get-Command amd-smi -ErrorAction SilentlyContinue){

    $GPUName = "AMD GPU"

    $stats = amd-smi metric --gpu use,memory

    $VRAMUsed = "See amd-smi"
    $VRAMTotal = "See amd-smi"
    $GPULoad = "See amd-smi"

}


# =========================
# Intel
# =========================

elseif(Get-Command intel_gpu_top -ErrorAction SilentlyContinue){

    $GPUName = "Intel GPU"

    $VRAMUsed = "See intel_gpu_top"
    $VRAMTotal = "Unknown"
    $GPULoad = "See intel_gpu_top"

}


# =========================
# Windows fallback
# =========================

else{

    $gpu = Get-CimInstance Win32_VideoController |
        Select-Object -First 1

    $GPUName = $gpu.Name

    $VRAMTotal = "{0:N2} GB" -f ($gpu.AdapterRAM / 1GB)

    $VRAMUsed = "Unavailable"
    $GPULoad = "Unavailable"

}


# =========================
# Display
# =========================

Write-Host ""
Write-Host "====== GPU STATUS ======"
Write-Host ""

Write-StatusLine "GPU" $GPUName
Write-StatusLine "VRAM Used" $VRAMUsed
Write-StatusLine "VRAM Total" $VRAMTotal
Write-StatusLine "GPU Load" $GPULoad