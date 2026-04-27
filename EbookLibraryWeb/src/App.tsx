import { NavLink, Outlet } from 'react-router-dom';
import { BookOpen, Upload } from 'lucide-react';

export default function App() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-gray-50 text-gray-900">
      {/* Nav rail */}
      <aside className="flex w-52 shrink-0 flex-col border-r border-gray-200 bg-white">
        <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-5">
          <BookOpen size={20} className="text-indigo-600" />
          <span className="text-sm font-semibold text-gray-800">Ebook Library</span>
        </div>

        <nav className="flex flex-col gap-1 p-2 pt-3">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <BookOpen size={16} />
            Library
          </NavLink>

          <NavLink
            to="/ingest"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <Upload size={16} />
            Ingest
          </NavLink>
        </nav>
      </aside>

      {/* Content area */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
