export interface IngestRequestDto {
  path: string;
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

export const SUPPORTED_FORMATS_LABEL = 'PDF, EPUB';
