using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;

namespace EbookLibraryUI.ViewModels;

public partial class LibraryViewModel : ObservableObject
{
    private readonly IEbookApiService _api;

    public ObservableCollection<EbookDto> Books { get; } = [];

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string _statusMessage = string.Empty;

    [ObservableProperty]
    private EbookDto? _selectedBook;

    [ObservableProperty]
    private string _coverImageBasePath = EbookDto.CoverImageRootPath;

    public event Action<EbookDto>? EditRequested;

    public LibraryViewModel(IEbookApiService api)
    {
        _api = api;
    }

    [RelayCommand]
    private async Task LoadBooksAsync()
    {
        IsLoading = true;
        StatusMessage = "Loading…";
        try
        {
            var books = await _api.GetAllAsync();
            Books.Clear();
            foreach (var b in books)
                Books.Add(b);
            StatusMessage = $"{Books.Count} book(s) loaded.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error loading books: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task ApplyCoverImagePathAsync()
    {
        var normalizedPath = string.IsNullOrWhiteSpace(CoverImageBasePath)
            ? string.Empty
            : CoverImageBasePath.Trim().TrimEnd('/');

        if (string.IsNullOrWhiteSpace(normalizedPath))
        {
            StatusMessage = "Image path cannot be empty.";
            return;
        }

        EbookDto.CoverImageRootPath = normalizedPath;
        CoverImageBasePath = normalizedPath;
        StatusMessage = $"Image path updated: {normalizedPath}";

        await LoadBooksAsync();
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
}
