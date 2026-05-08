using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.IO;
using System.Text;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;
using Microsoft.Win32;

namespace EbookLibraryUI.ViewModels;

public partial class IngestViewModel : ObservableObject
{
    private readonly IEbookApiService _api;
    private readonly IFolderPickerService _folderPicker;
    private CancellationTokenSource? _cts;

    public ObservableCollection<string> ProgressLog { get; } = [];

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(StartIngestCommand))]
    private string _selectedPath = string.Empty;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(StartIngestCommand))]
    private bool _isIngesting;

    [ObservableProperty]
    private string _statusMessage = string.Empty;

    public IngestViewModel(IEbookApiService api, IFolderPickerService folderPicker)
    {
        _api = api;
        _folderPicker = folderPicker;
        ProgressLog.CollectionChanged += OnProgressLogCollectionChanged;
    }

    private void OnProgressLogCollectionChanged(object? sender, NotifyCollectionChangedEventArgs e) =>
        SaveLogCommand.NotifyCanExecuteChanged();

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
            }, _cts.Token);

            await foreach (var evt in _api.StreamIngestAsync(startResponse.JobId, _cts.Token))
            {
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

    private bool CanSaveLog() => ProgressLog.Count > 0;

    [RelayCommand(CanExecute = nameof(CanSaveLog))]
    private async Task SaveLogAsync()
    {
        var dlg = new SaveFileDialog
        {
            Filter = "Text files (*.txt)|*.txt|All files (*.*)|*.*",
            DefaultExt = ".txt",
            FileName = "ingest-log.txt",
        };

        if (dlg.ShowDialog() != true)
            return;

        try
        {
            var text = string.Join(Environment.NewLine, ProgressLog);
            await File.WriteAllTextAsync(dlg.FileName, text, Encoding.UTF8).ConfigureAwait(true);
            StatusMessage = $"Log saved to {dlg.FileName}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not save log: {ex.Message}";
        }
    }
}
