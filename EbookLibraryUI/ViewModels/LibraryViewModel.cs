using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
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
