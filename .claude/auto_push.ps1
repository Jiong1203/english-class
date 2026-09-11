<#
    auto_push.ps1

    Scheduled auto-commit & push for the English Corner archive.

    Behaviour:
      1. If the working tree is clean, log one line and exit 0.
      2. Otherwise stage everything, commit with a fixed-template message,
         rebase onto origin and push.
      3. Every run appends to .claude/auto_push.log. Nothing is interactive:
         a credential prompt would hang the scheduled task, so terminal
         prompting is disabled and a failure is logged instead.

    Registered as the Windows scheduled task "EnglishClass-AutoPush".
#>

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogFile  = Join-Path $PSScriptRoot 'auto_push.log'

# Never block on a credential prompt inside a non-interactive scheduled task.
$env:GIT_TERMINAL_PROMPT = '0'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = '{0}  [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Add-Content -Path $LogFile -Value $line -Encoding utf8
}

function Invoke-Git {
    param([string[]]$GitArgs, [switch]$AllowFailure)
    $output = & git @GitArgs 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0 -and -not $AllowFailure) {
        throw ('git {0} failed (exit {1}): {2}' -f ($GitArgs -join ' '), $LASTEXITCODE, $output.Trim())
    }
    return $output.Trim()
}

try {
    Set-Location -Path $RepoRoot

    $changes = Invoke-Git @('status', '--porcelain')
    if ([string]::IsNullOrWhiteSpace($changes)) {
        Write-Log 'Working tree clean - nothing to push.'
        exit 0
    }

    $changeCount = ($changes -split "`n").Count
    $branch = Invoke-Git @('rev-parse', '--abbrev-ref', 'HEAD')
    Write-Log ("Detected {0} changed path(s) on branch '{1}'." -f $changeCount, $branch)

    Invoke-Git @('add', '-A') | Out-Null

    $staged = Invoke-Git @('diff', '--cached', '--name-only')
    if ([string]::IsNullOrWhiteSpace($staged)) {
        Write-Log 'All changes are ignored by .gitignore - nothing staged.' 'WARN'
        exit 0
    }

    $today    = Get-Date -Format 'yyyy-MM-dd'
    $fileList = ($staged -split "`n" | ForEach-Object { $_.Trim() }) -join ', '
    $subject  = "docs: update English Corner entries for $today"
    $body     = "Auto-committed by the scheduled task EnglishClass-AutoPush. Changed files: $fileList"

    # git commit -F <file> avoids any quoting/here-string pitfalls with multi-line messages.
    $msgFile = Join-Path $env:TEMP ('ec_commit_{0}.txt' -f (Get-Date -Format 'yyyyMMddHHmmss'))
    Set-Content -Path $msgFile -Value ($subject + "`r`n`r`n" + $body) -Encoding utf8

    try {
        Invoke-Git @('commit', '-F', $msgFile) | Out-Null
        Write-Log "Committed: $subject"
    } finally {
        Remove-Item -Path $msgFile -Force -ErrorAction SilentlyContinue
    }

    Invoke-Git @('fetch', 'origin', $branch) | Out-Null

    $rebase = & git rebase ('origin/' + $branch) 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        & git rebase --abort 2>&1 | Out-Null
        Write-Log ('Rebase onto origin/{0} failed, aborted. Commit is kept locally - resolve by hand. {1}' -f $branch, $rebase.Trim()) 'ERROR'
        exit 1
    }

    Invoke-Git @('push', 'origin', $branch) | Out-Null
    $head = Invoke-Git @('log', '-1', '--format=%h %s')
    Write-Log "Pushed to origin/$branch -> $head"
    exit 0
}
catch {
    Write-Log $_.Exception.Message 'ERROR'
    exit 1
}
