using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace EbookLibraryUI.Views;

public partial class EbookDetailView : Page
{
    public EbookDetailView()
    {
        InitializeComponent();
    }

    private void CoverBorder_OnMouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (CoverImage.Source is not BitmapSource bitmap)
            return;

        var image = new Image
        {
            Source = bitmap,
            Stretch = Stretch.None,
            HorizontalAlignment = HorizontalAlignment.Left,
            VerticalAlignment = VerticalAlignment.Top,
            SnapsToDevicePixels = true,
            UseLayoutRounding = true,
        };

        var scroll = new ScrollViewer
        {
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Content = image,
            Background = Brushes.Black,
        };

        var owner = Window.GetWindow(this);
        var popup = new Window
        {
            Title = "Cover Preview",
            Content = scroll,
            Width = Math.Min(bitmap.PixelWidth + 60, 1400),
            Height = Math.Min(bitmap.PixelHeight + 100, 1000),
            MinWidth = 420,
            MinHeight = 320,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = Brushes.Black,
            Owner = owner,
        };

        popup.ShowDialog();
    }
}
