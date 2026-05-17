using System.Text.Json.Serialization;

namespace EbookLibraryUI.Models;

public class BatchReextractFieldJobRequestDto
{
    [JsonPropertyName("ebook_ids")]
    public List<Guid> EbookIds { get; set; } = [];

    [JsonPropertyName("field")]
    public string Field { get; set; } = "authors";

    [JsonPropertyName("page_range")]
    public string PageRange { get; set; } = "1-5";

    [JsonPropertyName("direction")]
    public string Direction { get; set; } = "front_to_back";
}
