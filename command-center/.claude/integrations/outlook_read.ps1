# outlook_read.ps1 — FIXED, READ-ONLY Outlook MAPI reader for Deputy's integration layer (INT-OL-CAL / INT-OL-MAIL).
# Structural read-only boundary: this file contains no Send/Save/Move/Delete/Create call; the Python adapter pins its sha256
# and refuses to run a modified reader. Operations: probe · calendar · mail. Output: one JSON document on stdout.
# Data minimization: bodies are returned only as a short whitespace-collapsed preview (PreviewChars), never attachments.
param(
  [Parameter(Mandatory = $true)][ValidateSet("probe", "calendar", "mail", "get")][string]$Op,
  [string]$From = "", [string]$To = "", [int]$Limit = 50, [ValidateSet("Inbox", "Sent")][string]$Folder = "Inbox",
  [switch]$UnreadOnly, [string]$Search = "", [int]$PreviewChars = 600, [int]$Scan = 400, [string]$EntryId = ""
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function Emit($obj) { $obj | ConvertTo-Json -Depth 8 -Compress }
function Iso($d) { if ($null -eq $d) { return $null }; try { return ([datetime]$d).ToString("yyyy-MM-ddTHH:mm:ss") } catch { return $null } }
function Preview($text, $n) { if ($null -eq $text) { return "" }; $t = ([string]$text) -replace "\s+", " "; if ($t.Length -gt $n) { return $t.Substring(0, $n) + "…" } else { return $t } }
function Smtp($x) {
  try {
    if ($x.SenderEmailType -eq "EX") { $u = $x.Sender.GetExchangeUser(); if ($u) { return $u.PrimarySmtpAddress } }
    return [string]$x.SenderEmailAddress
  } catch { return [string]$x.SenderEmailAddress }
}
function Recipients($item) {
  $out = @()
  try { foreach ($r in $item.Recipients) { $addr = $null; try { $ex = $r.AddressEntry.GetExchangeUser(); if ($ex) { $addr = $ex.PrimarySmtpAddress } } catch {}; if (-not $addr) { $addr = [string]$r.Address }; $out += @{ name = [string]$r.Name; address = $addr; type = [int]$r.Type } } } catch {}
  return $out
}
$started = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
try {
  $ol = New-Object -ComObject Outlook.Application
  $ns = $ol.GetNamespace("MAPI")
  $accounts = @(); foreach ($a in $ns.Accounts) { $addr = [string]$a.SmtpAddress; if (-not $addr) { $addr = [string]$a.SmartAddress }; $accounts += @{ address = $addr; display = [string]$a.DisplayName; type = [int]$a.AccountType } }
  $me = $null; try { $me = @{ name = [string]$ns.CurrentUser.Name; address = [string]$ns.CurrentUser.Address; type = [string]$ns.CurrentUser.Type } } catch {}
  if ($Op -eq "get") {
    if (-not $EntryId) { Emit @{ ok = $false; error = "get requires -EntryId"; code = "BAD_PARAMS" }; exit 3 }
    $x = $null; try { $x = $ns.GetItemFromID($EntryId) } catch { $x = $null }
    if ($null -eq $x) { Emit @{ ok = $true; op = "get"; retrieved_at = $started; item = $null }; exit 0 }
    $item = @{ entry_id = [string]$x.EntryID; subject = [string]$x.Subject; class = [int]$x.Class; last_modified = Iso $x.LastModificationTime }
    if ($x.Class -eq 26) { $item = @{ entry_id = [string]$x.EntryID; subject = [string]$x.Subject; class = 26; last_modified = Iso $x.LastModificationTime; start = Iso $x.Start; end = Iso $x.End; location = [string]$x.Location; required = [string]$x.RequiredAttendees; cancelled = ($x.MeetingStatus -eq 5 -or $x.MeetingStatus -eq 7); recipients = @(Recipients $x) } }
    if ($x.Class -eq 43) { $item = @{ entry_id = [string]$x.EntryID; subject = [string]$x.Subject; class = 43; last_modified = Iso $x.LastModificationTime; to = [string]$x.To; cc = [string]$x.CC; sent = Iso $x.SentOn; unread = [bool]$x.UnRead; folder = [string]$x.Parent.Name; submitted = [bool]$x.Submitted } }
    Emit @{ ok = $true; op = "get"; retrieved_at = $started; accounts = $accounts; current_user = $me; item = $item }; exit 0
  }
  if ($Op -eq "probe") {
    $cals = @()
    try { foreach ($st in $ns.Stores) { try { $cf = $st.GetDefaultFolder(9); $cals += @{ store = [string]$st.DisplayName; folder = [string]$cf.FolderPath; count = [int]$cf.Items.Count } } catch {} } } catch {}
    Emit @{ ok = $true; op = "probe"; retrieved_at = $started; version = [string]$ol.Version; accounts = $accounts; current_user = $me; inbox_count = $ns.GetDefaultFolder(6).Items.Count; calendar_count = $ns.GetDefaultFolder(9).Items.Count; calendars = $cals }
    exit 0
  }
  if ($Op -eq "calendar") {
    if (-not $From -or -not $To) { Emit @{ ok = $false; error = "calendar requires -From and -To (ISO date/time)"; code = "BAD_PARAMS" }; exit 3 }
    $f = [datetime]::Parse($From, [Globalization.CultureInfo]::InvariantCulture); $t = [datetime]::Parse($To, [Globalization.CultureInfo]::InvariantCulture)
    $cal = $ns.GetDefaultFolder(9); $items = $cal.Items; $items.Sort("[Start]"); $items.IncludeRecurrences = $true
    $filter = "[Start] >= '" + $f.ToString("g") + "' AND [Start] <= '" + $t.ToString("g") + "'"
    $r = $items.Restrict($filter)
    $records = @(); $n = 0; $truncated = $false
    foreach ($x in $r) {
      $n++
      if ($n -gt $Limit) { $truncated = $true; break }
      $link = $null; try { $m = [regex]::Match([string]$x.Body, "https?://[^\s<>""']*(teams\.microsoft\.com|zoom\.us|meet\.google\.com)[^\s<>""']*"); if ($m.Success) { $link = $m.Value } } catch {}
      $records += @{
        entry_id = [string]$x.EntryID; subject = [string]$x.Subject; start = Iso $x.Start; end = Iso $x.End; all_day = [bool]$x.AllDayEvent
        location = [string]$x.Location; organizer = [string]$x.Organizer; required = [string]$x.RequiredAttendees; optional = [string]$x.OptionalAttendees
        recipients = @(Recipients $x); is_recurring = [bool]$x.IsRecurring; meeting_status = [int]$x.MeetingStatus; response_status = [int]$x.ResponseStatus
        busy_status = [int]$x.BusyStatus; sensitivity = [int]$x.Sensitivity; last_modified = Iso $x.LastModificationTime; preview = (Preview $x.Body $PreviewChars); online_link = $link
      }
    }
    Emit @{ ok = $true; op = "calendar"; retrieved_at = $started; accounts = $accounts; current_user = $me; from = (Iso $f); to = (Iso $t); filter = $filter; count = $records.Count; truncated = $truncated; records = $records }
    exit 0
  }
  if ($Op -eq "mail") {
    $fid = 6; if ($Folder -eq "Sent") { $fid = 5 }
    $fold = $ns.GetDefaultFolder($fid); $items = $fold.Items; $items.Sort("[ReceivedTime]", $true)
    $since = $null; if ($From) { $since = [datetime]::Parse($From, [Globalization.CultureInfo]::InvariantCulture) }
    $q = $Search.ToLowerInvariant()
    $records = @(); $seen = 0; $truncated = $false
    foreach ($x in $items) {
      $seen++
      if ($seen -gt $Scan) { $truncated = $true; break }
      if ($x.Class -ne 43) { continue }
      $rt = $null; try { $rt = [datetime]$x.ReceivedTime } catch {}
      if ($since -and $rt -and $rt -lt $since) { break }
      if ($UnreadOnly -and -not $x.UnRead) { continue }
      if ($q -and -not (([string]$x.Subject).ToLowerInvariant().Contains($q) -or ([string]$x.SenderName).ToLowerInvariant().Contains($q) -or ([string]$x.ConversationTopic).ToLowerInvariant().Contains($q))) { continue }
      $records += @{
        entry_id = [string]$x.EntryID; conversation_id = [string]$x.ConversationID; conversation_topic = [string]$x.ConversationTopic; subject = [string]$x.Subject
        sender_name = [string]$x.SenderName; sender = (Smtp $x); to = [string]$x.To; cc = [string]$x.CC; received = (Iso $rt); sent = (Iso $x.SentOn)
        unread = [bool]$x.UnRead; importance = [int]$x.Importance; flag_status = [int]$x.FlagStatus; flag_request = [string]$x.FlagRequest
        attachments = [int]$x.Attachments.Count; categories = [string]$x.Categories; last_modified = Iso $x.LastModificationTime; preview = (Preview $x.Body $PreviewChars); folder = $Folder
      }
      if ($records.Count -ge $Limit) { break }
    }
    Emit @{ ok = $true; op = "mail"; retrieved_at = $started; accounts = $accounts; current_user = $me; folder = $Folder; since = (Iso $since); count = $records.Count; scanned = $seen; truncated = $truncated; records = $records }
    exit 0
  }
} catch {
  $hr = $null; try { $hr = ("0x{0:X8}" -f $_.Exception.HResult) } catch {}
  Emit @{ ok = $false; op = $Op; error = [string]$_.Exception.Message; hresult = $hr; code = "COM_ERROR" }
  exit 2
}
