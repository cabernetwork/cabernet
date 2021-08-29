// ZipDLL.cpp : Definiert den Einsprungpunkt für die DLL-Anwendung.
//

#include "ZipArchive\ZipArchive.h"
#include "exdll.h"
#include <commctrl.h>

BOOL APIENTRY DllMain( HANDLE hModule, 
                       DWORD  ul_reason_for_call, 
                       LPVOID lpReserved
					 )
{
    return TRUE;
}

HWND g_hwndDlg, g_hwndList;

void LogMessage(const char *pStr);
void SetStatus(const char *pStr);

extern "C" void __declspec(dllexport) extractall(HWND hwndParent, int string_size, 
                                      char *variables, stack_t **stacktop)
{
	EXDLL_INIT();
	
	g_hwndDlg = g_hwndList = 0;
	
	// do your stuff here
	g_hwndDlg=FindWindowEx(hwndParent,NULL,"#32770",NULL);
	if (g_hwndDlg)
		g_hwndList=FindWindowEx(g_hwndDlg,NULL,"SysListView32",NULL);	
	
	//Extract file to destination
	char destination[MAX_PATH+1];
	char source[MAX_PATH+1];
	char buffer[4096];

	char szExtracting[MAX_PATH * 2 + 100] =			"Extracting contents of %s to %s";
	char szExtractingPrintCount[200] =				"  Extracting %d files and directories";
	char szExtractFile[MAX_PATH + 50] =				"  Extract : %s";
	char szErrorCouldNotExtract[MAX_PATH + 100] =	"  Error: Could not extract %s";
	char szCouldNotExtract[MAX_PATH + 100] =		"Could not extract %s";
	char szErrorCouldNotGetFileAttributes[100] =	"Error: Could not get file attributes.";
	char szCouldNotGetFileAttributes[100] =			"Could not get file attributes.";
	char szError[1000] =							"  Error: %s";

	popstring(source);

	if (!lstrcmpi(source, "/TRANSLATE")) {
		//Use localized strings
		popstring(szExtracting);
		popstring(szExtractingPrintCount);
		popstring(szExtractFile);
		popstring(szErrorCouldNotExtract);
		popstring(szCouldNotExtract);
		popstring(szErrorCouldNotGetFileAttributes);
		popstring(szCouldNotGetFileAttributes);
		popstring(szError);
		popstring(source);
	}
		
	popstring(destination);

	sprintf(buffer, szExtracting, source, destination);
	LogMessage(buffer);
	try
	{
		// Open archive
		CZipArchive archive;
		archive.Open(source, CZipArchive::zipOpenReadOnly);
		
		// Get number of entries in archive
		int nCount=archive.GetCount();
		sprintf(buffer, szExtractingPrintCount, nCount);
		LogMessage(buffer);

		//Process each file in archive
		for (int i=0;i<nCount;i++)
		{
			//Get file attributes
			CZipFileHeader fi;
			if (archive.GetFileInfo(fi, i))
			{
				//Extract file
				sprintf(buffer, szExtractFile, (LPCTSTR)fi.GetFileName());
				SetStatus(buffer);
				
				if (!archive.ExtractFile(i, destination))
				{
					sprintf(buffer, szErrorCouldNotExtract, (LPCTSTR)fi.GetFileName());
					LogMessage(buffer);
					sprintf(buffer, szCouldNotExtract, (LPCTSTR)fi.GetFileName());
					pushstring(buffer);
					return;
				}
			}
			else
			{
				LogMessage(szErrorCouldNotGetFileAttributes);
				pushstring(szCouldNotGetFileAttributes);
				return;
			}
		}
		archive.Close();
	}
	catch(CZipException e)
	{
		const char *desc=e.GetErrorDescription();
		pushstring(desc);
		sprintf(buffer, szError, (LPCTSTR)desc);
		LogMessage(buffer);
		return;
	}
	pushstring("success");
}


