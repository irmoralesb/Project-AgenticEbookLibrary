import type { EbookDto } from '../models/EbookDto';
import type { EbookUpdateDto } from '../models/EbookUpdateDto';
import type {
  IngestRequestDto,
  IngestStartResponse,
  IngestProgressEvent,
  SseMessage,
} from '../models/IngestModels';

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function getEbooks(skip = 0, limit = 200): Promise<EbookDto[]> {
  return request<EbookDto[]>(`/api/ebooks?skip=${skip}&limit=${limit}`);
}

export async function getEbook(id: string): Promise<EbookDto> {
  return request<EbookDto>(`/api/ebooks/${id}`);
}

export async function updateEbook(
  id: string,
  dto: EbookUpdateDto
): Promise<EbookDto> {
  return request<EbookDto>(`/api/ebooks/${id}`, {
    method: 'PUT',
    body: JSON.stringify(dto),
  });
}

export async function deleteEbook(id: string): Promise<void> {
  return request<void>(`/api/ebooks/${id}`, { method: 'DELETE' });
}

export async function startIngest(
  req: IngestRequestDto
): Promise<IngestStartResponse> {
  return request<IngestStartResponse>('/api/ingest/start', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function pickFolder(): Promise<string | null> {
  const res = await request<{ path: string | null }>('/api/system/folder-picker');
  return res.path;
}

/**
 * Opens an EventSource to the SSE ingest stream and calls onEvent for each
 * progress message. Resolves when stream-end is received or an error occurs.
 * Returns a cleanup function to abort early.
 */
export function streamIngest(
  jobId: string,
  onEvent: (evt: IngestProgressEvent) => void,
  onError: (msg: string) => void
): () => void {
  const url = `${BASE}/api/ingest/stream?job_id=${encodeURIComponent(jobId)}`;
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const parsed: SseMessage = JSON.parse(e.data as string);
      if (parsed.error) {
        onError(parsed.error);
        source.close();
        return;
      }
      const message = parsed.message ?? '';
      const isEndOfStream = message === 'stream-end';
      onEvent({ message, isEndOfStream });
      if (isEndOfStream) {
        source.close();
      }
    } catch {
      onError('Failed to parse server event');
      source.close();
    }
  };

  source.onerror = () => {
    onError('Connection to server lost');
    source.close();
  };

  return () => source.close();
}
