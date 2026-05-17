using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;

namespace EbookLibraryUI.ViewModels;

public enum LibraryErrorFilter
{
    All,
    HasErrorsOnly,
    NoErrorsOnly,
}

public partial class LibraryViewModel : ObservableObject
{
    private static readonly Regex PageRangeRe = new(@"^\s*\d+\s*-\s*\d+\s*$", RegexOptions.Compiled);

    private const int PageSize = 15;

    private readonly IEbookApiService _api;

    private int _nextSkip;
    private string _appliedPublisher = string.Empty;
    private string _appliedCategory = string.Empty;
    private string _appliedTagsFilter = string.Empty;
    private bool _appliedTagsEmptyOnly;
    private LibraryErrorFilter _appliedErrorFilter = LibraryErrorFilter.All;

    public ObservableCollection<LibraryBookRowViewModel> Books { get; } = [];

    public ObservableCollection<string> ProgressLog { get; } = [];

    [ObservableProperty]
    private string _publisherFilterText = string.Empty;

    [ObservableProperty]
    private string _categoryFilterText = string.Empty;

    [ObservableProperty]
    private string _tagsFilterText = string.Empty;

    [ObservableProperty]
    private bool _tagsEmptyOnly;

    public bool IsTagsTextFilterEnabled => !TagsEmptyOnly;

    partial void OnTagsEmptyOnlyChanged(bool value) =>
        OnPropertyChanged(nameof(IsTagsTextFilterEnabled));

    [ObservableProperty]
    private LibraryErrorFilter _errorFilter = LibraryErrorFilter.All;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private bool _isLoadingMore;

    [ObservableProperty]
    private bool _hasMorePages = true;

    [ObservableProperty]
    private string _statusMessage = string.Empty;

    [ObservableProperty]
    private LibraryBookRowViewModel? _selectedBook;

    [ObservableProperty]
    private bool _isBatchUpdateMode;

    [ObservableProperty]
    private bool _isBatchRunning;

    [ObservableProperty]
    private bool _batchDialogOpen;

    [ObservableProperty]
    private string _batchField = "authors";

    [ObservableProperty]
    private string _batchPageRange = "1-5";

    [ObservableProperty]
    private string _batchDirection = "front_to_back";

    public bool IsLibraryBusy => IsLoading || IsLoadingMore || IsBatchRunning;

    public event Action<EbookDto>? EditRequested;

    public LibraryViewModel(IEbookApiService api)
    {
        _api = api;
        ProgressLog.CollectionChanged += (_, _) => OnPropertyChanged(nameof(ShowBatchProgressPanel));
    }

    public bool ShowBatchProgressPanel =>
        IsBatchUpdateMode || IsBatchRunning || ProgressLog.Count > 0;

    partial void OnIsLoadingChanged(bool value) => OnPropertyChanged(nameof(IsLibraryBusy));

    partial void OnIsLoadingMoreChanged(bool value) => OnPropertyChanged(nameof(IsLibraryBusy));

