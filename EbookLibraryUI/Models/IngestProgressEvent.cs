namespace EbookLibraryUI.Models;

/// <summary>A single progress message received from the SSE ingestion stream.</summary>
public class IngestProgressEvent
{
    public string Message { get; init; } = string.Empty;

    /// <summary>True when the server sends the terminal "stream-end" sentinel.</summary>
    public bool IsEndOfStream => Message == "stream-end";
}
