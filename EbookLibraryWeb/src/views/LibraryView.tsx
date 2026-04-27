import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Pencil, Trash2, Loader2 } from 'lucide-react';
import { getEbooks, deleteEbook } from '../api/ebookApi';
import { type EbookDto, getAuthorsDisplay, getCoverUrl } from '../models/EbookDto';

export default function LibraryView() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [status, setStatus] = useState('');

  const { data: books = [], isLoading, refetch } = useQuery({
    queryKey: ['ebooks'],
    queryFn: () => getEbooks(),
  });

  const deleteMutation = useMutation({
    mutationFn: (book: EbookDto) => deleteEbook(book.id),
    onSuccess: (_, book) => {
      setStatus(`Deleted "${book.title ?? book.id}"`);
      qc.invalidateQueries({ queryKey: ['ebooks'] });
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

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">Library</h1>
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
      <div className="flex-1 overflow-auto">
        <table className="min-w-full border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 bg-gray-50">
            <tr>
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
                <td colSpan={8} className="py-12 text-center text-gray-400">
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

      {/* Status bar */}
      {status && (
        <div className="border-t border-gray-200 bg-white px-6 py-2 text-xs text-gray-500">
          {status}
        </div>
      )}
    </div>
  );
}
