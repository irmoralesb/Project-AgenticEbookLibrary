import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Save, Loader2, BookOpen, Search } from 'lucide-react';
import {
  getEbook,
  reextractField,
  updateEbook,
  createKnownPublisher,
  type ReextractDirection,
  type ReextractFieldName,
} from '../api/ebookApi';
import { getCoverUrl } from '../models/EbookDto';
import type { EbookUpdateDto } from '../models/EbookUpdateDto';

const CATEGORIES = [
  'Artificial Intelligence',
  'Biographies & Memoirs',
  'Business & Economics',
  'Children & Young Adult',
  'Computer Science',
  'Cybersecurity',
  'Data Science & Analytics',
  'Design',
  'DevOps & Cloud',
  'Fiction & Literature',
  'Health & Medicine',
  'History',
  'Mathematics',
  'Mobile Development',
  'Networking',
  'Personal Development',
  'Philosophy',
  'Programming',
  'Science & Nature',
  'Software Engineering',
  'Systems & Architecture',
  'Web Development',
  'Other',
] as const;

interface FormState {
  title: string;
  isbn: string;
  authorsText: string;
  year: string;
  description: string;
  category: string;
  subcategory: string;
  tagsText: string;
  publisher: string;
  edition: string;
  language: string;
  pageCount: string;
  hasErrors: boolean;
}

interface ReextractDialogState {
  open: boolean;
  field: ReextractFieldName;
  pageRange: string;
  direction: ReextractDirection;
}

function emptyForm(): FormState {
  return {
    title: '',
    isbn: '',
    authorsText: '',
    year: '',
    description: '',
    category: '',
    subcategory: '',
    tagsText: '',
    publisher: '',
    edition: '',
    language: '',
    pageCount: '',
    hasErrors: false,
  };
}

