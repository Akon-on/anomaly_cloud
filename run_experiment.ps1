param(
    [string]$Scenario = "balanced",
    [int]$SeedOverride = -1,
    [ValidateSet("standard", "thesis")]
    [string]$DurationProfile = "standard",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Description,
        [scriptblock]$Command
    )

    Write-Host $Description
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Description"
    }
}

$scenarioVars = @{
    "balanced" = @{
        WARMUP_SECONDS = "20"
        ATTACK_DURATION = "45"
        COOLDOWN_SECONDS = "20"
        REQUESTS_PER_SECOND = "10"
        THREADS = "3"
        NORMAL_TRAFFIC_RATIO = "0.30"
        RANDOM_SEED = "42"
        ATTACK_STYLE = "brute_force"
        NORMAL_LOGIN_RATIO = "0.10"
        NORMAL_LOGIN_FAILURE_RATE = "0.05"
        NORMAL_IP_POOL = "15"
        ATTACK_IP_POOL = "10"
    }
    "aggressive" = @{
        WARMUP_SECONDS = "15"
        ATTACK_DURATION = "60"
        COOLDOWN_SECONDS = "15"
        REQUESTS_PER_SECOND = "20"
        THREADS = "5"
        NORMAL_TRAFFIC_RATIO = "0.10"
        RANDOM_SEED = "1337"
        ATTACK_STYLE = "brute_force"
        NORMAL_LOGIN_RATIO = "0.12"
        NORMAL_LOGIN_FAILURE_RATE = "0.06"
        NORMAL_IP_POOL = "20"
        ATTACK_IP_POOL = "30"
    }
    "mostly-normal" = @{
        WARMUP_SECONDS = "20"
        ATTACK_DURATION = "45"
        COOLDOWN_SECONDS = "20"
        REQUESTS_PER_SECOND = "8"
        THREADS = "2"
        NORMAL_TRAFFIC_RATIO = "0.70"
        RANDOM_SEED = "7"
        ATTACK_STYLE = "brute_force"
        NORMAL_LOGIN_RATIO = "0.08"
        NORMAL_LOGIN_FAILURE_RATE = "0.04"
        NORMAL_IP_POOL = "30"
        ATTACK_IP_POOL = "8"
    }
    "credential-stuffing" = @{
        WARMUP_SECONDS = "15"
        ATTACK_DURATION = "75"
        COOLDOWN_SECONDS = "15"
        REQUESTS_PER_SECOND = "22"
        THREADS = "6"
        NORMAL_TRAFFIC_RATIO = "0.05"
        RANDOM_SEED = "2026"
        ATTACK_STYLE = "credential_stuffing"
        NORMAL_LOGIN_RATIO = "0.12"
        NORMAL_LOGIN_FAILURE_RATE = "0.04"
        NORMAL_IP_POOL = "20"
        ATTACK_IP_POOL = "40"
    }
    "endpoint-scanning" = @{
        WARMUP_SECONDS = "20"
        ATTACK_DURATION = "60"
        COOLDOWN_SECONDS = "20"
        REQUESTS_PER_SECOND = "16"
        THREADS = "4"
        NORMAL_TRAFFIC_RATIO = "0.25"
        RANDOM_SEED = "3030"
        ATTACK_STYLE = "endpoint_scanning"
        NORMAL_LOGIN_RATIO = "0.08"
        NORMAL_LOGIN_FAILURE_RATE = "0.03"
        NORMAL_IP_POOL = "25"
        ATTACK_IP_POOL = "20"
    }
    "burst-traffic" = @{
        WARMUP_SECONDS = "20"
        ATTACK_DURATION = "50"
        COOLDOWN_SECONDS = "20"
        REQUESTS_PER_SECOND = "14"
        THREADS = "4"
        NORMAL_TRAFFIC_RATIO = "0.20"
        RANDOM_SEED = "4040"
        ATTACK_STYLE = "burst_traffic"
        NORMAL_LOGIN_RATIO = "0.06"
        NORMAL_LOGIN_FAILURE_RATE = "0.03"
        NORMAL_IP_POOL = "25"
        ATTACK_IP_POOL = "12"
    }
    "slow-brute-force" = @{
        WARMUP_SECONDS = "30"
        ATTACK_DURATION = "90"
        COOLDOWN_SECONDS = "30"
        REQUESTS_PER_SECOND = "8"
        THREADS = "3"
        NORMAL_TRAFFIC_RATIO = "0.45"
        RANDOM_SEED = "5050"
        ATTACK_STYLE = "slow_brute_force"
        NORMAL_LOGIN_RATIO = "0.10"
        NORMAL_LOGIN_FAILURE_RATE = "0.05"
        NORMAL_IP_POOL = "30"
        ATTACK_IP_POOL = "18"
    }
    "mixed-attacks" = @{
        WARMUP_SECONDS = "25"
        ATTACK_DURATION = "75"
        COOLDOWN_SECONDS = "25"
        REQUESTS_PER_SECOND = "15"
        THREADS = "4"
        NORMAL_TRAFFIC_RATIO = "0.30"
        RANDOM_SEED = "6060"
        ATTACK_STYLE = "mixed"
        NORMAL_LOGIN_RATIO = "0.10"
        NORMAL_LOGIN_FAILURE_RATE = "0.05"
        NORMAL_IP_POOL = "30"
        ATTACK_IP_POOL = "25"
    }
}

