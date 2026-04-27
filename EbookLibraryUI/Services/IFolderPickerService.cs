namespace EbookLibraryUI.Services;

/// <summary>Abstraction over native folder-browser dialogs for testability.</summary>
public interface IFolderPickerService
{
    /// <summary>Show the OS folder picker and return the selected path, or null if cancelled.</summary>
    string? Pick(string title = "Select folder");
}
