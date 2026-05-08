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
            await using var dst = File.Create(localPath);
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

    public async IAsyncEnumerable<IngestProgressEvent> StreamIngestAsync(
        string jobId,
        [EnumeratorCancellation] CancellationToken ct)
    {
        using var response = await _http.GetAsync(
            $"api/ingest/stream?job_id={jobId}",
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

            // SSE lines start with "data: "
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

    private sealed class FolderPickerResponse
    {
        public string? Path { get; set; }
    }
}
