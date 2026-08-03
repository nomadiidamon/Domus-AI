param(
    [Parameter(Mandatory=$true)]
    [string]$Model,

    [switch]$Overwrite
)



. "$PSScriptRoot\AI-Common.ps1"


$Models =
Get-Content "$AIRoot\config\models.json" |
ConvertFrom-Json



if (-not $Models.$Model) {

    Write-Error "Unknown model"
    exit

}



$Info =
$Models.$Model



# ==========================
# Determine Output Model Name
# ==========================

if ($Overwrite) {

    $BuildName = $Model

}
else {

    $BuildName = $Model

    $ExistingModels = ollama list |
        Select-String $Model


    if ($ExistingModels) {

        $Counter = 2

        while ($true) {

            $Candidate = "$Model$Counter"

            $Exists =
            ollama list |
            Select-String "^$Candidate\s"


            if (!$Exists) {

                $BuildName = $Candidate
                break

            }

            $Counter++

        }

    }

}


Write-Host ""
Write-Host "Building model:"
Write-Host $BuildName
Write-Host ""



ollama create `
$BuildName `
-f $Info.modelfile



Write-Host ""
Write-Host "Completed."