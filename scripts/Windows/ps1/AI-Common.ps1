# ==============================
# Locate AI Root
# ==============================


function Find-AIRoot {

    param(
        [string]$StartPath
    )


    $Current =
    Get-Item $StartPath



    while($Current.Parent)
    {


        $Config =
        Join-Path $Current.FullName "config"


        $Models =
        Join-Path $Config "models.json"



        if(
            (Test-Path $Config) -and
            (Test-Path $Models)
        )
        {

            return $Current.FullName

        }



        $Current =
        $Current.Parent

    }


    throw "Unable to locate Local-AI-Runtime root."

}



$AIRoot =
Find-AIRoot $PSScriptRoot



# ==============================
# Runtime Paths
# ==============================


$ConfigPath =
Join-Path $AIRoot "config"


$ModelsFile =
Join-Path $ConfigPath "models.json"


$EnvFile =
Join-Path $ConfigPath "ollama.env"


$SessionFile =
Join-Path $ConfigPath "session.json"


$PIDFile =
Join-Path $ConfigPath "ollama.pid"



function Write-StatusLine($Name, $Value)
{

    Write-Host "${Name}:"
    Write-Host "  $Value"
    Write-Host ""

}