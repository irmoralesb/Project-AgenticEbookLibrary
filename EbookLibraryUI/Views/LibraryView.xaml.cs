using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using EbookLibraryUI.Models;
using EbookLibraryUI.ViewModels;

namespace EbookLibraryUI.Views;

public partial class LibraryView : Page
{
    public LibraryView()
    {
        InitializeComponent();
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
}
