import type { EbookDto } from '../models/EbookDto';
import type { EbookUpdateDto } from '../models/EbookUpdateDto';
import type {
  IngestRequestDto,
  IngestStartResponse,
  IngestProgressEvent,
  SseMessage,
} from '../models/IngestModels';

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export type ReextractDirection = 'front_to_back' | 'back_to_front';
export type ReextractFieldName = 'authors' | 'isbn' | 'publisher' | 'year';

export interface ReextractFieldRequestDto {
  field: ReextractFieldName;
  page_range: string;
  direction: ReextractDirection;
}

export interface ReextractFieldResponseDto {
  field: ReextractFieldName;
  value: string | string[] | number | null;
  used_start_page: number;
  used_end_page: number;
  direction: ReextractDirection;
  message: string;
}

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

export async function reextractField(
  id: string,
  dto: ReextractFieldRequestDto
): Promise<ReextractFieldResponseDto> {
  return request<ReextractFieldResponseDto>(`/api/ebooks/${id}/reextract-field`, {
    method: 'POST',
    body: JSON.stringify(dto),
  });
}

export interface KnownPublisherDto {
  id: string;
  name: string;
  created_at: string;
}

export type CreateKnownPublisherResult =
  | { kind: 'created'; publisher: KnownPublisherDto }
  | { kind: 'duplicate' };

/** Adds a publisher name to the regex catalog (tier before LLM). */
export async function createKnownPublisher(
  name: string
): Promise<CreateKnownPublisherResult> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new Error('Enter a publisher name first.');
  }
  const res = await fetch(`${BASE}/api/publishers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: trimmed }),
  });
  if (res.status === 409) {
    return { kind: 'duplicate' };
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  const publisher = (await res.json()) as KnownPublisherDto;
  return { kind: 'created', publisher };
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
