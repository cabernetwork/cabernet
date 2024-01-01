Var Dialog
Var lblLabel
Var lblUsername
Var lblPassword
Var txtUsername
Var pwdPassword
Var pwdConfirmPassword
Var hwnd
Var user
Var pwd
Var pwd2
Var subfolder
Var cmd
Var pythoninstall
Var pythonpath
Var DataFolder
Var txtDataFolder
Var BROWSEDATA

!include "CharToASCII.nsh"
!include "Base64.nsh"


Function DataFolderPage
    nsDialogs::Create /NOUNLOAD 1018
    Pop $Dialog
    ${If} $Dialog == error
        Abort
    ${EndIf}
    CreateDirectory "$DataFolder"
    ${NSD_CreateLabel} 0 0 100% 24u "Please specify the Cabernet data folder. \
        Writeable by the user: System$\r$\nIt is highly recommended to have \
        this folder be easy to access."
    ${NSD_CreateGroupBox} 0 40u 100% 34u "Data Folder"
        ${NSD_CreateText} 3% 54u 77% 12u "$DataFolder"
        Pop $txtDataFolder
        ${NSD_CreateBrowseButton} 82% 54u 15% 13u "Browse"
        pop $BROWSEDATA
        ${NSD_OnClick} $BROWSEDATA BrowseData
    nsDialogs::Show
FunctionEnd

Function BrowseData
    nsDialogs::SelectFolderDialog "Select Data Folder" "$DataFolder"
    pop $0
    ${If} $0 != error
        ${NSD_SetText} $txtDataFolder $0
        StrCpy $DataFolder $0
    ${EndIf}
FunctionEnd

Function DataFolderPageLeave
    ${NSD_GetText} $txtDataFolder $DataFolder
FunctionEnd

Function UserPassPage
    nsDialogs::Create /NOUNLOAD 1018
    Pop $Dialog
    ${If} $Dialog == error
        Abort
    ${EndIf}
    ${NSD_CreateLabel} 0 0 100% 24u "Please specify LocastUsername and Password."
    Pop $lblLabel
    ${NSD_CreateLabel} 0 30u 60u 12u "Username:"
    Pop $lblUsername
    ${NSD_CreateText} 65u 30u 50% 12u ""
    Pop $txtUsername
    ${NSD_CreateLabel} 0 45u 60u 12u "Password:"
    Pop $lblPassword
    ${NSD_CreatePassword} 65u 45u 50% 12u ""
    Pop $pwdPassword
    ${NSD_CreateLabel} 0 60u 60u 12u "Confirm Password:"
    Pop $lblPassword
    ${NSD_CreatePassword} 65u 60u 50% 12u ""
    Pop $pwdConfirmPassword
    ${NSD_CreateCheckbox} 65u 75u 50% 12u "Show password"
    Pop $hwnd
    ${NSD_OnClick} $hwnd ShowPassword
    nsDialogs::Show
FunctionEnd

Function UserPassPageLeave
    ${NSD_GetText} $txtUsername $user
    ${NSD_GetText} $pwdPassword $pwd
    ${NSD_GetText} $pwdConfirmPassword $pwd2
    ${If} $user == ""
    ${OrIf} $pwd == ""
    ${OrIf} $pwd2 == ""
        MessageBox MB_OK "All entries are required"
        Abort
    ${EndIf}
    ${If} $pwd != $pwd2
        MessageBox MB_OK "passwords do not match, try again"
        Abort
    ${EndIf}
    ${Base64_Encode} $pwd
    Pop $0
    StrCpy $pwd $0
FunctionEnd

