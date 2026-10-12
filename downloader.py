import os
import time
import threading
import urllib.request
from typing import Optional, Tuple, Set

PAPERS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(PAPERS_DIR, exist_ok=True)

# Lock and registry of files currently in use by an active session
ACTIVE_FILES_LOCK = threading.Lock()
ACTIVE_FILES: Set[str] = set()

# Cleanup settings: 10 minutes retention
EXPIRY_SECONDS = 600

SOURCES = [
    # dynamicpapers standard CDN
    "https://dynamicpapers.com/wp-content/uploads/2015/09/{filename}",
    # papacambridge mirror
    "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/{filename}",
    # alternative PapaCambridge path
    "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/{subject_code}/{filename}",
]

def format_filename(subject_code: str, session: str, year: int or str, doc_type: str, paper_variant: str) -> str:
    year_str = str(year)[-2:]
    return f"{subject_code}_{session.lower()}{year_str}_{doc_type.lower()}_{paper_variant}.pdf"

def register_active_file(filepath: Optional[str]):
    """Marks a file as actively being used by the user, and updates its access time."""
    if not filepath or not os.path.exists(filepath):
        return
    with ACTIVE_FILES_LOCK:
        ACTIVE_FILES.add(os.path.abspath(filepath))
    try:
        now = time.time()
        os.utime(filepath, (now, now))
    except Exception:
        pass

def unregister_active_file(filepath: Optional[str]):
    """Unmarks a file when cleared or session ends, starting its expiration countdown."""
    if not filepath:
        return
    with ACTIVE_FILES_LOCK:
        ACTIVE_FILES.discard(os.path.abspath(filepath))

def clear_all_active_files():
    """Unregisters all files, e.g. when user clicks Clear."""
    with ACTIVE_FILES_LOCK:
        ACTIVE_FILES.clear()

def cleanup_expired_files():
    """
    Deletes any PDF in downloads that:
    1. Is older than EXPIRY_SECONDS (10 minutes) since last access/modification.
    2. Is NOT currently in the active registry.
    """
    if not os.path.exists(PAPERS_DIR):
        return

    now = time.time()
    with ACTIVE_FILES_LOCK:
        active_set = set(ACTIVE_FILES)

    for fname in os.listdir(PAPERS_DIR):
        if not fname.lower().endswith(".pdf"):
            continue
        full_path = os.path.abspath(os.path.join(PAPERS_DIR, fname))
        if full_path in active_set:
            continue
        try:
            mtime = os.path.getmtime(full_path)
            if now - mtime >= EXPIRY_SECONDS:
                try:
                    os.remove(full_path)
                except PermissionError:
                    # File may be temporarily held open by a process
                    pass
        except Exception:
            pass

def _background_cleaner_loop():
    while True:
        try:
            cleanup_expired_files()
        except Exception:
            pass
        time.sleep(60) # Run check every minute

# Launch background thread once per process
_cleaner_thread = threading.Thread(target=_background_cleaner_loop, daemon=True)
_cleaner_thread.start()

def download_file_if_needed(filename: str, subject_code: str) -> Optional[str]:
    # Run a quick check for any older files
    cleanup_expired_files()

    local_path = os.path.join(PAPERS_DIR, filename)
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
        register_active_file(local_path)
        return local_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    for url_tmpl in SOURCES:
        url = url_tmpl.format(filename=filename, subject_code=subject_code)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if data.startswith(b"%PDF"):
                        with open(local_path, "wb") as f:
                            f.write(data)
                        register_active_file(local_path)
                        return local_path
        except Exception:
            continue

    return None

def fetch_pair(subject_code: str, session: str, year: int or str, paper_variant: str) -> Tuple[Optional[str], Optional[str], str]:
    qp_fname = format_filename(subject_code, session, year, "qp", paper_variant)
    ms_fname = format_filename(subject_code, session, year, "ms", paper_variant)

    qp_path = download_file_if_needed(qp_fname, subject_code)
    if not qp_path:
        return None, None, f"Could not retrieve Question Paper '{qp_fname}'. Please verify year, session, and paper variant."

    ms_path = download_file_if_needed(ms_fname, subject_code)
    if not ms_path:
        return qp_path, None, f"Found QP '{qp_fname}' but Mark Scheme '{ms_fname}' was not found online."

    return qp_path, ms_path, "Success"
