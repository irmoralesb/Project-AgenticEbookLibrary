const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface EbookDto {
  id: string;
  title: string | null;
  isbn: string | null;
  authors: string[] | null;
  year: number | null;
  description: string | null;
  category: string | null;
  subcategory: string | null;
  publisher: string | null;
  edition: string | null;
  language: string | null;
  page_count: number | null;
  file_name: string | null;
  cover_image_path: string | null;
  cover_image_mime_type: string | null;
  has_errors: boolean;
  is_metadata_stored: boolean;
  is_embeded_data_stored: boolean;
}

export function getAuthorsDisplay(ebook: EbookDto): string {
  return ebook.authors?.join(', ') ?? '';
}

export function getCoverUrl(ebook: EbookDto): string | null {
  if (!ebook.cover_image_path) return null;
  return `${API_BASE}/covers/${ebook.cover_image_path}`;
}
