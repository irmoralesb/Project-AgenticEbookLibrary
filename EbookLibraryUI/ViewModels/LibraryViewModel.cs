using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
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
    private const int PageSize = 15;

    private readonly IEbookApiService _api;

    private int _nextSkip;
    private string _appliedPublisher = string.Empty;
    private string _appliedCategory = string.Empty;
    private LibraryErrorFilter _appliedErrorFilter = LibraryErrorFilter.All;

    public ObservableCollection<EbookDto> Books { get; } = [];

    [ObservableProperty]
    private string _publisherFilterText = string.Empty;

    [ObservableProperty]
    private string _categoryFilterText = string.Empty;

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
    private EbookDto? _selectedBook;

    public bool IsLibraryBusy => IsLoading || IsLoadingMore;

    public event Action<EbookDto>? EditRequested;

    public LibraryViewModel(IEbookApiService api)
    {
        _api = api;
    }

    partial void OnIsLoadingChanged(bool value) => OnPropertyChanged(nameof(IsLibraryBusy));

    partial void OnIsLoadingMoreChanged(bool value) => OnPropertyChanged(nameof(IsLibraryBusy));

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
            if (Books[i].Id != updatedFromPut.Id)
                continue;
            var merged = CloneFromServerDto(updatedFromPut);
            merged.CoverUrl = await _api.DownloadCoverToTempAsync(updatedFromPut.Id);
            Books.RemoveAt(i);
            Books.Insert(i, merged);
            if (SelectedBook?.Id == updatedFromPut.Id)
                SelectedBook = merged;
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
                Books.Add(b);
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
                _appliedErrorFilter = ErrorFilter;
            }

            Books.Clear();
            _nextSkip = 0;
            HasMorePages = true;

            var batch = await FetchPageAsync();
            await PopulateCoverUrlsAsync(batch);
            foreach (var b in batch)
                Books.Add(b);
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

        return await _api.GetAllAsync(
            skip: _nextSkip,
            limit: PageSize,
            publisherContains: publisher,
            categoryContains: category,
            hasErrors: hasErrors);
    }

    private async Task PopulateCoverUrlsAsync(IEnumerable<EbookDto> books)
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
    private async Task DeleteBookAsync(EbookDto book)
    {
        try
        {
            await _api.DeleteAsync(book.Id);
            Books.Remove(book);
            StatusMessage = $"Deleted: {book.Title}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Delete failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void EditBook(EbookDto book)
    {
        EditRequested?.Invoke(book);
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
}
