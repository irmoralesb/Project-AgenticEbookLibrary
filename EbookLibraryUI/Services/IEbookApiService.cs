using EbookLibraryUI.Models;

namespace EbookLibraryUI.Services;

public interface IEbookApiService
{
    Task<List<EbookDto>> GetAllAsync(int skip = 0, int limit = 100, CancellationToken ct = default);
    Task<EbookDto?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<EbookDto?> UpdateAsync(Guid id, EbookUpdateDto dto, CancellationToken ct = default);
    Task DeleteAsync(Guid id, CancellationToken ct = default);
    Task<IngestStartResponse> StartIngestAsync(IngestRequestDto request, CancellationToken ct = default);
    IAsyncEnumerable<IngestProgressEvent> StreamIngestAsync(string jobId, CancellationToken ct);
    Task<string?> PickFolderAsync(CancellationToken ct = default);
}
