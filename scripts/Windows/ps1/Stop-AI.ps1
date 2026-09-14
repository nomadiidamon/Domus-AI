# ==============================
# Configuration
# ==============================

. "$PSScriptRoot\AI-Common.ps1"



Write-Host ""
Write-Host "================================="
Write-Host " Stopping AI Environment"
Write-Host "================================="
Write-Host ""



# ==============================
# Load Session
# ==============================

$Session = $null


if(Test-Path $SessionFile)
{

    $Session =
    Get-Content $SessionFile |
    ConvertFrom-Json


    Write-Host "Active Session:"
    Write-Host " Model: $($Session.Model)"
    Write-Host ""

}



# ==============================
# Stop Ollama if owned by session
# ==============================


if(Test-Path $PIDFile)
{


    $OllamaPID =
    Get-Content $PIDFile



    $Process =
    Get-Process `
        -Id $OllamaPID `
        -ErrorAction SilentlyContinue



    if($Process)
    {


        if($Process.ProcessName -eq "ollama")
        {


            Write-Host "Stopping Ollama PID $OllamaPID..."



            Stop-Process `
                -Id $OllamaPID `
                -Force



            Write-Host "Ollama stopped."

        }
        else
        {

            Write-Host ""
            Write-Host "PID $OllamaPID is not Ollama."
            Write-Host "Not stopping process."

        }


    }
    else
    {

        Write-Host "Ollama process already stopped."

    }



    Remove-Item $PIDFile -Force


}
else
{

    Write-Host "No Ollama PID owned by AI session."

}



# ==============================
# Cleanup
# ==============================

if(Test-Path $SessionFile)
{

    Remove-Item $SessionFile -Force

}



Write-Host ""
Write-Host "AI environment stopped."
Write-Host ""