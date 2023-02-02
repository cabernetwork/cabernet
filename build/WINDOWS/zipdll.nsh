;ZipDLL include file for NSIS
;Written by Tim Kosse (mailto:tim.kosse@gmx.de)
;some improvements by deguix

;Supported languages with their translators in alphabetical order:

;Arabic translation by asdfuae
;Brazilian Portuguese translation by "deguix"
;Chinese, Simplified translation by Kii Ali <kiiali@cpatch.org>
;Chinese, Traditional traslation by "matini" and Kii Ali <kiiali@cpatch.org>
;Croatian translation by "iostriz"
;Danish translation by Claus Futtrup
;French translation by "veekee"
;German translation by Tim Kosse
;Hungarian translation by Toth Laszlo
;Korean translation by Seongab Kim
;Lithuanian translation by Vytautas Krivickas
;Polish translation by Krzysztof Galuszka
;Russion translation by Sergey
;Spanish translation by "dark_boy"

!ifndef ZIPDLL_USED

!define ZIPDLL_USED

!macro ZIPDLL_EXTRACT SOURCE DESTINATION FILE

  !define "FILE_${FILE}"

  !ifndef FILE_<ALL>
    Push "${FILE}"
  !endif

  IfFileExists "${DESTINATION}" +2
    CreateDirectory "${DESTINATION}"

  Push "${DESTINATION}"

  IfFileExists "${SOURCE}" +2
    SetErrors

  Push "${SOURCE}"

  ;The strings that will be translated are (ready to copy,
  ;remove leading semicolons in your language block):

  !ifdef LANG_ENGLISH

    ;English is default language of ZipDLL, no need to push the untranslated strings

    ;StrCmp $LANGUAGE ${LANG_ENGLISH} 0 +1

      ;Push "  Error: %s"
      ;Push "Could not get file attributes."
      ;Push "Error: Could not get file attributes."
      ;Push "Could not extract %s"
      ;Push "  Error: Could not extract %s"

      ;!ifdef FILE_<ALL>
        ;Push "  Extract: %s"
        ;Push "  Extracting %d files and directories"
        ;Push "Extracting contents of %s to %s"
      ;!else
        ;Push "Specified file does not exist in archive."
        ;Push "Error: Specified file does not exist in archive."
        ;Push "Extracting the file %s from %s to %s"
      ;!endif

      ;Push "/TRANSLATE"

  !endif

  !ifdef LANG_GERMAN

    StrCmp $LANGUAGE ${LANG_GERMAN} 0 +10

      Push "  Fehler: %s"
      Push "Dateiattribute konnten nicht ermittelt werden."
      Push "Fehler: Dateiattribute konnten nicht ermittelt werden."
      Push "%s konnte nicht dekomprimiert werden."
      Push "  Fehler: %s konnte nicht dekomprimiert werden."

      !ifdef FILE_<ALL>
        Push "  Dekomprimiere: %s"
        Push "  Dekomprimiere %d Dateien und Verzeichnisse"
        Push "Dekomprimiere Inhalt von %s nach %s"
      !else
        Push "Die angegebene Datei existiert nicht im Archiv"
        Push "Fehler: Die angegebene Datei existiert nicht im Archiv"
        Push "Dekomprimiere Datei %s von %s nach %s"
      !endif

      Push "/TRANSLATE"

  !endif

  !ifdef LANG_SPANISH

    StrCmp $LANGUAGE ${LANG_SPANISH} 0 +10

      Push "  Error: %s"
      Push "No se obtuvieron atributos del archivo"
      Push "Error: No se obtuvieron atributos del archivo"
      Push "No se pudo extraer %s"
      Push "  Error: No se pudo extraer %s"

      !ifdef FILE_<ALL>
        Push "  Extraer: %s"
        Push "  Extrayendo %d archivos y directorios"
        Push "Extraer archivos de %s a %s"
      !else
        Push "Archivo especificado no existe en el ZIP"
        Push "Error: El archivo especificado no existe en el ZIP"
        Push "Extrayendo el archivo %s de %s a %s"
      !endif

      Push "/TRANSLATE"

  !endif


  !ifdef FILE_<ALL>
    ZipDLL::extractall
  !else
    ZipDLL::extractfile
  !endif

  !undef "FILE_${FILE}"

!macroend

!endif
