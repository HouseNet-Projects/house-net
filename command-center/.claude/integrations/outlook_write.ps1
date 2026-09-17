# outlook_write.ps1 — FIXED Outlook MAPI WRITE operations for Deputy's Action Runtime (INT-OL-CAL / INT-OL-MAIL).
# Reached ONLY by adapter_outlook_write.py after a Gev-approved action (actions.execute). Integrity-pinned (sha256 in capabilities/adapter).
# Operations: calendar.create · calendar.update · calendar.cancel · mail.draft · mail.send. One JSON document on stdout.
# Every operation returns the EntryID of the touched item so the read-only reader (outlook_read.ps1 -Op get) can verify independently.
param(
  [Parameter(Mandatory = $true)][ValidateSet("calendar.create", "calendar.update", "calendar.cancel", "mail.draft", "mail.send")][string]$Op,
  [string]$Subject = "", [string]$Start = "", [string]$End = "", [string]$Location = "", [string]$Body = "", [string]$Participants = "", [string]$EntryId = "",
  [string]$To = "", [string]$Cc = "", [string]$ReplyToEntryId = ""
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function Emit($obj) { $obj | ConvertTo-Json -Depth 6 -Compress }
function Iso($d) { if ($null -eq $d) { return $null }; try { return ([datetime]$d).ToString("yyyy-MM-ddTHH:mm:ss") } catch { return $null } }
$started = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
try {
  $ol = New-Object -ComObject Outlook.Application
  $ns = $ol.GetNamespace("MAPI")
  if ($Op -like "calendar.*") {
    if ($Op -eq "calendar.create") {
      if (-not $Subject -or -not $Start -or -not $End) { Emit @{ ok = $false; code = "BAD_PARAMS"; error = "calendar.create needs Subject, Start, End" }; exit 3 }
      $it = $ol.CreateItem(1)   # olAppointmentItem
      $it.Subject = $Subject; $it.Start = [datetime]::Parse($Start, [Globalization.CultureInfo]::InvariantCulture); $it.End = [datetime]::Parse($End, [Globalization.CultureInfo]::InvariantCulture)
      if ($Location) { $it.Location = $Location }; if ($Body) { $it.Body = $Body }
      if ($Participants) { $it.MeetingStatus = 1; foreach ($p in $Participants.Split(";")) { if ($p.Trim()) { $r = $it.Recipients.Add($p.Trim()); $r.Type = 1 } }; $null = $it.Recipients.ResolveAll(); $it.Send() } else { $it.Save() }
      Emit @{ ok = $true; op = $Op; retrieved_at = $started; entry_id = [string]$it.EntryID; subject = [string]$it.Subject; start = (Iso $it.Start); end = (Iso $it.End) }; exit 0
    }
    if (-not $EntryId) { Emit @{ ok = $false; code = "BAD_PARAMS"; error = "EntryId required" }; exit 3 }
    $it = $ns.GetItemFromID($EntryId)
    if ($Op -eq "calendar.update") {
      if ($Subject) { $it.Subject = $Subject }; if ($Start) { $it.Start = [datetime]::Parse($Start, [Globalization.CultureInfo]::InvariantCulture) }; if ($End) { $it.End = [datetime]::Parse($End, [Globalization.CultureInfo]::InvariantCulture) }
      if ($Location) { $it.Location = $Location }; if ($Body) { $it.Body = $Body }
      if ($Participants) { foreach ($p in $Participants.Split(";")) { if ($p.Trim()) { $r = $it.Recipients.Add($p.Trim()); $r.Type = 1 } }; $null = $it.Recipients.ResolveAll() }
      if ($it.MeetingStatus -eq 1 -and $it.Recipients.Count -gt 0) { $it.Send() } else { $it.Save() }
      Emit @{ ok = $true; op = $Op; retrieved_at = $started; entry_id = [string]$it.EntryID; subject = [string]$it.Subject; start = (Iso $it.Start); end = (Iso $it.End) }; exit 0
    }
    if ($Op -eq "calendar.cancel") {
      $id = [string]$it.EntryID
      if ($it.MeetingStatus -eq 1 -and $it.Recipients.Count -gt 0) { $it.MeetingStatus = 5; $it.Send() } else { $it.Delete() }
      Emit @{ ok = $true; op = $Op; retrieved_at = $started; entry_id = $id; cancelled = $true }; exit 0
    }
  }
  if ($Op -eq "mail.send" -and $EntryId) {
    # natural Outlook behaviour: send the EXISTING draft item (reviewed by the owner) — it leaves Drafts and lands in Sent Items
    $m = $ns.GetItemFromID($EntryId)
    if ($null -eq $m -or $m.Class -ne 43) { Emit @{ ok = $false; code = "BAD_PARAMS"; error = "EntryId is not a mail item" }; exit 3 }
    if ($m.Submitted -or $m.Sent) { Emit @{ ok = $false; code = "ALREADY_SENT"; error = "the item was already submitted/sent" }; exit 3 }
    $id = [string]$m.EntryID; $conv = [string]$m.ConversationID; $subj = [string]$m.Subject; $to = [string]$m.To
    # If the owner is looking at this very draft in the reading pane, Outlook holds it as an INLINE RESPONSE and refuses Send().
    # Natural behaviour: close the inline editor (saving the owner's edits), re-open the saved item by EntryID and send THAT.
    $inline = $false
    try {
      $exp = $ol.ActiveExplorer()
      if ($null -ne $exp) {
        $ir = $exp.ActiveInlineResponse
        if ($null -ne $ir -and ([string]$ir.EntryID -eq $id)) {
          # Close() does not release an inline editor; clearing the Explorer selection does. Save first so the owner's edits survive and no prompt appears.
          $inline = $true; if (-not $ir.Saved) { $ir.Save() }
          $exp.ClearSelection(); Start-Sleep -Milliseconds 600
          $m = $ns.GetItemFromID($id)
        }
      }
    } catch {}
    try { $m.Send() } catch {
      if ($_.Exception.Message -match "inline response") { Emit @{ ok = $false; code = "INLINE_RESPONSE"; error = "the draft is open in the Outlook reading pane (inline editor) — close it or select another item, then approve a new card"; entry_id = $id }; exit 3 }
      throw
    }
    Emit @{ ok = $true; op = $Op; retrieved_at = $started; submitted = $true; sent_draft = $true; inline_closed = $inline; entry_id = $id; subject = $subj; to = $to; conversation_id = $conv }; exit 0
  }
  if ($Op -eq "mail.draft" -or $Op -eq "mail.send") {
    if (-not $To -and -not $ReplyToEntryId) { Emit @{ ok = $false; code = "BAD_PARAMS"; error = "To required" }; exit 3 }
    if ($ReplyToEntryId) { $src = $ns.GetItemFromID($ReplyToEntryId); $m = $src.Reply(); if ($Body) { $m.Body = $Body + "`r`n`r`n" + $m.Body } } else { $m = $ol.CreateItem(0); $m.To = $To; if ($Cc) { $m.CC = $Cc }; $m.Subject = $Subject; $m.Body = $Body }
    if ($Op -eq "mail.draft") { $m.Save(); Emit @{ ok = $true; op = $Op; retrieved_at = $started; entry_id = [string]$m.EntryID; subject = [string]$m.Subject; to = [string]$m.To; folder = "Drafts" }; exit 0 }
    $conv = [string]$m.ConversationID; $subj = [string]$m.Subject; $to = [string]$m.To
    $m.Send()
    Emit @{ ok = $true; op = $Op; retrieved_at = $started; submitted = $true; subject = $subj; to = $to; conversation_id = $conv }; exit 0
  }
} catch {
  $hr = $null; try { $hr = ("0x{0:X8}" -f $_.Exception.HResult) } catch {}
  Emit @{ ok = $false; op = $Op; error = [string]$_.Exception.Message; hresult = $hr; code = "COM_ERROR" }
  exit 2
}
