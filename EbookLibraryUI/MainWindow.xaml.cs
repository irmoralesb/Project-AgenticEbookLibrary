using System.Windows;
using EbookLibraryUI.Models;
using EbookLibraryUI.ViewModels;
using EbookLibraryUI.Views;
using Microsoft.Extensions.DependencyInjection;

namespace EbookLibraryUI;

/// <summary>
/// Shell window — wires navigation and DI-created views.
/// Only navigation plumbing lives here; no business logic.
/// </summary>
public partial class MainWindow : Window
{
    private LibraryView? _libraryView;
    private IngestView? _ingestView;
    private EbookDetailView? _detailView;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        BuildViews();
        ShowLibraryView(refresh: true);
    }

    private void BuildViews()
    {
        var libraryVm = App.Services.GetRequiredService<LibraryViewModel>();
        libraryVm.EditRequested += ShowDetailView;
        _libraryView = new LibraryView { DataContext = libraryVm };

        var ingestVm = App.Services.GetRequiredService<IngestViewModel>();
        _ingestView = new IngestView { DataContext = ingestVm };

        var detailVm = App.Services.GetRequiredService<EbookDetailViewModel>();
        detailVm.SaveCompleted  += () => ShowLibraryView(refresh: true);
        detailVm.CancelRequested += () => ShowLibraryView(refresh: false);
        _detailView = new EbookDetailView { DataContext = detailVm };
    }

    private void NavLibrary_Click(object sender, RoutedEventArgs e) =>
        ShowLibraryView(refresh: false);

    private void NavIngest_Click(object sender, RoutedEventArgs e) =>
        PageFrame.Navigate(_ingestView);

    private void ShowLibraryView(bool refresh)
    {
        PageFrame.Navigate(_libraryView);
        if (refresh && _libraryView?.DataContext is LibraryViewModel vm)
            _ = vm.LoadBooksCommand.ExecuteAsync(null);
    }

    private void ShowDetailView(EbookDto book)
    {
        if (_detailView?.DataContext is EbookDetailViewModel vm)
            vm.LoadFrom(book);
        PageFrame.Navigate(_detailView);
    }
}