    partial void OnIsBatchRunningChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLibraryBusy));
        OnPropertyChanged(nameof(ShowBatchProgressPanel));
    }

    partial void OnIsBatchUpdateModeChanged(bool value)
    {
        if (!value)
        {
            foreach (var row in Books)
                row.IsBatchSelected = false;
            BatchDialogOpen = false;
        }

        OnPropertyChanged(nameof(ShowBatchProgressPanel));
    }

    partial void OnBatchDialogOpenChanged(bool value) =>
        OnPropertyChanged(nameof(ShowBatchProgressPanel));

    [RelayCommand]
    private async Task LoadBooksAsync()
    {
        await ReloadFromServerAsync(appliedFromDraft: false);
    }

    [RelayCommand]
    private async Task ApplyFilterAsync()
    {
        await ReloadFromServerAsync(appliedFromDraft: true);
    }

    [RelayCommand]
    private Task LoadMoreAsync() => AppendNextPageAsync();

    /// <summary>Called from the view when the user scrolls near the end of the list.</summary>
    public Task TryLoadNextPageIfNeededAsync() => AppendNextPageAsync();

    /// <summary>Reloads library from API (awaitable), then rebinds the saved row so grid columns refresh cleanly.</summary>
    public async Task RefreshLibraryAfterSavedAsync(EbookDto? updatedFromPut)
    {
        await LoadBooksCommand.ExecuteAsync(null);
        if (updatedFromPut is not null)
            await RebindMatchingRowFromPutAsync(updatedFromPut);
    }

    private async Task RebindMatchingRowFromPutAsync(EbookDto updatedFromPut)
    {
        for (var i = 0; i < Books.Count; i++)
        {
            if (Books[i].Book.Id != updatedFromPut.Id)
                continue;
            var merged = CloneFromServerDto(updatedFromPut);
            merged.CoverUrl = await _api.DownloadCoverToTempAsync(updatedFromPut.Id);
            var wasSelected = Books[i].IsBatchSelected;
            Books.RemoveAt(i);
            Books.Insert(i, new LibraryBookRowViewModel(merged) { IsBatchSelected = wasSelected });
            if (SelectedBook?.Book.Id == updatedFromPut.Id)
                SelectedBook = Books[i];
            break;
        }
    }

    private static EbookDto CloneFromServerDto(EbookDto src) => new()
    {
        Id = src.Id,
        Title = src.Title,
        Isbn = src.Isbn,
        Authors = src.Authors.Count > 0 ? [..src.Authors] : [],
        Year = src.Year,
        Description = src.Description,
        Category = src.Category,
        Subcategory = src.Subcategory,
        Tags = src.Tags.Count > 0 ? [..src.Tags] : [],
        Publisher = src.Publisher,
        Edition = src.Edition,
        Language = src.Language,
        PageCount = src.PageCount,
        FileName = src.FileName,
        FilePath = src.FilePath,
        CoverImagePath = src.CoverImagePath,
        CoverImageMimeType = src.CoverImageMimeType,
        HasErrors = src.HasErrors,
        IsMetadataStored = src.IsMetadataStored,
        IsEmbededDataStored = src.IsEmbededDataStored,
    };

    private async Task AppendNextPageAsync()
    {
        if (!HasMorePages || IsLoadingMore || IsLoading)
            return;

        IsLoadingMore = true;
        StatusMessage = "Loading more…";
        try
        {
            var batch = await FetchPageAsync();
            await PopulateCoverUrlsAsync(batch);
            foreach (var b in batch)
                Books.Add(new LibraryBookRowViewModel(b));
            AdvancePaging(batch.Count);
            StatusMessage = $"{Books.Count} book(s) shown.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error loading more: {ex.Message}";
        }
        finally
        {
            IsLoadingMore = false;
        }
    }

    private async Task ReloadFromServerAsync(bool appliedFromDraft)
    {
        IsLoading = true;
        StatusMessage = "Loading…";
        try
        {
            if (appliedFromDraft)
            {
                _appliedPublisher = PublisherFilterText.Trim();
                _appliedCategory = CategoryFilterText.Trim();
                _appliedTagsFilter = TagsFilterText.Trim();
                _appliedTagsEmptyOnly = TagsEmptyOnly;
                _appliedErrorFilter = ErrorFilter;
            }

            Books.Clear();
            _nextSkip = 0;
            HasMorePages = true;

            var batch = await FetchPageAsync();
            await PopulateCoverUrlsAsync(batch);
            foreach (var b in batch)
                Books.Add(new LibraryBookRowViewModel(b));
            AdvancePaging(batch.Count);

            StatusMessage = $"{Books.Count} book(s) shown.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error loading books: {ex.Message}";
            HasMorePages = false;
        }
        finally
        {
            IsLoading = false;
        }
    }

    private async Task<List<EbookDto>> FetchPageAsync()
    {
        bool? hasErrors = _appliedErrorFilter switch
        {
            LibraryErrorFilter.All => null,
            LibraryErrorFilter.HasErrorsOnly => true,
            LibraryErrorFilter.NoErrorsOnly => false,
            _ => null,
        };

        string? publisher = string.IsNullOrWhiteSpace(_appliedPublisher) ? null : _appliedPublisher;
        string? category = string.IsNullOrWhiteSpace(_appliedCategory) ? null : _appliedCategory;
        string? tags = _appliedTagsEmptyOnly || string.IsNullOrWhiteSpace(_appliedTagsFilter)
            ? null
            : _appliedTagsFilter;
        bool? tagsEmpty = _appliedTagsEmptyOnly ? true : null;

        return await _api.GetAllAsync(
            skip: _nextSkip,
            limit: PageSize,
            publisherContains: publisher,
            categoryContains: category,
            tagsContains: tags,
            tagsEmpty: tagsEmpty,
            hasErrors: hasErrors);
    }

    private async Task PopulateCoverUrlsAsync(List<EbookDto> books)
    {
        var tasks = books.Select(async book =>
        {
            book.CoverUrl = await _api.DownloadCoverToTempAsync(book.Id);
        });
        await Task.WhenAll(tasks);
    }

    private void AdvancePaging(int returnedCount)
    {
        _nextSkip += returnedCount;
        HasMorePages = returnedCount >= PageSize;
    }

    [RelayCommand]
    private async Task DeleteBookAsync(LibraryBookRowViewModel row)
    {
        var book = row.Book;
        try
        {
            await _api.DeleteAsync(book.Id);
            Books.Remove(row);
            StatusMessage = $"Deleted: {book.Title}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Delete failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void EditBook(LibraryBookRowViewModel row)
    {
        EditRequested?.Invoke(row.Book);
    }

    [RelayCommand]
    private void OpenBook(EbookDto? book)
    {
        if (book is null)
        {
            StatusMessage = "No book selected.";
            return;
        }

        if (string.IsNullOrWhiteSpace(book.FilePath))
        {
            StatusMessage = "This book has no file path on disk.";
            return;
        }

        string path;
        try
        {
            path = Path.GetFullPath(book.FilePath.Trim());
        }
        catch (Exception ex)
        {
            StatusMessage = $"Invalid file path: {ex.Message}";
            return;
        }

        if (!File.Exists(path))
        {
            StatusMessage = $"File not found: {path}";
            return;
        }

        try
        {
            Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
            StatusMessage = $"Opened: {book.Title ?? book.FileName ?? path}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not open file: {ex.Message}";
        }
    }

    private bool AllVisibleSelected() =>
        Books.Count > 0 && Books.All(r => r.IsBatchSelected);

    [RelayCommand]
    private void ToggleSelectAllVisible()
    {
        var select = !AllVisibleSelected();
        foreach (var row in Books)
            row.IsBatchSelected = select;
    }

    [RelayCommand]
    private void OpenBatchReextractDialog()
    {
        if (!Books.Any(r => r.IsBatchSelected))
        {
            StatusMessage = "Select at least one book.";
            return;
        }

        BatchDialogOpen = true;
    }

    [RelayCommand]
    private void CancelBatchDialog()
    {
        BatchDialogOpen = false;
    }

    [RelayCommand]
    private async Task RunBatchReextractAsync()
    {
        var ids = Books.Where(r => r.IsBatchSelected).Select(r => r.Book.Id).ToList();
        if (ids.Count == 0)
        {
            StatusMessage = "Select at least one book.";
            return;
        }

        if (!PageRangeRe.IsMatch(BatchPageRange))
        {
            StatusMessage = "Page range must look like start-end (example: 5-10).";
            return;
        }

        BatchDialogOpen = false;
        ProgressLog.Clear();
        IsBatchRunning = true;
        StatusMessage = "Batch re-extract running…";

        try
        {
            var start = await _api.StartBatchReextractFieldAsync(
                new BatchReextractFieldJobRequestDto
                {
                    EbookIds = ids,
                    Field = BatchField.Trim(),
                    PageRange = BatchPageRange.Trim(),
                    Direction = BatchDirection.Trim(),
                });

            Application.Current.Dispatcher.Invoke(() => ProgressLog.Add($"Job started: {start.JobId}"));

            await foreach (var evt in _api.StreamBatchReextractFieldAsync(start.JobId))
            {
                Application.Current.Dispatcher.Invoke(() => ProgressLog.Add(evt.Message));
                if (evt.IsEndOfStream)
                    break;
            }

            Application.Current.Dispatcher.Invoke(() => ProgressLog.Add("--- Batch complete ---"));
            StatusMessage = "Batch re-extract complete.";
            await ReloadFromServerAsync(appliedFromDraft: false);
        }
        catch (Exception ex)
        {
            Application.Current.Dispatcher.Invoke(() => ProgressLog.Add($"Error: {ex.Message}"));
            StatusMessage = $"Batch failed: {ex.Message}";
        }
        finally
        {
            IsBatchRunning = false;
        }
    }
}
