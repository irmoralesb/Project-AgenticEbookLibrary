using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;

namespace EbookLibraryUI.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    private readonly IAppSettingsService _appSettingsService;
    private readonly IFolderPickerService _folderPickerService;

    [ObservableProperty]
    private string _coverImagePath = string.Empty;

    [ObservableProperty]
    private string _statusMessage = string.Empty;

    public SettingsViewModel(IAppSettingsService appSettingsService, IFolderPickerService folderPickerService)
    {
        _appSettingsService = appSettingsService;
        _folderPickerService = folderPickerService;
        CoverImagePath = _appSettingsService.CoverImagePath;
    }

    [RelayCommand]
    private void BrowseCoverPath()
    {
        var path = _folderPickerService.Pick("Select cover images folder");
        if (!string.IsNullOrWhiteSpace(path))
            CoverImagePath = path;
    }

    [RelayCommand]
    private async Task SaveAsync()
    {
        var normalizedPath = CoverImagePath.Trim();
        await _appSettingsService.SaveCoverImagePathAsync(normalizedPath);
        EbookDto.CoverImageRootPath = normalizedPath;
        CoverImagePath = normalizedPath;
        StatusMessage = "Settings saved.";
    }
}
