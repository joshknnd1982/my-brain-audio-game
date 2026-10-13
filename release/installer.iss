; Inno Setup 6 script: My Brain by Josh Kennedy, inspired by Jim Kitchen (Brain clone).
; Phase 10 (playbook 8.2). Compile (from anywhere):
;   "C:\Users\joshk\AppData\Local\Programs\Inno Setup 6\ISCC.exe" "<game folder>\release\installer.iss"
; Optional defines: /DAppVersion=1.0.0  /DBuild64=<dist\brain folder>  /DBuild32=<dist\brain folder>
; Run clone\tools\build.ps1 first so the build folders are fresh. Output: brain-setup-<version>.exe in this folder.
;
; Design decisions (DECISIONS.md, P10):
;  - One installer holds both builds and installs the one that fits the Windows (64-bit or 32-bit).
;  - Per-user install by default (no administrator rights); the player may choose all users in the first dialog.
;  - The program folder holds only program files. Settings, player sounds and logs live in
;    %APPDATA%\Kitchensinc Revival\Brain; install, update and uninstall never touch them
;    (the uninstaller asks, default keep).
;  - An update removes the old _internal folder first (stale library files), never assets\sounds' extras.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef Build64
  #define Build64 "C:\Users\joshk\.kitchensinc-builds\brain\64\dist\brain"
#endif
#ifndef Build32
  #define Build32 "C:\Users\joshk\.kitchensinc-builds\brain\32\dist\brain"
#endif

[Setup]
; Never change this GUID: it is how a newer version finds and replaces an older one.
AppId={{6F2B8C14-3A7D-4E95-B1C0-5D9E47A82F36}
AppName=My Brain
AppVersion={#AppVersion}
AppVerName=My Brain {#AppVersion}
AppPublisher=Josh Kennedy
AppPublisherURL=https://github.com/joshknnd1982
AppSupportURL=https://github.com/joshknnd1982
AppUpdatesURL=https://github.com/joshknnd1982
VersionInfoVersion={#AppVersion}
VersionInfoDescription=My Brain by Josh Kennedy, inspired by Jim Kitchen (setup)
VersionInfoCopyright=Copyright (c) 2026 Josh Kennedy
DefaultDirName={autopf}\My Brain
DefaultGroupName=My Brain
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=.
OutputBaseFilename=brain-setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
LicenseFile=..\LICENSE
InfoBeforeFile=installer_info.txt
UninstallDisplayName=My Brain
UninstallDisplayIcon={app}\brain.exe
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[InstallDelete]
; Library files of an older build that this build no longer has. Only our own folder.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#Build64}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Check: Is64BitInstallMode
Source: "{#Build32}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Check: not Is64BitInstallMode

[Icons]
Name: "{group}\My Brain"; Filename: "{app}\brain.exe"
Name: "{group}\My Brain read me"; Filename: "{app}\README.txt"
Name: "{group}\Uninstall My Brain"; Filename: "{uninstallexe}"
Name: "{autodesktop}\My Brain"; Filename: "{app}\brain.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\brain.exe"; Description: "Start My Brain now"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Code]
// Uninstall: the program goes, the player's settings, own sounds and log stay unless the player says yes.
// Silent uninstall keeps them too, unless the command line has /DELETEUSERDATA=1 (used by the scripted tests).
// {param:} is not expanded inside the uninstaller, so the command line is read by hand.
function WantsDeleteUserData: Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/DELETEUSERDATA=1') = 0 then Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir, Vendor: String;
  DoDelete: Boolean;
begin
  if CurUninstallStep <> usPostUninstall then Exit;
  Vendor := ExpandConstant('{userappdata}\Kitchensinc Revival');
  DataDir := Vendor + '\Brain';
  if not DirExists(DataDir) then Exit;
  DoDelete := WantsDeleteUserData;
  if (not DoDelete) and (not UninstallSilent) then
    DoDelete := MsgBox('Also delete your My Brain settings, your own sounds and the log?' + #13#10 + #13#10 +
      'They are in ' + DataDir + #13#10 + #13#10 +
      'Choose No to keep them (recommended if you may install My Brain again).',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  if DoDelete then
  begin
    DelTree(DataDir, True, True, True);
    RemoveDir(Vendor);   // only if nothing else (another Kitchensinc game) is in it
  end;
end;
