using System.Net.Http;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.IO;
using EbookLibraryUI.Models;

namespace EbookLibraryUI.Services;

public class EbookApiService : IEbookApiService
{
    private readonly HttpClient _http;
    private readonly string _coverCacheDir;

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public EbookApiService(HttpClient http)
    {
        _http = http;
        _coverCacheDir = Path.Combine(Path.GetTempPath(), "AgenticEbookLibrary", "covers");
        Directory.CreateDirectory(_coverCacheDir);
    }

    public async Task<List<EbookDto>> GetAllAsync(
        int skip = 0,
        int limit = 15,
        string? publisherContains = null,
        string? categoryContains = null,
        string? tagsContains = null,
        bool? tagsEmpty = null,
        bool? hasErrors = null,
        CancellationToken ct = default)
    {
        var qs = new List<string>
        {
            $"skip={skip}",
            $"limit={limit}",
        };
        if (!string.IsNullOrWhiteSpace(publisherContains))
            qs.Add($"publisher={Uri.EscapeDataString(publisherContains.Trim())}");
        if (!string.IsNullOrWhiteSpace(categoryContains))
            qs.Add($"category={Uri.EscapeDataString(categoryContains.Trim())}");
        if (tagsEmpty == true)
            qs.Add("tags_empty=true");
        else if (!string.IsNullOrWhiteSpace(tagsContains))
            qs.Add($"tags={Uri.EscapeDataString(tagsContains.Trim())}");
        if (hasErrors.HasValue)
            qs.Add($"has_errors={(hasErrors.Value ? "true" : "false")}");

        var url = $"api/ebooks?{string.Join("&", qs)}";
        var result = await _http.GetFromJsonAsync<List<EbookDto>>(url, _jsonOptions, ct);
        return result ?? [];
    }