if (-not $scenarioVars.ContainsKey($Scenario)) {
    $validScenarios = ($scenarioVars.Keys | Sort-Object) -join ", "
    throw "Unknown scenario '$Scenario'. Valid values: $validScenarios"
}

if ($DurationProfile -eq "thesis") {
    foreach ($name in $scenarioVars.Keys) {
        $scenarioVars[$name].WARMUP_SECONDS = "60"
        $scenarioVars[$name].ATTACK_DURATION = "120"
        $scenarioVars[$name].COOLDOWN_SECONDS = "60"
    }
}

Invoke-Step "Resetting containers and volumes for a clean experiment run..." {
    docker compose down -v
}

if (-not $SkipBuild) {
    Invoke-Step "Building latest images for victim, ml, ml_eval, traffic, and visual..." {
        docker compose build victim ml ml_eval traffic visual
    }
}

Invoke-Step "Starting base services..." {
    docker compose up -d db victim ml
}

Write-Host "Running traffic scenario: $Scenario (duration_profile=$DurationProfile)"
$vars = $scenarioVars[$Scenario]

if ($SeedOverride -ge 0) {
    $vars.RANDOM_SEED = [string]$SeedOverride
}

Write-Host "Scenario parameters: warmup=$($vars.WARMUP_SECONDS), attack=$($vars.ATTACK_DURATION), cooldown=$($vars.COOLDOWN_SECONDS), rps=$($vars.REQUESTS_PER_SECOND), threads=$($vars.THREADS), normal_ratio=$($vars.NORMAL_TRAFFIC_RATIO), normal_login_ratio=$($vars.NORMAL_LOGIN_RATIO), normal_login_failure=$($vars.NORMAL_LOGIN_FAILURE_RATE), seed=$($vars.RANDOM_SEED), attack_style=$($vars.ATTACK_STYLE), normal_ips=$($vars.NORMAL_IP_POOL), attack_ips=$($vars.ATTACK_IP_POOL)"

Invoke-Step "Executing traffic generator..." {
    docker compose run --rm `
        -e WARMUP_SECONDS=$($vars.WARMUP_SECONDS) `
    -e ATTACK_DURATION=$($vars.ATTACK_DURATION) `
        -e COOLDOWN_SECONDS=$($vars.COOLDOWN_SECONDS) `
    -e REQUESTS_PER_SECOND=$($vars.REQUESTS_PER_SECOND) `
    -e THREADS=$($vars.THREADS) `
    -e NORMAL_TRAFFIC_RATIO=$($vars.NORMAL_TRAFFIC_RATIO) `
    -e NORMAL_LOGIN_RATIO=$($vars.NORMAL_LOGIN_RATIO) `
    -e NORMAL_LOGIN_FAILURE_RATE=$($vars.NORMAL_LOGIN_FAILURE_RATE) `
    -e RANDOM_SEED=$($vars.RANDOM_SEED) `
    -e NORMAL_IP_POOL=$($vars.NORMAL_IP_POOL) `
    -e ATTACK_IP_POOL=$($vars.ATTACK_IP_POOL) `
    -e ATTACK_STYLE=$($vars.ATTACK_STYLE) `
    -e SCENARIO_NAME=$Scenario `
        traffic
}

Invoke-Step "Running model comparison evaluation..." {
    docker compose --profile evaluation run --rm ml_eval
}

Write-Host "Done. Check outputs in ./output"
