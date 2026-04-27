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

    public IngestViewModel(IEbookApiService api, IFolderPickerService folderPicker)
    {
        _api = api;
        _folderPicker = folderPicker;
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
            var startResponse = await _api.StartIngestAsync(new IngestRequestDto
            {
                Path = SelectedPath,
                Extension = SelectedExtension,
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
}
