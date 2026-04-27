export interface IngestRequestDto {
  path: string;
  extension: 'pdf' | 'epub';
  limit?: number;
}

export interface IngestStartResponse {
  job_id: string;
  message: string;
}

export interface SseMessage {
  message?: string;
  error?: string;
}

export interface IngestProgressEvent {
  message: string;
  isEndOfStream: boolean;
}

export const EXTENSIONS = ['pdf', 'epub'] as const;
export type Extension = (typeof EXTENSIONS)[number];