    public async Task<EbookDto?> GetByIdAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            return await _http.GetFromJsonAsync<EbookDto>($"api/ebooks/{id}", _jsonOptions, ct);
        }
        catch (HttpRequestException ex) when (ex.StatusCode == System.Net.HttpStatusCode.NotFound)
        {
            return null;
        }
    }

    public async Task<string?> DownloadCoverToTempAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            var cachedPattern = $"{id}.*";
            var cachedFile = Directory
                .EnumerateFiles(_coverCacheDir, cachedPattern, SearchOption.TopDirectoryOnly)
                .FirstOrDefault();
            if (!string.IsNullOrWhiteSpace(cachedFile) && File.Exists(cachedFile))
                return new Uri(cachedFile).AbsoluteUri;

            using var response = await _http.GetAsync($"api/ebooks/{id}/cover", ct);
            if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                return null;
            response.EnsureSuccessStatusCode();

            var ext = response.Content.Headers.ContentType?.MediaType?.ToLowerInvariant() switch
            {
                "image/png" => ".png",
                "image/jpeg" => ".jpg",
                "image/jpg" => ".jpg",
                "image/webp" => ".webp",
                "image/gif" => ".gif",
                _ => ".img",
            };

            var localPath = Path.Combine(_coverCacheDir, $"{id}{ext}");
            await using var src = await response.Content.ReadAsStreamAsync(ct);
            await using var dst = new FileStream(
                localPath,
                FileMode.CreateNew,
                FileAccess.Write,
                FileShare.Read);
            await src.CopyToAsync(dst, ct);

            return new Uri(localPath).AbsoluteUri;
        }
        catch (HttpRequestException ex) when (ex.StatusCode == System.Net.HttpStatusCode.NotFound)
        {
            return null;
        }
    }

    public async Task<EbookDto?> UpdateAsync(Guid id, EbookUpdateDto dto, CancellationToken ct = default)
    {
        var response = await _http.PutAsJsonAsync($"api/ebooks/{id}", dto, _jsonOptions, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<EbookDto>(_jsonOptions, ct);
    }

    public async Task<ReextractFieldResponseDto> ReextractFieldAsync(
        Guid id,
        ReextractFieldRequestDto dto,
        CancellationToken ct = default)
    {
        var response = await _http.PostAsJsonAsync($"api/ebooks/{id}/reextract-field", dto, _jsonOptions, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<ReextractFieldResponseDto>(_jsonOptions, ct)
            ?? throw new InvalidOperationException("Empty response from reextract-field.");
    }

    public async Task DeleteAsync(Guid id, CancellationToken ct = default)
    {
        var response = await _http.DeleteAsync($"api/ebooks/{id}", ct);
        response.EnsureSuccessStatusCode();
    }

    public async Task<IngestStartResponse> StartIngestAsync(IngestRequestDto request, CancellationToken ct = default)
    {
        var response = await _http.PostAsJsonAsync("api/ingest/start", request, _jsonOptions, ct);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<IngestStartResponse>(_jsonOptions, ct);
        return result ?? throw new InvalidOperationException("Empty response from ingest/start.");
    }

    public async Task<IngestStartResponse> StartBatchReextractFieldAsync(
        BatchReextractFieldJobRequestDto request,
        CancellationToken ct = default)
    {
        var response = await _http.PostAsJsonAsync(
            "api/ebooks/batch-reextract-field/start",
            request,
            _jsonOptions,
            ct);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<IngestStartResponse>(_jsonOptions, ct);
        return result ?? throw new InvalidOperationException("Empty response from batch-reextract-field/start.");
    }

    public async IAsyncEnumerable<IngestProgressEvent> StreamIngestAsync(
        string jobId,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        await foreach (var evt in StreamSseProgressAsync("api/ingest/stream", jobId, ct).ConfigureAwait(false))
            yield return evt;
    }

    public async IAsyncEnumerable<IngestProgressEvent> StreamBatchReextractFieldAsync(
        string jobId,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        await foreach (
            var evt in StreamSseProgressAsync("api/ebooks/batch-reextract-field/stream", jobId, ct)
                .ConfigureAwait(false))
            yield return evt;
    }

    private async IAsyncEnumerable<IngestProgressEvent> StreamSseProgressAsync(
        string streamPathWithoutQuery,
        string jobId,
        [EnumeratorCancellation] CancellationToken ct)
    {
        var url =
            $"{streamPathWithoutQuery}?job_id={Uri.EscapeDataString(jobId)}";
        using var response = await _http.GetAsync(
            url,
            HttpCompletionOption.ResponseHeadersRead,
            ct
        );
        response.EnsureSuccessStatusCode();

        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var reader = new System.IO.StreamReader(stream);

        while (!ct.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(ct);
            if (line is null)
                break;

            if (!line.StartsWith("data:", StringComparison.Ordinal))
                continue;

            var json = line["data:".Length..].Trim();
            if (string.IsNullOrEmpty(json))
                continue;

            SseMessage? sseMsg;
            try
            {
                sseMsg = JsonSerializer.Deserialize<SseMessage>(json, _jsonOptions);
            }
            catch (JsonException)
            {
                continue;
            }

            if (sseMsg?.Message is not null)
            {
                yield return new IngestProgressEvent { Message = sseMsg.Message };

                if (sseMsg.Message == "stream-end")
                    yield break;
            }
            else if (sseMsg?.Error is not null)
            {
                yield return new IngestProgressEvent { Message = $"ERROR: {sseMsg.Error}" };
                yield break;
            }
        }
    }

    public async Task<string?> PickFolderAsync(CancellationToken ct = default)
    {
        try
        {
            var result = await _http.GetFromJsonAsync<FolderPickerResponse>("api/system/folder-picker", _jsonOptions, ct);
            return result?.Path;
        }
        catch
        {
            return null;
        }
    }

    public async Task<KnownPublisherCatalogResult> AddKnownPublisherAsync(
        string name,
        CancellationToken ct = default)
    {
        var trimmed = name.Trim();
        if (string.IsNullOrEmpty(trimmed))
        {
            return new KnownPublisherCatalogResult(
                KnownPublisherCatalogResultKind.ValidationError,
                "Enter a publisher name first.");
        }

        using var response = await _http.PostAsJsonAsync(
            "api/publishers",
            new KnownPublisherCreateDto(trimmed),
            _jsonOptions,
            ct);

        if (response.StatusCode == System.Net.HttpStatusCode.Conflict)
        {
            return new KnownPublisherCatalogResult(
                KnownPublisherCatalogResultKind.AlreadyExists,
                "That publisher is already in the catalog.");
        }

        response.EnsureSuccessStatusCode();
        var row = await response.Content.ReadFromJsonAsync<KnownPublisherResponseDto>(_jsonOptions, ct);
        var displayName = row?.Name ?? trimmed;
        return new KnownPublisherCatalogResult(
            KnownPublisherCatalogResultKind.Created,
            $"Added \"{displayName}\" to the publisher catalog.");
    }

    private sealed class FolderPickerResponse
    {
        public string? Path { get; set; }
    }
}
