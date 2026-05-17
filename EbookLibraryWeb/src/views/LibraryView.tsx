import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Pencil, Trash2, Loader2, Search } from 'lucide-react';
import {
  getEbooks,
  deleteEbook,
  startBatchReextractField,
  streamBatchReextractField,
  type ReextractDirection,
  type ReextractFieldName,
} from '../api/ebookApi';
import {
  type EbookDto,
  getAuthorsDisplay,
  getCoverUrl,
  getTagsDisplay,
} from '../models/EbookDto';

const PAGE_RANGE_RE = /^\s*\d+\s*-\s*\d+\s*$/;

interface BatchDialogState {
  open: boolean;
  field: ReextractFieldName;
  pageRange: string;
  direction: ReextractDirection;
}

export default function LibraryView() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [status, setStatus] = useState('');
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [progressLog, setProgressLog] = useState<string[]>([]);
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [batchDialog, setBatchDialog] = useState<BatchDialogState>({
    open: false,
    field: 'authors',
    pageRange: '1-5',
    direction: 'front_to_back',
  });
  const logEndRef = useRef<HTMLDivElement | null>(null);
  const batchStreamStopRef = useRef<(() => void) | null>(null);

  const { data: books = [], isLoading, refetch } = useQuery({
    queryKey: ['ebooks'],
    queryFn: () => getEbooks(),
  });

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [progressLog]);

  useEffect(
    () => () => {
      batchStreamStopRef.current?.();
      batchStreamStopRef.current = null;
    },
    []
  );

  const appendLog = useCallback((msg: string) => {
    setProgressLog((prev) => [...prev, msg]);
  }, []);

  const deleteMutation = useMutation({
    mutationFn: (book: EbookDto) => deleteEbook(book.id),
    onSuccess: (_, book) => {
      setStatus(`Deleted "${book.title ?? book.id}"`);
      qc.invalidateQueries({ queryKey: ['ebooks'] });
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(book.id);
        return next;
      });
    },
    onError: (err) => {
      setStatus(`Error: ${(err as Error).message}`);
    },
  });

  const handleRefresh = async () => {
    setStatus('');
    await refetch();
  };

  const handleDelete = (book: EbookDto) => {
    if (!window.confirm(`Delete "${book.title ?? book.file_name}"?`)) return;
    deleteMutation.mutate(book);
  };

  const toggleBatchMode = (on: boolean) => {
    setBatchMode(on);
    if (!on) {
      setSelectedIds(new Set());
      batchStreamStopRef.current?.();
      batchStreamStopRef.current = null;
      setIsBatchRunning(false);
    }
  };

  const toggleRowSelected = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const allVisibleSelected =
    books.length > 0 && books.every((b) => selectedIds.has(b.id));

  const toggleSelectAllVisible = () => {
    setSelectedIds(() => {
      if (allVisibleSelected) return new Set();
      return new Set(books.map((b) => b.id));
    });
  };

  const openBatchDialog = () => {
    if (selectedIds.size === 0) return;
    setBatchDialog((prev) => ({ ...prev, open: true }));
  };

  const runBatchReextract = async () => {
    if (!PAGE_RANGE_RE.test(batchDialog.pageRange)) {
      setStatus('Page range must look like start-end (example: 5-10).');
      return;
    }
    const ids = [...selectedIds];
    if (ids.length === 0) return;

    setBatchDialog((prev) => ({ ...prev, open: false }));
    setProgressLog([]);
    setIsBatchRunning(true);
    setStatus('');

    batchStreamStopRef.current?.();
    batchStreamStopRef.current = null;

    try {
      const start = await startBatchReextractField({
        ebook_ids: ids,
        field: batchDialog.field,
        page_range: batchDialog.pageRange.trim(),
        direction: batchDialog.direction,
      });
      appendLog(`Job started: ${start.job_id}`);

      const stop = streamBatchReextractField(
        start.job_id,
        (evt) => {
          if (!evt.isEndOfStream) {
            appendLog(evt.message);
          } else {
            appendLog('--- Batch complete ---');
            setIsBatchRunning(false);
            batchStreamStopRef.current = null;
            void qc.invalidateQueries({ queryKey: ['ebooks'] });
          }
        },
        (errMsg) => {
          appendLog(`Error: ${errMsg}`);
          setIsBatchRunning(false);
          batchStreamStopRef.current = null;
        }
      );
      batchStreamStopRef.current = stop;
    } catch (err) {
      appendLog(`Failed to start: ${(err as Error).message}`);
      setIsBatchRunning(false);
    }
  };

  const colCount = batchMode ? 10 : 9;

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">Library</h1>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={batchMode}
            onChange={(e) => toggleBatchMode(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Batch update
        </label>
        {batchMode && (
          <button
            type="button"
            onClick={openBatchDialog}
            disabled={selectedIds.size === 0 || isBatchRunning}
            className="flex items-center gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-800 hover:bg-indigo-100 disabled:opacity-50"
          >
            {isBatchRunning ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Search size={14} />
            )}
            Re-extract selected…
          </button>
        )}
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="ml-auto flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <RefreshCw size={14} />
          )}
          Refresh
        </button>
      </div>

      {/* Table */}
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-full border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 bg-gray-50">
            <tr>
              {batchMode && (
                <th className="w-10 border-b border-gray-200 px-2 py-3 text-center text-xs font-medium uppercase tracking-wide text-gray-500">
                  <input
                    type="checkbox"
                    title="Select all visible"
                    checked={allVisibleSelected}
                    onChange={toggleSelectAllVisible}
                    disabled={books.length === 0}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                </th>
              )}
              <th className="w-16 border-b border-gray-200 px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Cover
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Title
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Authors
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Category
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Tags
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Year
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Publisher
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                Pages
              </th>
              <th className="border-b border-gray-200 px-3 py-3 text-center text-xs font-medium uppercase tracking-wide text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white">
            {books.length === 0 && !isLoading && (
              <tr>
                <td colSpan={colCount} className="py-12 text-center text-gray-400">
                  No ebooks found.
                </td>
              </tr>
            )}
            {books.map((book) => {
              const coverUrl = getCoverUrl(book);
              return (
                <tr
                  key={book.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  {batchMode && (
                    <td className="border-b border-gray-100 px-2 py-2 text-center">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(book.id)}
                        onChange={() => toggleRowSelected(book.id)}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                    </td>
                  )}
                  <td className="border-b border-gray-100 px-3 py-2">
                    {coverUrl ? (
                      <img
                        src={coverUrl}
                        alt={book.title ?? ''}
                        className="h-14 w-10 rounded object-cover shadow-sm"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="h-14 w-10 rounded bg-gray-100 flex items-center justify-center text-gray-300 text-xs">
                        N/A
                      </div>
                    )}
                  </td>
                  <td className="max-w-xs border-b border-gray-100 px-3 py-2 font-medium text-gray-900">
                    <div className="truncate" title={book.title ?? ''}>
                      {book.title ?? <span className="text-gray-400 italic">Untitled</span>}
                    </div>
                    {book.has_errors && (
                      <span className="mt-0.5 inline-block rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700">
                        Has errors
                      </span>
                    )}
                  </td>
                  <td className="max-w-[180px] border-b border-gray-100 px-3 py-2 text-gray-600">
                    <div className="truncate">{getAuthorsDisplay(book)}</div>
                  </td>
                  <td className="border-b border-gray-100 px-3 py-2 text-gray-600">
                    {book.category}
                  </td>
                  <td className="max-w-[200px] border-b border-gray-100 px-3 py-2 text-gray-600">
                    <div
                      className="truncate"
                      title={
                        book.tags && book.tags.length > 0
                          ? book.tags.join(', ')
                          : undefined
                      }
                    >
                      {getTagsDisplay(book)}
                    </div>
                  </td>
                  <td className="border-b border-gray-100 px-3 py-2 text-gray-600">
                    {book.year}
                  </td>
                  <td className="max-w-[140px] border-b border-gray-100 px-3 py-2 text-gray-600">
                    <div className="truncate">{book.publisher}</div>
                  </td>
                  <td className="border-b border-gray-100 px-3 py-2 text-right text-gray-600">
                    {book.page_count}
                  </td>
                  <td className="border-b border-gray-100 px-3 py-2">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => navigate(`/ebooks/${book.id}/edit`)}
                        title="Edit"
                        className="rounded p-1.5 text-gray-500 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        onClick={() => handleDelete(book)}
                        title="Delete"
                        disabled={deleteMutation.isPending}
                        className="rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {(batchMode || progressLog.length > 0 || isBatchRunning) && (
        <div className="max-h-40 shrink-0 overflow-y-auto border-t border-gray-200 bg-gray-50 px-4 py-2 font-mono text-xs text-gray-700">
          {progressLog.length === 0 && !isBatchRunning && (
            <div className="text-gray-400">Batch progress will appear here.</div>
          )}
          {progressLog.map((line, i) => (
            <div key={`${i}-${line.slice(0, 24)}`}>{line}</div>
          ))}
          {isBatchRunning && (
            <div className="mt-1 flex items-center gap-2 text-indigo-600">
              <Loader2 size={12} className="animate-spin" />
              Running…
            </div>
          )}
          <div ref={logEndRef} />
        </div>
      )}

      {/* Status bar */}
      {status && (
        <div className="border-t border-gray-200 bg-white px-6 py-2 text-xs text-gray-500">
          {status}
        </div>
      )}

      {batchDialog.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-5 shadow-lg">
            <h2 className="text-base font-semibold text-gray-900">Batch re-extract</h2>
            <p className="mt-1 text-sm text-gray-600">
              Re-extract and save one field for {selectedIds.size} selected book(s).
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">
                  Field
                </label>
                <select
                  value={batchDialog.field}
                  onChange={(e) =>
                    setBatchDialog((prev) => ({
                      ...prev,
                      field: e.target.value as ReextractFieldName,
                    }))
                  }
                  className={inputCls}
                >
                  <option value="authors">Authors</option>
                  <option value="isbn">ISBN</option>
                  <option value="publisher">Publisher</option>
                  <option value="year">Year</option>
                  <option value="tags">Tags</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">
                  Page range
                </label>
                <input
                  type="text"
                  value={batchDialog.pageRange}
                  onChange={(e) =>
                    setBatchDialog((prev) => ({ ...prev, pageRange: e.target.value }))
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
                  value={batchDialog.direction}
                  onChange={(e) =>
                    setBatchDialog((prev) => ({
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
                type="button"
                onClick={() => void runBatchReextract()}
                disabled={isBatchRunning}
                className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {isBatchRunning ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Search size={14} />
                )}
                Run
              </button>
              <button
                type="button"
                onClick={() => setBatchDialog((prev) => ({ ...prev, open: false }))}
                disabled={isBatchRunning}
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
