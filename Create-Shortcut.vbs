' AquaMark for Windows - create a desktop shortcut
' ASCII-only for the same reason as the .bat files.
Option Explicit

Dim fso, ws, here, target, icon, lnk, desktop

Set fso  = CreateObject("Scripting.FileSystemObject")
Set ws   = CreateObject("WScript.Shell")

here    = fso.GetParentFolderName(WScript.ScriptFullName)
target  = fso.BuildPath(here, "Start-AquaMark.bat")
icon    = fso.BuildPath(here, "AquaMark.ico")
desktop = ws.SpecialFolders("Desktop")

If Not fso.FileExists(target) Then
  WScript.Echo "Cannot find Start-AquaMark.bat next to this script."
  WScript.Quit 1
End If

Set lnk = ws.CreateShortcut(fso.BuildPath(desktop, "AquaMark.lnk"))
lnk.TargetPath       = target
lnk.WorkingDirectory = here
If fso.FileExists(icon) Then
  lnk.IconLocation = icon & ",0"
End If
lnk.Description      = "AquaMark - retro Aqua Markdown editor"
lnk.Save

WScript.Echo "Desktop shortcut created: AquaMark" & vbCrLf & _
             "Double-click it to open AquaMark." & vbCrLf & _
             "Tip: F11 toggles full screen once the app is running."
