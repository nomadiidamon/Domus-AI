param(
    [Parameter(Mandatory=$true)]
    [string]$Model
)


# ==============================
# Configuration
# ==============================

. "$PSScriptRoot\AI-Common.ps1"


Write-Host ""
Write-Host "================================="
Write-Host " Starting AI Environment"
Write-Host "================================="
Write-Host ""



# ==============================
# Validate Configuration Files
# ==============================

if (!(Test-Path $ModelsFile)) {

    Write-Error "Missing models.json: $ModelsFile"
    exit 1

}


if (!(Test-Path $EnvFile)) {

    Write-Error "Missing ollama.env: $EnvFile"
    exit 1

}



# ==============================
# Load Model Configuration
# ==============================

$Models =
Get-Content $ModelsFile |
ConvertFrom-Json



$AvailableModels =
$Models.PSObject.Properties.Name



if ($AvailableModels -notcontains $Model) {

    Write-Host ""
    Write-Host "Unknown model: $Model"
    Write-Host ""

    Write-Host "Available models:"
    
    foreach($m in $AvailableModels)
    {
        Write-Host " - $m"
    }

    exit 1

}



$ModelInfo =
$Models.$Model



Write-Host "Selected Model:"
Write-Host " $Model"

Write-Host ""

Write-Host "Description:"
Write-Host " $($ModelInfo.description)"

Write-Host ""



# ==============================
# Load Ollama Environment
# ==============================

Write-Host "Loading Ollama configuration..."



Get-Content $EnvFile | ForEach-Object {


    # Ignore comments

    if ($_ -match "^\s*#") {
        return
    }


    # Ignore blank lines

    if ($_ -match "^\s*$") {
        return
    }



    $KeyValue =
    $_ -split "=",2



    $Key =
    $KeyValue[0].Trim()



    $Value =
    $KeyValue[1].Trim()



    [Environment]::SetEnvironmentVariable(
        $Key,
        $Value,
        "Process"
    )


    Write-Host " Loaded: $Key"

}



Write-Host ""



# ==============================
# Check Ollama Server
# ==============================

Write-Host "Checking Ollama server..."



$OllamaRunning = $false



try {

    Invoke-RestMethod `
        http://localhost:11434/api/tags `
        -TimeoutSec 2 `
        | Out-Null


    $OllamaRunning = $true

}
catch {

    $OllamaRunning = $false

}



$StartedOllama = $false

$OllamaPID = $null



if (!$OllamaRunning) {


    Write-Host "Ollama server not detected."
    Write-Host "Starting Ollama..."



    $OllamaProcess =
    Start-Process `
        -FilePath "ollama" `
        -ArgumentList "serve" `
        -WindowStyle Hidden `
        -PassThru



    $OllamaPID =
    $OllamaProcess.Id



    $StartedOllama = $true



    $OllamaPID |
        Out-File $PIDFile



    Write-Host "Ollama PID: $OllamaPID"



    Write-Host "Waiting for Ollama startup..."



    $Attempts = 0


    while($Attempts -lt 10)
    {

        Start-Sleep -Seconds 1


        try {

            Invoke-RestMethod `
                http://localhost:11434/api/tags `
                -TimeoutSec 2 `
                | Out-Null


            break

        }
        catch {

            $Attempts++

        }

    }



}
else {

    Write-Host "Ollama already running."

}



Write-Host ""



# ==============================
# Save Session Information
# ==============================

$Session = @{
    
    Model = $Model

    StartedOllama = $StartedOllama

    OllamaPID = $OllamaPID

    Started = (Get-Date).ToString("o")

}



$Session |
ConvertTo-Json |
Out-File $SessionFile



# ==============================
# Launch Claude
# ==============================

Write-Host ""
Write-Host "Launching Claude with $Model..."
Write-Host ""



ollama launch claude --model $Model