Function ShowPassword
    Pop $hwnd
    ${NSD_GetState} $hwnd $0
    ShowWindow $pwdPassword ${SW_HIDE}
    ShowWindow $pwdConfirmPassword ${SW_HIDE}
    ${If} $0 == 1
        SendMessage $pwdPassword ${EM_SETPASSWORDCHAR} 0 0
        SendMessage $pwdConfirmPassword ${EM_SETPASSWORDCHAR} 0 0
    ${Else}
        SendMessage $pwdPassword ${EM_SETPASSWORDCHAR} 42 0
        SendMessage $pwdConfirmPassword ${EM_SETPASSWORDCHAR} 42 0
    ${EndIf}
    ShowWindow $pwdPassword ${SW_SHOW}
    ShowWindow $pwdConfirmPassword ${SW_SHOW}
FunctionEnd

Function TestPython
    !define SOURCEPATH "../.."
    SetOutPath "$INSTDIR"
    File "${SOURCEPATH}\build\WINDOWS\findpython.pyw"
    StrCpy $cmd 'python findpython.pyw'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 PythonFound
        MessageBox MB_OK "Python 3.x not found, Make sure to install python$\r$\n\
            for all users if a Windows Service is needed or single user$\r$\n\
            without admin access"
        StrCpy $pythonpath ""
        Goto PythonMissing
    PythonFound:
    MessageBox MB_OK "Using Python installation $1$\r$\n\
        If this is not correct, please uninstall the unwanted python versions"
    Push $1
    Call Trim
    Pop $pythonpath
    Call ClearPythonInstallFlag
    PythonMissing:
    Delete $INSTDIR\findpython.pyw
FunctionEnd

Function TestPythonSilent
    SetOutPath "$INSTDIR"
    File "${SOURCEPATH}\build\WINDOWS\findpython.pyw"
    nsExec::ExecToStack 'python findpython.pyw'
    Pop $0 ;return value
    Pop $1 ;return value
    IntCmp $0 0 PythonFound
        StrCpy $pythonpath ""
        Goto PythonMissing
    PythonFound:
    Push $1
    Call Trim
    Pop $pythonpath
    ;StrCpy $pythonpath $1
    PythonMissing:
    Delete $INSTDIR\findpython.pyw
FunctionEnd

Function UpdateConfig
    SetOutPath "$INSTDIR"
    StrCpy $cmd 'python -m build.WINDOWS.UpdateConfig -i "$INSTDIR" -d "$DataFolder"'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 PythonDone
        MessageBox MB_OK "Unable to update Config file. Edit the file manually. $0 $1"
    PythonDone:
FunctionEnd

Function AddFiles
    ; !define SOURCEPATH "../.."
    SetOutPath "$INSTDIR"
    File "${SOURCEPATH}\tvh_main.py"
    File "${SOURCEPATH}\LICENSE"
    File "${SOURCEPATH}\CHANGELOG.md"
    File "${SOURCEPATH}\.dockerignore"
    File "${SOURCEPATH}\docker-compose.yml"
    File "${SOURCEPATH}\Dockerfile"
    File "${SOURCEPATH}\Dockerfile_tvh"
    File "${SOURCEPATH}\Dockerfile_tvh_crypt.alpine"
    File "${SOURCEPATH}\Dockerfile_tvh_crypt.alpine"
    File "${SOURCEPATH}\Dockerfile_tvh_crypt.slim-buster"
    File "${SOURCEPATH}\README.md"
    File "${SOURCEPATH}\TVHEADEND.md"
    File "${SOURCEPATH}\requirements.txt"
    Rename "$INSTDIR\TVHEADEND.md" "$INSTDIR\README.txt"

    SetOutPath "$INSTDIR\lib"
    File /r /x __pycache__ /x development "${SOURCEPATH}\lib\*.*"
    SetOutPath "$INSTDIR\plugins"
    File /r /x __pycache__ "${SOURCEPATH}\plugins\*.*"

    SetOutPath "$INSTDIR\build\WINDOWS"
    File "${SOURCEPATH}\build\WINDOWS\UpdateConfig.pyw"
FunctionEnd

; arg: $subfolder
; return: $subfolder
Function GetSubfolder
    FindFirst $0 $1 "$subfolder"
    StrCmp $1 "" empty
    ${If} ${FileExists} "$subfolder"
        StrCpy $subfolder $1
    ${EndIf}
    Goto done
    empty:
    StrCpy $subfolder ""
    done:
    FindClose $0
