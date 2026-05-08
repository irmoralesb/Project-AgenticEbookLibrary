using System.Windows;
using EbookLibraryUI.Services;
using EbookLibraryUI.ViewModels;
using EbookLibraryUI.Views;
using Microsoft.Extensions.DependencyInjection;

namespace EbookLibraryUI;

public partial class App : Application
{
    public static IServiceProvider Services { get; private set; } = null!;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        var services = new ServiceCollection();
        ConfigureServices(services);
        Services = services.BuildServiceProvider();

        var window = Services.GetRequiredService<MainWindow>();
        window.Show();
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        services.AddHttpClient<IEbookApiService, EbookApiService>(client =>
        {
            client.BaseAddress = new Uri("http://localhost:8000/");
            client.Timeout = TimeSpan.FromMinutes(10);
        });

        services.AddSingleton<IFolderPickerService, WindowsFolderPickerService>();

        services.AddTransient<LibraryViewModel>();
        services.AddTransient<EbookDetailViewModel>();
        services.AddTransient<IngestViewModel>();
        services.AddTransient<SettingsViewModel>();

        services.AddSingleton<MainWindow>();
    }
}
