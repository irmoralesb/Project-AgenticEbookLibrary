using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using EbookLibraryUI.Models;
using EbookLibraryUI.ViewModels;

namespace EbookLibraryUI.Views;

public partial class LibraryView : Page
{
    private ScrollViewer? _bookGridScrollViewer;

    public LibraryView()
    {
        InitializeComponent();
        Loaded += OnPageLoaded;
        Unloaded += OnPageUnloaded;
    }

    private void OnPageLoaded(object sender, RoutedEventArgs e)
    {
        Dispatcher.BeginInvoke(DispatcherPriority.Loaded, new Action(AttachPagingHooks));
    }

    private void OnPageUnloaded(object sender, RoutedEventArgs e)
    {
        BookGrid.LayoutUpdated -= BookGrid_OnLayoutUpdated;
        if (_bookGridScrollViewer is not null)
        {
            _bookGridScrollViewer.ScrollChanged -= ScrollViewer_OnScrollChanged;
            _bookGridScrollViewer = null;
        }
    }

    private void AttachPagingHooks()
    {
        BookGrid.LayoutUpdated += BookGrid_OnLayoutUpdated;
        _bookGridScrollViewer = FindScrollViewer(BookGrid);
        if (_bookGridScrollViewer is not null)
            _bookGridScrollViewer.ScrollChanged += ScrollViewer_OnScrollChanged;
    }

    private async void ScrollViewer_OnScrollChanged(object sender, ScrollChangedEventArgs e)
    {
        if (DataContext is not LibraryViewModel vm)
            return;
        if (!vm.HasMorePages || vm.IsLibraryBusy)
            return;
        if (sender is not ScrollViewer sv)
            return;
        if (sv.ScrollableHeight <= 0)
            return;

        const double threshold = 80;
        if (sv.VerticalOffset < sv.ScrollableHeight - threshold)
            return;

        await vm.TryLoadNextPageIfNeededAsync();
    }

    /// <summary>Fetches more rows when the grid is shorter than the viewport (nothing to scroll yet).</summary>
    private async void BookGrid_OnLayoutUpdated(object? sender, EventArgs e)
    {
        if (sender is not DataGrid dg)
            return;
        if (DataContext is not LibraryViewModel vm)
            return;
        if (!vm.HasMorePages || vm.IsLibraryBusy)
            return;

        var sv = FindScrollViewer(dg);
        if (sv == null || sv.ViewportHeight <= 0)
            return;

        // Enough content to scroll — user can reach the end via ScrollChanged.
        if (sv.ExtentHeight > sv.ViewportHeight + 48)
            return;

        await vm.TryLoadNextPageIfNeededAsync();
    }

    private void BookGrid_OnMouseDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is not DataGrid dg)
            return;

        if (FindAncestor<DataGridColumnHeader>(e.OriginalSource as DependencyObject) is not null)
            return;

        if (FindAncestor<DataGridRow>(e.OriginalSource as DependencyObject)?.Item is not EbookDto book)
            return;

        if (dg.DataContext is LibraryViewModel vm)
            vm.OpenBookCommand.Execute(book);
    }

    private static T? FindAncestor<T>(DependencyObject? current) where T : DependencyObject
    {
        while (current is not null)
        {
            if (current is T match)
                return match;
            current = VisualTreeHelper.GetParent(current);
        }

        return null;
    }

    private static ScrollViewer? FindScrollViewer(DependencyObject root)
    {
        if (root is ScrollViewer sv)
            return sv;

        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            var found = FindScrollViewer(child);
            if (found is not null)
                return found;
        }

        return null;
    }
}
