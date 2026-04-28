using System.Windows;
using EbookLibraryUI.Models;
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

        var appSettings = Services.GetRequiredService<IAppSettingsService>();
        appSettings.InitializeAsync().GetAwaiter().GetResult();
        EbookDto.CoverImageRootPath = appSettings.CoverImagePath;

        var window = Services.GetRequiredService<MainWindow>();
        window.Show();
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        // HTTP client pointed at the local FastAPI server.
        services.AddHttpClient<IEbookApiService, EbookApiService>(client =>
        {
            client.BaseAddress = new Uri("http://localhost:8000/");
            client.Timeout = TimeSpan.FromMinutes(10); // ingestion can be slow
        });

        services.AddSingleton<IFolderPickerService, WindowsFolderPickerService>();
        services.AddSingleton<IAppSettingsService, AppSettingsService>();

        // ViewModels
        services.AddTransient<LibraryViewModel>();
        services.AddTransient<EbookDetailViewModel>();
        services.AddTransient<IngestViewModel>();
        services.AddTransient<SettingsViewModel>();

        // Views
        services.AddSingleton<MainWindow>();
    }
}

