                              ZipDLL v1.2.2a
                              --------------
                            Copyright 2002-2004 
                               by Tim Kosse
                              tim.kosse@gmx.de

What is this?
-------------

  ZipDLL is a extension DLL for NSIS. It can unzip files from
  zip files. It is especially useful in combination with NSISdl so 
  that you don't have to download large files uncompressed.

Usage
-----

  To extract files from a zip file, use the following macro:

  !insertmacro ZIPDLL_EXTRACT SOURCE DESTINATION FILE

  Parameters:  Zip file, destination directory, file to extract
  Description: Extract the specified file in the archive to the 
               destination directory.
               If file is &lt;ALL&gt;, all files in the archive
               will be extracted.

  Example:
    !insertmacro MUI_ZIPDLL_EXTRACTALL "c:\test.zip" "c:\output"

  
  Exported Functions:
  - extractall
    Parameters: Zip file, destination directory
    Description: Extracts all files in the archive to the destination
                 directory.

  - extractfile
    Parameters: Zip file, destination directory, file to extract
    Description: Extracts the specified file in the archive to the destination
                 directory.

  Example:
    ZipDLL::extractall "c:\test.zip" "c:\output"

Supported languages
-------------------

ZipDLL.nsh contains the following additional languages:
- Arabic
- Brazilian
- Chinese Simplified
- Chinese Traditional
- Croatian
- Danish
- French
- German
- Hungarian
- Korean
- Lithuanian
- Polish
- Russian
- Spanish

To add your language, simply modify ZipDLL.nsh, should be really easy. 
Please send the modified ZipDLL.nsh to tim.kosse@gmx.de so that other people can 
benfit from it, too.

Legal Stuff
-----------

  This NSIS plugin is licensed under the GPL, please read the file ZipArchive\glp.txt
  for details.
  
  ZipDLL uses the ZipArchive library from http://www.artpol-software.com/index_zip.html
  Please read the file ZipArchive\license.txt for details

  Alternative license for use with proprietary software:
  ------------------------------------------------------

  Since ZipArchive is licensed under the GPL, it may only be used with programs with a
  GPL compatible license, the same applies to this DLL.
  You can, however obtain a commercial license (free of charge for freeware and most 
  shareware programs) for ZipArchive. Please read ZipArchive\license.txt for details.
  Permission is granted to use ZipDLL together with prorietary software when you've
  obtained a license for ZipArchive.

Version History
---------------

1.2.2a
------

- added Croatian and Hungarian language

1.2.2
-----

- Added a lot of languages
- Some improvements for ZipDll.nsh made by deguix

1.2.1
-----

- Made compatible with NSIS 2b3

1.2
---

- Added macros for automatic language selection
- Translation possible, works like /translate switch for NsisDL plugin

1.1
---

- made compatible with latest NSIS (parameters on stack swapped)
- cleaned up code

1.0
---

- initial release
   