extern "C" void __declspec(dllexport) extractfile(HWND hwndParent, int string_size, 
                                      char *variables, stack_t **stacktop)
{
	EXDLL_INIT();
	
	g_hwndDlg = g_hwndList = 0;
	
	// do your stuff here
	g_hwndDlg=FindWindowEx(hwndParent, NULL, "#32770", NULL);
	if (g_hwndDlg)
		g_hwndList=FindWindowEx(g_hwndDlg, NULL, "SysListView32", NULL);
	
	//Extract file to destination
	char file[MAX_PATH+1];
	char destination[MAX_PATH+1];
	char source[MAX_PATH+1];
	char buffer[4096];
					
	char szExtracting[MAX_PATH * 3 + 100] =			"Extracting the file %s from %s to %s";
	char szErrorFileDoesNotExist[100] =				"Error: Specified file does not exist in archive.";
	char szFileDoesNotExist[100] =					"Specified file does not exist in archive.";
	char szErrorCouldNotExtract[MAX_PATH + 100] =	"  Error: Could not extract %s";
	char szCouldNotExtract[MAX_PATH + 100] =		"Could not extract %s";
	char szErrorCouldNotGetFileAttributes[100] =	"Error: Could not get file attributes.";
	char szCouldNotGetFileAttributes[100] =			"Could not get file attributes.";
	char szError[1000] =							"  Error: %s";

	popstring(source);

	if (!lstrcmpi(source, "/TRANSLATE")) {
		//Use localized strings
		popstring(szExtracting);
		popstring(szErrorFileDoesNotExist);
		popstring(szFileDoesNotExist);
		popstring(szErrorCouldNotExtract);
		popstring(szCouldNotExtract);
		popstring(szErrorCouldNotGetFileAttributes);
		popstring(szCouldNotGetFileAttributes);
		popstring(szError);
		popstring(source);
	}
	
	popstring(destination);
	popstring(file);
	
	sprintf(buffer, szExtracting, file, source, destination);
	SetStatus(buffer);
	try
	{
		//Open archive
		CZipArchive archive;
		archive.Open(source, CZipArchive::zipOpenReadOnly);

		//Find file in archive
		int index=archive.FindFile(file);
		if (index==-1)
		{
			LogMessage(szErrorFileDoesNotExist);
			pushstring(szFileDoesNotExist);
			return;
		}
  
		//Get file attributes
		CZipFileHeader fi;
		if (archive.GetFileInfo(fi, index))
		{
			//Extract file		
			if (!archive.ExtractFile(index, destination))
			{
				sprintf(buffer, szErrorCouldNotExtract, (LPCTSTR)fi.GetFileName());
				LogMessage(buffer);
				sprintf(buffer, szCouldNotExtract, (LPCTSTR)fi.GetFileName());
				pushstring(buffer);
				return;
			}
		}
		else
		{
			LogMessage(szErrorCouldNotGetFileAttributes);
			pushstring(szCouldNotGetFileAttributes);
			return;
		}

		archive.Close();
	}
	catch(CZipException e)
	{
		const char *desc=e.GetErrorDescription();
		pushstring(desc);
		sprintf(buffer, szError, desc);
		LogMessage(buffer);
		return;
	}
	pushstring("success");
}

void SetStatus(const char *pStr)
{
	if (g_hwndDlg)
	{
		HWND hwndCtrl=GetDlgItem(g_hwndDlg, 1006);
		if (hwndCtrl)
			SetWindowText(hwndCtrl, pStr);
	}
	LogMessage(pStr);
	return;
}

void LogMessage(const char *pStr)
{
	if (!g_hwndList)
		return;

	LVITEM item={0};
	int nItemCount=SendMessage(g_hwndList, LVM_GETITEMCOUNT, 0, 0);
	item.mask=LVIF_TEXT;
	item.pszText=(char *)pStr;
	item.cchTextMax=strlen(pStr);
	item.iItem=nItemCount;
	ListView_InsertItem(g_hwndList, &item);
    ListView_EnsureVisible(g_hwndList, item.iItem, 0);
    return;
}