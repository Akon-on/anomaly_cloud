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
        NORMAL_IP_POOL = "20"
        ATTACK_IP_POOL = "40"
    }
}

if (-not $scenarioVars.ContainsKey($Scenario)) {
    throw "Unknown scenario '$Scenario'. Valid values: balanced, aggressive, mostly-normal, credential-stuffing"
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

Write-Host "Scenario parameters: warmup=$($vars.WARMUP_SECONDS), attack=$($vars.ATTACK_DURATION), cooldown=$($vars.COOLDOWN_SECONDS), rps=$($vars.REQUESTS_PER_SECOND), threads=$($vars.THREADS), normal_ratio=$($vars.NORMAL_TRAFFIC_RATIO), seed=$($vars.RANDOM_SEED), normal_ips=$($vars.NORMAL_IP_POOL), attack_ips=$($vars.ATTACK_IP_POOL)"

Invoke-Step "Executing traffic generator..." {
    docker compose run --rm `
        -e WARMUP_SECONDS=$($vars.WARMUP_SECONDS) `
    -e ATTACK_DURATION=$($vars.ATTACK_DURATION) `
        -e COOLDOWN_SECONDS=$($vars.COOLDOWN_SECONDS) `
    -e REQUESTS_PER_SECOND=$($vars.REQUESTS_PER_SECOND) `
    -e THREADS=$($vars.THREADS) `
    -e NORMAL_TRAFFIC_RATIO=$($vars.NORMAL_TRAFFIC_RATIO) `
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
