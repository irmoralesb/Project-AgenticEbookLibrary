using System.Text.Json.Serialization;

namespace EbookLibraryUI.Models;

/// <summary>POST /api/publishers — JSON property must be <c>name</c> (matches FastAPI/Pydantic).</summary>
public sealed record KnownPublisherCreateDto([property: JsonPropertyName("name")] string Name);

public sealed class KnownPublisherResponseDto
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; }
}

public enum KnownPublisherCatalogResultKind
{
    Created,
    AlreadyExists,
    ValidationError,
}

public sealed record KnownPublisherCatalogResult(
    KnownPublisherCatalogResultKind Kind,
    string Message);
