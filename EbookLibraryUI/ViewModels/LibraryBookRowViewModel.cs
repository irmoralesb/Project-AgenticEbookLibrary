using CommunityToolkit.Mvvm.ComponentModel;
using EbookLibraryUI.Models;

namespace EbookLibraryUI.ViewModels;

/// <summary>One library grid row: ebook payload plus batch-selection checkbox state.</summary>
public partial class LibraryBookRowViewModel : ObservableObject
{
    public LibraryBookRowViewModel(EbookDto book) => Book = book;

    [ObservableProperty]
    private EbookDto _book;

    [ObservableProperty]
    private bool _isBatchSelected;
}
