import { useRef, useState, useCallback, useEffect } from 'react';
import { FolderOpen, Play, Square, Loader2 } from 'lucide-react';
import { startIngest, pickFolder, streamIngest } from '../api/ebookApi';
import { EXTENSIONS, type Extension } from '../models/IngestModels';

export default function IngestView() {
  const [selectedPath, setSelectedPath] = useState('');
  const [extension, setExtension] = useState<Extension>('pdf');
  const [isIngesting, setIsIngesting] = useState(false);
  const [progressLog, setProgressLog] = useState<string[]>([]);
  const [status, setStatus] = useState('');
  const [isBrowsing, setIsBrowsing] = useState(false);

  const stopRef = useRef<(() => void) | null>(null);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [progressLog]);

  const handleBrowse = async () => {
    setIsBrowsing(true);
    setStatus('');
    try {
      const path = await pickFolder();
      if (path) setSelectedPath(path);
    } catch (err) {
      setStatus(`Browse error: ${(err as Error).message}`);
    } finally {
      setIsBrowsing(false);
    }
  };

  const appendLog = useCallback((msg: string) => {
    setProgressLog((prev) => [...prev, msg]);
  }, []);

  const handleStart = async () => {
    if (!selectedPath.trim() || isIngesting) return;
    setProgressLog([]);
    setStatus('');
    setIsIngesting(true);

    try {
      const response = await startIngest({ path: selectedPath.trim(), extension });
      appendLog(`Job started: ${response.job_id}`);

      const stop = streamIngest(
        response.job_id,
        (evt) => {
          if (!evt.isEndOfStream) {
            appendLog(evt.message);
          } else {
            appendLog('--- Ingestion complete ---');
            setIsIngesting(false);
            setStatus('Ingestion completed successfully.');
            stopRef.current = null;
          }
        },
        (errMsg) => {
          appendLog(`Error: ${errMsg}`);
          setIsIngesting(false);
          setStatus(`Error: ${errMsg}`);
          stopRef.current = null;
        }
      );
      stopRef.current = stop;
    } catch (err) {
      setStatus(`Failed to start: ${(err as Error).message}`);
      setIsIngesting(false);
    }
  };

  const handleCancel = () => {
    stopRef.current?.();
    stopRef.current = null;
    setIsIngesting(false);
    setStatus('Ingestion cancelled.');
    appendLog('--- Cancelled by user ---');
  };

  const canStart = !isIngesting && selectedPath.trim().length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">Ingest</h1>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-auto p-6">
        {/* Input card */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-gray-500">
              Folder path
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={selectedPath}
                onChange={(e) => setSelectedPath(e.target.value)}
                placeholder="C:\path\to\ebooks"
                disabled={isIngesting}
                className="flex-1 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400"
              />
              <button
                onClick={handleBrowse}
                disabled={isIngesting || isBrowsing}
                className="flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                {isBrowsing ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <FolderOpen size={14} />
                )}
                Browse…
              </button>
            </div>
          </div>

          <div className="mb-5 flex items-center gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-gray-500">
                File type
              </label>
              <select
                value={extension}
                onChange={(e) => setExtension(e.target.value as Extension)}
                disabled={isIngesting}
                className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400"
              >
                {EXTENSIONS.map((ext) => (
                  <option key={ext} value={ext}>
                    {ext}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleStart}
              disabled={!canStart}
              className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              <Play size={14} />
              Start Ingestion
            </button>

            <button
              onClick={handleCancel}
              disabled={!isIngesting}
              className="flex items-center gap-2 rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              <Square size={14} />
              Cancel
            </button>

            {isIngesting && (
              <div className="flex items-center gap-2 text-sm text-indigo-600">
                <Loader2 size={14} className="animate-spin" />
                Processing…
              </div>
            )}
          </div>
        </div>

        {/* Progress log */}
        {progressLog.length > 0 && (
          <div className="flex flex-col">
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Progress
              </span>
              <button
                onClick={() => setProgressLog([])}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Clear
              </button>
            </div>
            <div className="flex-1 overflow-auto rounded-lg border border-gray-200 bg-gray-900 p-4">
              <div className="min-h-0 space-y-0.5 font-mono text-xs text-green-400">
                {progressLog.map((line, i) => (
                  <div key={i} className="whitespace-pre-wrap leading-5">
                    {line}
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          </div>
        )}
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
