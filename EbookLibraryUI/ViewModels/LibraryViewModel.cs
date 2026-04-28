using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;

namespace EbookLibraryUI.ViewModels;

public partial class LibraryViewModel : ObservableObject
{
    private readonly IEbookApiService _api;
    private readonly IAppSettingsService _appSettings;

    public ObservableCollection<EbookDto> Books { get; } = [];

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string _statusMessage = string.Empty;

    [ObservableProperty]
    private EbookDto? _selectedBook;

    [ObservableProperty]
    private string _coverImagePath = string.Empty;

    public event Action<EbookDto>? EditRequested;

    public LibraryViewModel(IEbookApiService api, IAppSettingsService appSettings)
    {
        _api = api;
        _appSettings = appSettings;
        CoverImagePath = _appSettings.CoverImagePath;
        _appSettings.CoverImagePathChanged += OnCoverImagePathChanged;
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

    private void OnCoverImagePathChanged(object? sender, string value)
    {
        CoverImagePath = value;
        EbookDto.CoverImageRootPath = value;
        _ = LoadBooksAsync();
    }
}
