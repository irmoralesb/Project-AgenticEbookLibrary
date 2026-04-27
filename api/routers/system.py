"""System-level utilities: native OS folder picker."""

from fastapi import APIRouter

from api.schemas import FolderPickerResponse

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/folder-picker", response_model=FolderPickerResponse)
def pick_folder() -> FolderPickerResponse:
    """Open a native Windows folder browser dialog on the server machine and
    return the selected path.  Because the API and WPF client run on the same
    Windows machine, this is a pragmatic solution for local-only deployments.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="Select ebook folder")
        root.destroy()
        return FolderPickerResponse(path=selected if selected else None)
    except Exception:
        return FolderPickerResponse(path=None)
