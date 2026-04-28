namespace EbookLibraryUI.Services;

public interface IAppSettingsService
{
    string CoverImagePath { get; }
    bool SettingsFileExists { get; }
    bool HasConfiguredCoverImagePath { get; }
    event EventHandler<string>? CoverImagePathChanged;

    Task InitializeAsync();
    Task SaveCoverImagePathAsync(string coverImagePath);
}
