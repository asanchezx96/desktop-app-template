; Script de Inno Setup para el instalador de Windows.
#define MyAppName "DesktopAppTemplate"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Tu Empresa"
#define MyAppExeName "DesktopAppTemplate.exe"

[Setup]
AppId={{49CBD4D1-3087-4BAB-8CE3-532E5ED78ADB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; Directorio de instalación por defecto
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename={#MyAppName}-setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compresión optimizada
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Soporte nativo para sistemas de 64 bits
ArchitecturesInstallIn64BitMode=x64compatible

; Privilegios: permite al usuario instalar para sí mismo (sin Admin) o para todos los usuarios
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Detectar y cerrar automáticamente instancias previas durante la instalación/actualización
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "runonstartup"; Description: "Iniciar {#MyAppName} automáticamente al arrancar Windows"; GroupDescription: "Configuración adicional:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Agregar clave al registro de Windows para ejecutar al iniciar sesión (solo si el usuario lo selecciona)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: runonstartup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
