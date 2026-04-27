using System.Text.Json.Serialization;

namespace EbookLibraryUI.Models;

/// <summary>Mirrors the EbookResponse schema returned by the FastAPI backend.</summary>
public class EbookDto
{
    /// <summary>Base URL used for static cover image links (set from configured API base address).</summary>
    public static string CoverBaseUrl { get; set; } = "http://localhost:8000";

    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("title")]
    public string? Title { get; set; }

    [JsonPropertyName("isbn")]
    public string? Isbn { get; set; }

    [JsonPropertyName("authors")]
    public List<string> Authors { get; set; } = [];

    [JsonPropertyName("year")]
    public int? Year { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("category")]
    public string? Category { get; set; }

    [JsonPropertyName("subcategory")]
    public string? Subcategory { get; set; }

    [JsonPropertyName("publisher")]
    public string? Publisher { get; set; }

    [JsonPropertyName("edition")]
    public string? Edition { get; set; }

    [JsonPropertyName("language")]
    public string? Language { get; set; }

    [JsonPropertyName("page_count")]
    public int? PageCount { get; set; }

    [JsonPropertyName("file_name")]
    public string? FileName { get; set; }

    [JsonPropertyName("cover_image_path")]
    public string? CoverImagePath { get; set; }

    [JsonPropertyName("cover_image_mime_type")]
    public string? CoverImageMimeType { get; set; }

    [JsonPropertyName("has_errors")]
    public bool HasErrors { get; set; }

    [JsonPropertyName("is_metadata_stored")]
    public bool IsMetadataStored { get; set; }

    [JsonPropertyName("is_embeded_data_stored")]
    public bool IsEmbededDataStored { get; set; }

    /// <summary>Comma-separated authors string for display in table cells.</summary>
    public string AuthorsDisplay => Authors.Count > 0 ? string.Join(", ", Authors) : "—";

    /// <summary>Full URL to load the cover image from the FastAPI static files mount.</summary>
    public string? CoverUrl =>
        FileName is not null
            ? $"{CoverBaseUrl.TrimEnd('/')}/covers/{System.IO.Path.GetFileNameWithoutExtension(FileName)}{CoverExtension}"
            : null;

    private string CoverExtension =>
        CoverImageMimeType switch
        {
            "image/png" => ".png",
            "image/jpeg" => ".jpg",
            "image/gif" => ".gif",
            _ => string.Empty,
        };
}
