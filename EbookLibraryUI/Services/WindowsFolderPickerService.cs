using Microsoft.Win32;

namespace EbookLibraryUI.Services;

/// <summary>Windows implementation using the built-in <see cref="OpenFolderDialog"/> (.NET 8).</summary>
public class WindowsFolderPickerService : IFolderPickerService
{
    public string? Pick(string title = "Select folder")
    {
        var dialog = new OpenFolderDialog
        {
            Title = title,
            Multiselect = false,
        };

        return dialog.ShowDialog() == true ? dialog.FolderName : null;
    }
}
