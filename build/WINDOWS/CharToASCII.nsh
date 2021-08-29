!define CharToASCII "!insertmacro CharToASCII" 
 
!macro CharToASCII AsciiCode Character
  Push "${Character}"
  Call CharToASCII
  Pop "${AsciiCode}"
!macroend
 
Function CharToASCII
  Exch $0 ; given character
  Push $1 ; current character
  Push $2 ; current Ascii Code   
 
  StrCpy $2 1 ; right from start
Loop:
  IntFmt $1 %c $2 ; Get character from current ASCII code
  ${If} $1 S== $0 ; case sensitive string comparison
     StrCpy $0 $2
     Goto Done
  ${EndIf}
  IntOp $2 $2 + 1
  StrCmp $2 255 0 Loop ; ascii from 1 to 255
  StrCpy $0 0 ; ASCII code wasn't found -> return 0
Done:         
  Pop $2
  Pop $1
  Exch $0
FunctionEnd