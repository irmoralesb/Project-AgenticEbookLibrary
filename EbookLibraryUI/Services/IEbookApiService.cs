using EbookLibraryUI.Models;

namespace EbookLibraryUI.Services;

public interface IEbookApiService
{
    Task<List<EbookDto>> GetAllAsync(
        int skip = 0,
        int limit = 15,
        string? publisherContains = null,
        string? categoryContains = null,
        bool? hasErrors = null,
        CancellationToken ct = default);

    Task<EbookDto?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<string?> DownloadCoverToTempAsync(Guid id, CancellationToken ct = default);
    Task<EbookDto?> UpdateAsync(Guid id, EbookUpdateDto dto, CancellationToken ct = default);
    Task<ReextractFieldResponseDto> ReextractFieldAsync(Guid id, ReextractFieldRequestDto dto, CancellationToken ct = default);
    Task DeleteAsync(Guid id, CancellationToken ct = default);
    Task<IngestStartResponse> StartIngestAsync(IngestRequestDto request, CancellationToken ct = default);
    IAsyncEnumerable<IngestProgressEvent> StreamIngestAsync(string jobId, CancellationToken ct);
    Task<string?> PickFolderAsync(CancellationToken ct = default);

    /// <summary>Adds a publisher name to the regex catalog. Duplicate names are treated as success.</summary>
    Task<KnownPublisherCatalogResult> AddKnownPublisherAsync(string name, CancellationToken ct = default);
}
