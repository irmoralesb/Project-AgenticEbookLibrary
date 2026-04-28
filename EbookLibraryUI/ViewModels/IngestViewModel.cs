using System.Collections.ObjectModel;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;

namespace EbookLibraryUI.ViewModels;

public partial class IngestViewModel : ObservableObject
{
    private readonly IEbookApiService _api;
    private readonly IFolderPickerService _folderPicker;
    private readonly IAppSettingsService _appSettings;
    private CancellationTokenSource? _cts;

    public ObservableCollection<string> ProgressLog { get; } = [];

    public IReadOnlyList<string> Extensions { get; } = ["pdf", "epub"];

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(StartIngestCommand))]
    private string _selectedPath = string.Empty;

    [ObservableProperty]
    private string _selectedExtension = "pdf";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(StartIngestCommand))]
    private bool _isIngesting;

    [ObservableProperty]
    private string _statusMessage = string.Empty;

    [ObservableProperty]
    private string _coverImagePath = string.Empty;

    public IngestViewModel(IEbookApiService api, IFolderPickerService folderPicker, IAppSettingsService appSettings)
    {
        _api = api;
        _folderPicker = folderPicker;
        _appSettings = appSettings;
        CoverImagePath = _appSettings.CoverImagePath;
        _appSettings.CoverImagePathChanged += OnCoverImagePathChanged;
    }

    [RelayCommand]
    private void BrowseFolder()
    {
        var path = _folderPicker.Pick("Select ebook folder");
        if (path is not null)
            SelectedPath = path;
    }

    private bool CanStartIngest() => !IsIngesting && !string.IsNullOrWhiteSpace(SelectedPath);

    [RelayCommand(CanExecute = nameof(CanStartIngest))]
    private async Task StartIngestAsync()
    {
        ProgressLog.Clear();
        IsIngesting = true;
        StatusMessage = "Starting ingestion…";
        _cts = new CancellationTokenSource();

        try
        {
            var normalizedCoverImagePath = string.IsNullOrWhiteSpace(_appSettings.CoverImagePath)
                ? null
                : _appSettings.CoverImagePath.Trim();
            CoverImagePath = normalizedCoverImagePath ?? string.Empty;
            EbookDto.CoverImageRootPath = CoverImagePath;

            var startResponse = await _api.StartIngestAsync(new IngestRequestDto
            {
                Path = SelectedPath,
                Extension = SelectedExtension,
                CoverImagePath = normalizedCoverImagePath,
            }, _cts.Token);

            await foreach (var evt in _api.StreamIngestAsync(startResponse.JobId, _cts.Token))
            {
                // Marshal to UI thread.
                Application.Current.Dispatcher.Invoke(() => ProgressLog.Add(evt.Message));

                if (evt.IsEndOfStream)
                    break;
            }

            StatusMessage = "Ingestion complete.";
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "Ingestion cancelled.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error: {ex.Message}";
        }
        finally
        {
            IsIngesting = false;
            _cts?.Dispose();
            _cts = null;
        }
    }

    [RelayCommand]
    private void CancelIngest()
    {
        _cts?.Cancel();
    }

    private void OnCoverImagePathChanged(object? sender, string value)
    {
        CoverImagePath = value;
        EbookDto.CoverImageRootPath = value;
    }
}