export default function EbookDetailView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState>(emptyForm());
  const [status, setStatus] = useState('');
  const [reextractStatus, setReextractStatus] = useState('');
  const [dialog, setDialog] = useState<ReextractDialogState>({
    open: false,
    field: 'authors',
    pageRange: '1-5',
    direction: 'front_to_back',
  });

  const { data: ebook, isLoading } = useQuery({
    queryKey: ['ebook', id],
    queryFn: () => getEbook(id!),
    enabled: !!id,
  });

  useEffect(() => {
    if (!ebook) return;
    setForm({
      title: ebook.title ?? '',
      isbn: ebook.isbn ?? '',
      authorsText: ebook.authors?.join(', ') ?? '',
      year: ebook.year?.toString() ?? '',
      description: ebook.description ?? '',
      category: ebook.category ?? '',
      subcategory: ebook.subcategory ?? '',
      tagsText: ebook.tags?.join(', ') ?? '',
      publisher: ebook.publisher ?? '',
      edition: ebook.edition ?? '',
      language: ebook.language ?? '',
      pageCount: ebook.page_count?.toString() ?? '',
      hasErrors: ebook.has_errors ?? false,
    });
  }, [ebook]);

  const saveMutation = useMutation({
    mutationFn: (dto: EbookUpdateDto) => updateEbook(id!, dto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ebooks'] });
      navigate('/');
    },
    onError: (err) => {
      setStatus(`Error: ${(err as Error).message}`);
    },
  });

  const reextractMutation = useMutation({
    mutationFn: () =>
      reextractField(id!, {
        field: dialog.field,
        page_range: dialog.pageRange.trim(),
        direction: dialog.direction,
      }),
    onSuccess: (result) => {
      setReextractStatus(result.message);
      if (result.field === 'authors') {
        const authors = Array.isArray(result.value) ? result.value : [];
        setForm((prev) => ({ ...prev, authorsText: authors.join(', ') }));
      } else if (result.field === 'isbn') {
        const value = typeof result.value === 'string' ? result.value : '';
        setForm((prev) => ({ ...prev, isbn: value }));
      } else if (result.field === 'year') {
        const y =
          typeof result.value === 'number'
            ? String(result.value)
            : typeof result.value === 'string'
              ? result.value
              : '';
        setForm((prev) => ({ ...prev, year: y }));
      } else {
        const value = typeof result.value === 'string' ? result.value : '';
        setForm((prev) => ({ ...prev, publisher: value }));
      }
      setDialog((prev) => ({ ...prev, open: false }));
    },
    onError: (err) => {
      setReextractStatus(`Find again failed: ${(err as Error).message}`);
    },
  });

  const addCatalogMutation = useMutation({
    mutationFn: () => createKnownPublisher(form.publisher),
    onSuccess: (result) => {
      if (result.kind === 'duplicate') {
        setStatus('That publisher is already in the catalog.');
      } else {
        setStatus(`Added "${result.publisher.name}" to the publisher catalog.`);
      }
    },
    onError: (err) => {
      setStatus(`Error: ${(err as Error).message}`);
    },
  });

  const handleChange = (
    field: keyof FormState,
    value: string | boolean
  ) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    const authors = form.authorsText
      .split(',')
      .map((a) => a.trim())
      .filter(Boolean);

    const tags = form.tagsText
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const dto: EbookUpdateDto = {
      title: form.title || null,
      isbn: form.isbn || null,
      authors: authors.length ? authors : null,
      year: form.year ? parseInt(form.year, 10) : null,
      description: form.description || null,
      category: form.category || null,
      subcategory: form.subcategory || null,
      tags,
      publisher: form.publisher || null,
      edition: form.edition || null,
      language: form.language || null,
      page_count: form.pageCount ? parseInt(form.pageCount, 10) : null,
      ...(form.hasErrors ? { has_errors: true } : {}),
    };
    setStatus('');
    saveMutation.mutate(dto);
  };

  const openFindAgain = (field: ReextractFieldName) => {
    setReextractStatus('');
    setDialog({
      open: true,
      field,
      pageRange: '1-5',
      direction: 'front_to_back',
    });
  };

  const handleRunFindAgain = () => {
    if (!/^\s*\d+\s*-\s*\d+\s*$/.test(dialog.pageRange)) {
      setReextractStatus('Find again failed: page range must follow start-end (example: 5-10).');
      return;
    }
    setReextractStatus('Finding value...');
    reextractMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-gray-400">
        <Loader2 size={24} className="animate-spin" />
      </div>
    );
  }

  if (!ebook) {
    return (
      <div className="flex h-full items-center justify-center text-gray-400">
        Ebook not found.
      </div>
    );
  }

  const coverUrl = getCoverUrl(ebook);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-200 bg-white px-6 py-4">
        <button
          onClick={() => navigate('/')}
          className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
        >
          <ArrowLeft size={18} />
        </button>
        <h1 className="text-lg font-semibold text-gray-900">Edit Ebook</h1>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-4xl">
          <div className="flex gap-6">
            {/* Left column: cover + has errors */}
            <div className="flex shrink-0 flex-col items-center gap-4">
              <div className="h-48 w-32 overflow-hidden rounded-lg border border-gray-200 bg-gray-100 shadow-sm">
                {coverUrl ? (
                  <img
                    src={coverUrl}
                    alt={ebook.title ?? ''}
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display = 'none';
                    }}
                  />
                ) : (
                  <div className="flex h-full flex-col items-center justify-center gap-1 text-gray-300">
                    <BookOpen size={28} />
                    <span className="text-xs">No cover</span>
                  </div>
                )}
              </div>

              <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={form.hasErrors}
                  onChange={(e) => handleChange('hasErrors', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                Has errors
              </label>
            </div>

            {/* Right column: form */}
            <div className="flex-1 overflow-auto">
              <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                <div className="grid grid-cols-1 gap-4">
                  {/* Title */}
                  <Field label="Title">
                    <input
                      type="text"
                      value={form.title}
                      onChange={(e) => handleChange('title', e.target.value)}
                      className={inputCls}
                    />
                  </Field>

                  {/* Authors */}
                  <Field label="Authors" hint="comma-separated">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={form.authorsText}
                        onChange={(e) => handleChange('authorsText', e.target.value)}
                        placeholder="Author One, Author Two"
                        className={inputCls}
                      />
                      <FindAgainButton onClick={() => openFindAgain('authors')} />
                    </div>
                  </Field>

                  {/* ISBN, Year, Language, Edition, Page count — one row on wide screens */}
                  <div className="flex flex-wrap items-end gap-x-3 gap-y-5 xl:flex-nowrap xl:gap-x-4">
                    <div className="w-full min-w-0 shrink-0 sm:w-[calc(50%-0.375rem)] xl:w-[11rem]">
                      <Field label="ISBN">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={form.isbn}
                            onChange={(e) => handleChange('isbn', e.target.value)}
                            maxLength={20}
                            className={`${inputCls} w-full max-w-[9.25rem]`}
                          />
                          <FindAgainButton onClick={() => openFindAgain('isbn')} />
                        </div>
                      </Field>
                    </div>
                    <div className="w-full min-w-0 shrink-0 sm:w-[calc(50%-0.375rem)] xl:w-[8.75rem]">
                      <Field label="Year">
                        <div className="flex gap-2">
                          <input
                            type="number"
                            value={form.year}
                            onChange={(e) => handleChange('year', e.target.value)}
                            min={1950}
                            max={2050}
                            className={`${inputCls} min-w-[6.25rem] w-full flex-1`}
                          />
                          <FindAgainButton onClick={() => openFindAgain('year')} />
                        </div>
                      </Field>
                    </div>
                    <div className="min-w-0 flex-1 basis-[min(100%,10rem)] sm:basis-[calc(50%-0.375rem)] xl:basis-0 xl:min-w-[6rem]">
                      <Field label="Language">
                        <input
                          type="text"
                          value={form.language}
                          onChange={(e) => handleChange('language', e.target.value)}
                          className={inputCls}
                        />
                      </Field>
                    </div>
                    <div className="min-w-0 flex-1 basis-[min(100%,10rem)] sm:basis-[calc(50%-0.375rem)] xl:basis-0 xl:min-w-[6rem]">
                      <Field label="Edition">
                        <input
                          type="text"
                          value={form.edition}
                          onChange={(e) => handleChange('edition', e.target.value)}
                          className={inputCls}
                        />
                      </Field>
                    </div>
                    <div className="w-full min-w-0 shrink-0 sm:w-[calc(50%-0.375rem)] xl:w-[6.75rem]">
                      <Field label="Page count">
                        <input
                          type="number"
                          value={form.pageCount}
                          onChange={(e) => handleChange('pageCount', e.target.value)}
                          min={1}
                          className={inputCls}
                        />
                      </Field>
                    </div>
                  </div>

                  {/* Category / Subcategory */}
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Category">
                      <select
                        value={form.category}
                        onChange={(e) => handleChange('category', e.target.value)}
                        className={inputCls}
                      >
                        <option value="">— Select —</option>
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Subcategory">
                      <input
                        type="text"
                        value={form.subcategory}
                        onChange={(e) => handleChange('subcategory', e.target.value)}
                        className={inputCls}
                      />
                    </Field>
                  </div>

                  <Field
                    label="Tags"
                    hint="comma-separated keywords, any topic (not limited to category)"
                  >
                    <input
                      type="text"
                      value={form.tagsText}
                      onChange={(e) => handleChange('tagsText', e.target.value)}
                      placeholder="e.g. C#, SOLID Principles, Design Patterns"
                      className={inputCls}
                    />
                  </Field>

                  {/* Publisher */}
                  <Field label="Publisher">
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="text"
                        value={form.publisher}
                        onChange={(e) => handleChange('publisher', e.target.value)}
                        className={`${inputCls} min-w-0 flex-1 basis-[12rem]`}
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setStatus('');
                          addCatalogMutation.mutate();
                        }}
                        disabled={
                          !form.publisher.trim() || addCatalogMutation.isPending
                        }
                        title="Save this imprint to the library catalog for faster matching on new books"
                        className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-800 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {addCatalogMutation.isPending ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : null}
                        Add to catalog
                      </button>
                      <FindAgainButton onClick={() => openFindAgain('publisher')} />
                    </div>
                  </Field>

                  {/* Description */}
                  <Field label="Description">
                    <textarea
                      value={form.description}
                      onChange={(e) => handleChange('description', e.target.value)}
                      rows={5}
                      className={`${inputCls} resize-y`}
                    />
                  </Field>
                </div>

                {/* Actions */}
                <div className="mt-5 flex items-center gap-3">
                  <button
                    onClick={handleSave}
                    disabled={saveMutation.isPending}
                    className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {saveMutation.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Save size={14} />
                    )}
                    Save
                  </button>

                  <button
                    onClick={() => navigate('/')}
                    className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Status bar */}
      {(status || reextractStatus || reextractMutation.isPending) && (
        <div className="border-t border-gray-200 bg-white px-6 py-2 text-xs">
          {status && <div className="text-red-600">{status}</div>}
          {reextractMutation.isPending ? (
            <div className="flex items-center gap-2 text-indigo-600">
              <Loader2 size={12} className="animate-spin" />
              Finding again...
            </div>
          ) : (
            reextractStatus && <div className="text-gray-700">{reextractStatus}</div>
          )}
        </div>
      )}

      {dialog.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-5 shadow-lg">
            <h2 className="text-base font-semibold text-gray-900">Find again</h2>
            <p className="mt-1 text-sm text-gray-600">
              Re-extract <strong>{dialog.field.toUpperCase()}</strong> from a specific range.
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">
                  Page range
                </label>
                <input
                  type="text"
                  value={dialog.pageRange}
                  onChange={(e) =>
                    setDialog((prev) => ({ ...prev, pageRange: e.target.value }))
                  }
                  placeholder="5-10"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">
                  Direction
                </label>
                <select
                  value={dialog.direction}
                  onChange={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      direction: e.target.value as ReextractDirection,
                    }))
                  }
                  className={inputCls}
                >
                  <option value="front_to_back">Front to Back</option>
                  <option value="back_to_front">Back to Front</option>
                </select>
              </div>
            </div>

            <div className="mt-5 flex items-center gap-3">
              <button
                onClick={handleRunFindAgain}
                disabled={reextractMutation.isPending}
                className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {reextractMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Search size={14} />
                )}
                Run
              </button>
              <button
                onClick={() => setDialog((prev) => ({ ...prev, open: false }))}
                disabled={reextractMutation.isPending}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inputCls =
  'w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500';

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
        {hint && <span className="ml-1 normal-case text-gray-400">({hint})</span>}
      </label>
      {children}
    </div>
  );
}

function FindAgainButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex shrink-0 items-center justify-center rounded-md border border-gray-300 bg-white px-2 text-gray-600 hover:bg-gray-50 hover:text-gray-800"
      title="Find again"
    >
      <Search size={14} />
    </button>
  );
}