FunctionEnd


Function InstallService
    Call TestPythonSilent
    StrCmp "$pythonpath" "" 0 found
        MessageBox MB_OK "Unable to detect python install, aborting $pythonpath"
        Abort
    found:
    StrCpy $cmd '"$INSTDIR\lib\tvheadend\service\Windows\nssm.exe" install Cabernet \
        "$pythonpath" "\""$INSTDIR\tvh_main.py\""" -c "\""$DataFolder\config.ini\"""'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 5 ServiceAlreadyInstalled
    IntCmp $0 0 ServiceDone
        MessageBox MB_OK "Service not installed. status:$0 $1"
    ServiceDone:
    StrCpy $cmd '$INSTDIR\lib\tvheadend\service\Windows\nssm.exe set Cabernet AppDirectory "$INSTDIR"'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 Service2Done
        MessageBox MB_OK "Service update AppDirectory failed.  status:$0 $1"
    Service2Done:
    CreateDirectory "$TEMP\cabernet"
    StrCpy $cmd '$INSTDIR\lib\tvheadend\service\Windows\nssm.exe set Cabernet AppStdout "$TEMP\cabernet\out.log"'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 Service3Done
        MessageBox MB_OK "Service update AppDirectory failed.  status:$0 $1"
    Service3Done:
    StrCpy $cmd '$INSTDIR\lib\tvheadend\service\Windows\nssm.exe set Cabernet AppStderr "$TEMP\cabernet\error.log"'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 Service4Done
        MessageBox MB_OK "Service update AppDirectory failed.  status:$0 $1"
    Service4Done:
    StrCpy $cmd '$INSTDIR\lib\tvheadend\service\Windows\nssm.exe set Cabernet AppStdoutCreationDisposition 2'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 Service5Done
        MessageBox MB_OK "Service update AppDirectory failed.  status:$0 $1"
    Service5Done:
    StrCpy $cmd '$INSTDIR\lib\tvheadend\service\Windows\nssm.exe set Cabernet AppStderrCreationDisposition 2'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 Service6Done
        MessageBox MB_OK "Service update AppDirectory failed.  status:$0 $1"
    Goto Service6Done
    ServiceAlreadyInstalled:
    MessageBox MB_OK "Service already installed"
    Service6Done:
FunctionEnd


Function un.installService
    StrCpy $cmd '"$INSTDIR\lib\tvheadend\service\Windows\nssm.exe" stop Cabernet'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    StrCpy $cmd '"$INSTDIR\lib\tvheadend\service\Windows\nssm.exe" remove Cabernet confirm'
    nsExec::ExecToStack '$cmd'
    Pop $0 ;return value
    Pop $1 ; status text
    IntCmp $0 0 ServiceDone
        MessageBox MB_OK "Service not uninstalled. status:$0 $1"
    ServiceDone:
FunctionEnd


; Trim
;   Removes leading & trailing whitespace from a string
; Usage:
;   Push
;   Call Trim
;   Pop
Function Trim
	Exch $R1 ; Original string
	Push $R2
Loop:
	StrCpy $R2 "$R1" 1
	StrCmp "$R2" " " TrimLeft
	StrCmp "$R2" "$\r" TrimLeft
	StrCmp "$R2" "$\n" TrimLeft
	StrCmp "$R2" "$\t" TrimLeft
	GoTo Loop2
TrimLeft:
	StrCpy $R1 "$R1" "" 1
	Goto Loop
Loop2:
	StrCpy $R2 "$R1" 1 -1
	StrCmp "$R2" " " TrimRight
	StrCmp "$R2" "$\r" TrimRight
	StrCmp "$R2" "$\n" TrimRight
	StrCmp "$R2" "$\t" TrimRight
	GoTo Done
TrimRight:
	StrCpy $R1 "$R1" -1
	Goto Loop2
Done:
	Pop $R2
	Exch $R1
FunctionEnd
