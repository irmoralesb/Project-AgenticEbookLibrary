using System.Collections.Specialized;
using System.Windows.Controls;
using EbookLibraryUI.ViewModels;

namespace EbookLibraryUI.Views;

public partial class IngestView : Page
{
    public IngestView()
    {
        InitializeComponent();
        DataContextChanged += OnDataContextChanged;
    }

    private void OnDataContextChanged(object sender, System.Windows.DependencyPropertyChangedEventArgs e)
    {
        if (e.NewValue is IngestViewModel vm)
            vm.ProgressLog.CollectionChanged += ScrollToBottom;
    }

    private void ScrollToBottom(object? sender, NotifyCollectionChangedEventArgs e)
    {
        ProgressScroller.ScrollToBottom();
    }
}
