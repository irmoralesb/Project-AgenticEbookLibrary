using System.Text.Json.Serialization;

namespace EbookLibraryUI.Models;

public class ReextractFieldRequestDto
{
    [JsonPropertyName("field")]
    public string Field { get; set; } = "authors";

    [JsonPropertyName("page_range")]
    public string PageRange { get; set; } = "1-5";

    [JsonPropertyName("direction")]
    public string Direction { get; set; } = "front_to_back";
}

public class ReextractFieldResponseDto
{
    [JsonPropertyName("field")]
    public string Field { get; set; } = string.Empty;

    [JsonPropertyName("value")]
    public object? Value { get; set; }

    [JsonPropertyName("used_start_page")]
    public int UsedStartPage { get; set; }

    [JsonPropertyName("used_end_page")]
    public int UsedEndPage { get; set; }

    [JsonPropertyName("direction")]
    public string Direction { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;
}
