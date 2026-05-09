using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;
using System.Text.RegularExpressions;
using System.Text.Json;

namespace EbookLibraryUI.ViewModels;

public partial class EbookDetailViewModel : ObservableObject
{
    private readonly IEbookApiService _api;
    private Guid _ebookId;

    [ObservableProperty] private string? _title;
    [ObservableProperty] private string? _isbn;
    [ObservableProperty] private string? _authorsText;
    [ObservableProperty] private string? _year;
    [ObservableProperty] private string? _description;
    [ObservableProperty] private string? _category;
    [ObservableProperty] private string? _subcategory;
    [ObservableProperty] private string? _tagsText;
    [ObservableProperty] private string? _publisher;
    [ObservableProperty] private string? _edition;
    [ObservableProperty] private string? _language;
    [ObservableProperty] private string? _pageCount;
    [ObservableProperty] private bool _hasErrors;
    [ObservableProperty] private string? _coverUrl;
    [ObservableProperty] private string _statusMessage = string.Empty;
    [ObservableProperty] private bool _isFindAgainDialogOpen;
    [ObservableProperty] private bool _isReextracting;
    [ObservableProperty] private string _findAgainField = "authors";
    [ObservableProperty] private string _findAgainPageRange = "1-5";
    [ObservableProperty] private string _findAgainDirection = "front_to_back";

    /// <summary>Returned <see cref="EbookDto"/> is the PUT response (may be null). Handlers run on the calling sync context.</summary>
    public event Func<EbookDto?, Task>? SaveCompletedAsync;
    public event Action? CancelRequested;

    public EbookDetailViewModel(IEbookApiService api)
    {
        _api = api;
    }

    public void LoadFrom(EbookDto dto)
    {
        _ebookId = dto.Id;
        Title = dto.Title;
        Isbn = dto.Isbn;
        AuthorsText = dto.Authors.Count > 0 ? string.Join(", ", dto.Authors) : null;
        Year = dto.Year?.ToString();
        Description = dto.Description;
        Category = dto.Category;
        Subcategory = dto.Subcategory;
        TagsText = dto.Tags.Count > 0 ? string.Join(", ", dto.Tags) : null;
        Publisher = dto.Publisher;
        Edition = dto.Edition;
        Language = dto.Language;
        PageCount = dto.PageCount?.ToString();
        HasErrors = dto.HasErrors;
        CoverUrl = dto.CoverUrl;
        StatusMessage = string.Empty;
    }

    [RelayCommand]
    private async Task SaveAsync()
    {
        StatusMessage = "Saving…";
        try
        {
            var dto = BuildUpdateDto();
            var updated = await _api.UpdateAsync(_ebookId, dto);
            StatusMessage = "Saved successfully.";
            await InvokeSaveCompletedAsync(updated);
        }
        catch (Exception ex)
        {
            StatusMessage = $"Save failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void Cancel()
    {
        CancelRequested?.Invoke();
    }

    private async Task InvokeSaveCompletedAsync(EbookDto? dto)
    {
        if (SaveCompletedAsync is null)
            return;
        foreach (var subscriber in SaveCompletedAsync.GetInvocationList())
        {
            if (subscriber is not Func<EbookDto?, Task> handler)
                continue;
            await handler(dto).ConfigureAwait(true);
        }
    }

    [RelayCommand]
    private void OpenFindAgain(string field)
    {
        FindAgainField = string.IsNullOrWhiteSpace(field) ? "authors" : field;
        FindAgainPageRange = "1-5";
        FindAgainDirection = "front_to_back";
        IsFindAgainDialogOpen = true;
        StatusMessage = string.Empty;
    }

    [RelayCommand]
    private void CloseFindAgain()
    {
        if (IsReextracting)
            return;
        IsFindAgainDialogOpen = false;
    }

    [RelayCommand]
    private async Task RunFindAgainAsync()
    {
        if (!Regex.IsMatch(FindAgainPageRange ?? string.Empty, @"^\s*\d+\s*-\s*\d+\s*$"))
        {
            StatusMessage = "Find again failed: page range must follow start-end (example: 5-10).";
            return;
        }

        IsReextracting = true;
        StatusMessage = "Finding value...";
        try
        {
            var result = await _api.ReextractFieldAsync(_ebookId, new ReextractFieldRequestDto
            {
                Field = FindAgainField,
                PageRange = FindAgainPageRange ?? "1-5",
                Direction = FindAgainDirection,
            });
            ApplyReextractResult(result);
            StatusMessage = string.IsNullOrWhiteSpace(result.Message) ? "Find again completed." : result.Message;
            IsFindAgainDialogOpen = false;
        }
        catch (Exception ex)
        {
            StatusMessage = $"Find again failed: {ex.Message}";
        }
        finally
        {
            IsReextracting = false;
        }
    }

    private EbookUpdateDto BuildUpdateDto()
    {
        var authors = AuthorsText?
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .ToList();

        var tags = TagsText?
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .ToList();

        return new EbookUpdateDto
        {
            Title = Title,
            Isbn = Isbn,
            Authors = authors?.Count > 0 ? authors : null,
            Year = int.TryParse(Year, out var y) ? y : null,
            Description = Description,
            Category = Category,
            Subcategory = Subcategory,
            Tags = tags ?? [],
            Publisher = Publisher,
            Edition = Edition,
            Language = Language,
            PageCount = int.TryParse(PageCount, out var pc) ? pc : null,
            HasErrors = HasErrors,
        };
    }

    private void ApplyReextractResult(ReextractFieldResponseDto result)
    {
        switch (result.Field)
        {
            case "authors":
                AuthorsText = ParseAuthorsValue(result.Value);
                break;
            case "isbn":
                Isbn = ParseSingleValue(result.Value);
                break;
            case "publisher":
                Publisher = ParseSingleValue(result.Value);
                break;
            case "year":
                Year = ParseYearValue(result.Value);
                break;
        }
    }

    private static string? ParseYearValue(object? value)
    {
        if (value is null)
            return null;
        if (value is int yearInt)
            return yearInt.ToString();
        if (value is JsonElement json)
        {
            if (json.ValueKind == JsonValueKind.Number && json.TryGetInt32(out var y))
                return y.ToString();
            if (json.ValueKind == JsonValueKind.String)
                return json.GetString();
            return json.ToString();
        }
        if (value is string s)
            return s;
        return value.ToString();
    }

    private static string? ParseSingleValue(object? value)
    {
        if (value is null)
            return null;
        if (value is string stringValue)
            return stringValue;
        if (value is JsonElement json && json.ValueKind == JsonValueKind.String)
            return json.GetString();
        return value.ToString();
    }

    private static string? ParseAuthorsValue(object? value)
    {
        if (value is null)
            return null;
        if (value is JsonElement json && json.ValueKind == JsonValueKind.Array)
        {
            var authors = new List<string>();
            foreach (var item in json.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(item.GetString()))
                    authors.Add(item.GetString()!);
            }
            return authors.Count > 0 ? string.Join(", ", authors) : null;
        }
        if (value is string single)
            return single;
        return value.ToString();
    }

    [RelayCommand]
    private async Task AddPublisherToCatalogAsync()
    {
        StatusMessage = "Adding to catalog…";
        try
        {
            var result = await _api.AddKnownPublisherAsync(Publisher ?? string.Empty);
            StatusMessage = result.Message;
        }
        catch (Exception ex)
        {
            StatusMessage = $"Could not add publisher: {ex.Message}";
        }
    }
}
