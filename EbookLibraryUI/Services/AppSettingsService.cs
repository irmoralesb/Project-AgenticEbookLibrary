using System.Text.Json;
using System.IO;
using EbookLibraryUI.Models;

namespace EbookLibraryUI.Services;

public sealed class AppSettingsService : IAppSettingsService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
    };

    private readonly string _settingsDirectory;
    private readonly string _settingsFilePath;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private AppSettings _settings = new();

    public AppSettingsService()
    {
        _settingsDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "AgenticEbookLibrary");
        _settingsFilePath = Path.Combine(_settingsDirectory, "appsettings.json");
    }

    public string CoverImagePath => _settings.CoverImagePath;
    public bool SettingsFileExists => File.Exists(_settingsFilePath);
    public bool HasConfiguredCoverImagePath => !string.IsNullOrWhiteSpace(_settings.CoverImagePath);

    public event EventHandler<string>? CoverImagePathChanged;

    public async Task InitializeAsync()
    {
        await _gate.WaitAsync();
        try
        {
            _settings = await LoadSettingsAsync();
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task SaveCoverImagePathAsync(string coverImagePath)
    {
        var normalized = NormalizePath(coverImagePath);

        await _gate.WaitAsync();
        try
        {
            _settings.CoverImagePath = normalized;
            await SaveSettingsAsync(_settings);
        }
        finally
        {
            _gate.Release();
        }

        CoverImagePathChanged?.Invoke(this, normalized);
    }

    private async Task<AppSettings> LoadSettingsAsync()
    {
        try
        {
            if (!File.Exists(_settingsFilePath))
                return new AppSettings();

            await using var stream = File.OpenRead(_settingsFilePath);
            var settings = await JsonSerializer.DeserializeAsync<AppSettings>(stream, JsonOptions);
            settings ??= new AppSettings();
            settings.CoverImagePath = NormalizePath(settings.CoverImagePath);
            return settings;
        }
        catch
        {
            return new AppSettings();
        }
    }

    private async Task SaveSettingsAsync(AppSettings settings)
    {
        Directory.CreateDirectory(_settingsDirectory);

        var tempPath = _settingsFilePath + ".tmp";
        var json = JsonSerializer.Serialize(settings, JsonOptions);
        await File.WriteAllTextAsync(tempPath, json);

        if (File.Exists(_settingsFilePath))
        {
            File.Replace(tempPath, _settingsFilePath, null);
            return;
        }

        File.Move(tempPath, _settingsFilePath);
    }

    private static string NormalizePath(string? value) => value?.Trim() ?? string.Empty;
}
