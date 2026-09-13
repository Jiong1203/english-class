<#
    auto_push.ps1

    Scheduled auto-commit & push for the English Corner archive.

    Behaviour:
      1. Commit the working tree if it is dirty (skipped when already clean).
      2. Then ALWAYS reconcile with origin and push if the branch is ahead --
         a previous run may have committed successfully but failed to push
         (e.g. the network was down), and that commit must not be stranded.
      3. Every run appends to .claude/auto_push.log. Nothing is interactive:
         a credential prompt would hang the scheduled task, so terminal
         prompting is disabled and a failure is logged instead.

    Registered as the Windows scheduled task "EnglishClass-AutoPush".
#>

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogFile  = Join-Path $PSScriptRoot 'auto_push.log'

# Never block on a credential prompt inside a non-interactive scheduled task.
$env:GIT_TERMINAL_PROMPT = '0'
# Keep git's output readable in the log regardless of the console code page.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = '{0}  [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    # PowerShell 5.1's -Encoding utf8 emits a BOM; write it ourselves without one.
    [System.IO.File]::AppendAllText($LogFile, $line + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding $false))
}

function Invoke-Git {
    param([string[]]$GitArgs, [switch]$AllowFailure)
    # PowerShell 5.1 wraps each native stderr line in an ErrorRecord, which would
    # dump a multi-line NativeCommandError blob into the log. Unwrap to plain text.
    $lines = & git @GitArgs 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { $_ }
    }
    $output = ($lines -join "`n").Trim()
    if ($LASTEXITCODE -ne 0 -and -not $AllowFailure) {
        $first = ($output -split "`n" | Where-Object { $_.Trim() } | Select-Object -First 1)
        throw ('git {0} failed (exit {1}): {2}' -f ($GitArgs -join ' '), $LASTEXITCODE, $first)
    }
    return $output
}

try {
    Set-Location -Path $RepoRoot
    $branch = Invoke-Git @('rev-parse', '--abbrev-ref', 'HEAD')

    # --- Stage 1: commit the working tree, if there is anything in it ---------
    $changes = Invoke-Git @('status', '--porcelain')
    if ([string]::IsNullOrWhiteSpace($changes)) {
        Write-Log "Working tree clean on '$branch'."
    }
    else {
        $changeCount = ($changes -split "`n").Count
        Write-Log ("Detected {0} changed path(s) on branch '{1}'." -f $changeCount, $branch)

        Invoke-Git @('add', '-A') | Out-Null
        $staged = Invoke-Git @('diff', '--cached', '--name-only')

        if ([string]::IsNullOrWhiteSpace($staged)) {
            Write-Log 'All changes are ignored by .gitignore - nothing staged.' 'WARN'
        }
        else {
            $today    = Get-Date -Format 'yyyy-MM-dd'
            $fileList = ($staged -split "`n" | ForEach-Object { $_.Trim() }) -join ', '
            $subject  = "docs: update English Corner entries for $today"
            $body     = "Auto-committed by the scheduled task EnglishClass-AutoPush. Changed files: $fileList"

            # git commit -F <file> avoids any quoting/here-string pitfalls with multi-line
            # messages. Set-Content -Encoding utf8 would prepend a BOM on PowerShell 5.1 and
            # git would treat those bytes as the start of the subject, so write it raw.
            $msgFile = Join-Path $env:TEMP ('ec_commit_{0}.txt' -f (Get-Date -Format 'yyyyMMddHHmmss'))
            [System.IO.File]::WriteAllText($msgFile, ($subject + "`r`n`r`n" + $body), (New-Object System.Text.UTF8Encoding $false))

            try {
                Invoke-Git @('commit', '-F', $msgFile) | Out-Null
                $actual = Invoke-Git @('log', '-1', '--format=%s')
                if ($actual -ne $subject) {
                    Write-Log ("Commit subject was mangled (expected '{0}', got '{1}') - amending." -f $subject, $actual) 'WARN'
                    Invoke-Git @('commit', '--amend', '-F', $msgFile) | Out-Null
                }
                Write-Log "Committed: $subject"
            }
            finally {
                Remove-Item -Path $msgFile -Force -ErrorAction SilentlyContinue
            }
        }
    }

    # --- Stage 2: reconcile with origin, ALWAYS ------------------------------
    # This runs even when stage 1 committed nothing. A clean working tree does NOT
    # mean there is nothing to push: an earlier run may have committed and then
    # failed to push, leaving the commit stranded on this machine forever.
    Invoke-Git @('fetch', 'origin', $branch) | Out-Null

    $ahead  = [int](Invoke-Git @('rev-list', '--count', "origin/$branch..$branch"))
    $behind = [int](Invoke-Git @('rev-list', '--count', "$branch..origin/$branch"))

    if ($ahead -eq 0) {
        if ($behind -gt 0) {
            Write-Log "Nothing to push; local is behind origin/$branch by $behind commit(s)."
        } else {
            Write-Log "In sync with origin/$branch - nothing to do."
        }
        exit 0
    }

    Write-Log "Local is ahead of origin/$branch by $ahead commit(s), behind by $behind."

    if ($behind -gt 0) {
        $rebase = & git rebase ('origin/' + $branch) 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { $_ }
        }
        if ($LASTEXITCODE -ne 0) {
            & git rebase --abort 2>&1 | Out-Null
            $first = (($rebase -join "`n") -split "`n" | Where-Object { $_.Trim() } | Select-Object -First 1)
            Write-Log ("Rebase onto origin/{0} failed and was aborted; commits kept locally. {1}" -f $branch, $first) 'ERROR'
            exit 1
        }
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
