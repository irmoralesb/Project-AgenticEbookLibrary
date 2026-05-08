using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EbookLibraryUI.Models;
using EbookLibraryUI.Services;

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

    public event Action? SaveCompleted;
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
            await _api.UpdateAsync(_ebookId, dto);
            StatusMessage = "Saved successfully.";
            SaveCompleted?.Invoke();
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
}
