export interface EbookUpdateDto {
  title?: string | null;
  isbn?: string | null;
  authors?: string[] | null;
  year?: number | null;
  description?: string | null;
  category?: string | null;
  subcategory?: string | null;
  publisher?: string | null;
  edition?: string | null;
  language?: string | null;
  page_count?: number | null;
  has_errors?: boolean;
}
