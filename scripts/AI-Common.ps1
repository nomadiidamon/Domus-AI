# ==============================
# Locate AI Root
# ==============================


$ScriptDirectory =
Split-Path -Parent $MyInvocation.MyCommand.Path


$AIRoot =
Split-Path $ScriptDirectory -Parent



if (!(Test-Path "$AIRoot\config")) {

    throw "AI root not found."

}



$ConfigPath =
"$AIRoot\config"



$ModelsFile =
"$ConfigPath\models.json"



$EnvFile =
"$ConfigPath\ollama.env"



$SessionFile =
"$ConfigPath\session.json"



$PIDFile =
"$ConfigPath\ollama.pid"