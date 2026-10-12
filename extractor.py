import re
import io
from typing import List, Dict, Optional, Tuple
import pymupdf as fitz
from PIL import Image

class CAIEExtractor:
    def __init__(self, qp_path: str, ms_path: str):
        self.qp_path = qp_path
        self.ms_path = ms_path
        self.qp_doc = fitz.open(qp_path)
        self.ms_doc = fitz.open(ms_path)
        self._qp_questions = self._index_qp()
        self._ms_questions = self._index_ms()

    def close(self):
        """Releases underlying file handles so the files can be safely deleted."""
        try:
            if hasattr(self, 'qp_doc') and self.qp_doc:
                self.qp_doc.close()
            if hasattr(self, 'ms_doc') and self.ms_doc:
                self.ms_doc.close()
        except Exception:
            pass


    def _index_qp(self) -> Dict[int, List[Dict]]:
        """
        Indexes QP pages by Question Number.
        Filters out BLANK PAGE and covers.
        """
        q_map: Dict[int, List[Dict]] = {}
        starts = []

        for pno in range(1, len(self.qp_doc)):
            page = self.qp_doc[pno]
            text_full = page.get_text("text")
            if "BLANK PAGE" in text_full:
                continue

            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))
            for b in blocks:
                x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4].strip()
                if y0 < 50 or y0 > page.rect.height - 50:
                    continue
                # Margin detection
                if x0 <= 90:
                    m = re.match(r"^([1-9][0-9]?)\s*(?:\n|\s|[A-Z]|\(|$)", text)
                    if m:
                        q_num = int(m.group(1))
                        if not any(s[0] == q_num for s in starts):
                            starts.append((q_num, pno, y0))

        starts.sort(key=lambda s: (s[1], s[2]))
        cleaned = []
        expected = 1
        for q, pno, y0 in starts:
            if q == expected:
                cleaned.append((q, pno, y0))
                expected += 1
            elif expected < q <= expected + 2:
                cleaned.append((q, pno, y0))
                expected = q + 1

        for i, (q, pno, y0) in enumerate(cleaned):
            q_map[q] = []
            if i + 1 < len(cleaned):
                next_p, next_y = cleaned[i + 1][1], cleaned[i + 1][2]
            else:
                next_p, next_y = len(self.qp_doc) - 1, None

            for p in range(pno, next_p + 1):
                if "BLANK PAGE" in self.qp_doc[p].get_text("text"):
                    continue
                top = y0 - 10 if p == pno else 45
                bot = next_y - 5 if p == next_p and next_y is not None else self.qp_doc[p].rect.height - 45
                if bot > top + 15:
                    q_map[q].append({
                        "page": p,
                        "y0": max(0, top),
                        "y1": min(self.qp_doc[p].rect.height, bot),
                        "x0": 30,
                        "x1": self.qp_doc[p].rect.width - 30
                    })

        return q_map

    def _index_ms(self) -> Dict[int, List[int]]:
        """
        Indexes Mark Scheme pages by question number.
        Filters out 'Generic Marking Principles', 'Mathematics Specific Marking Principles', etc.
        Only indexes pages where actual question answers are given.
        """
        q_map: Dict[int, List[int]] = {}

        for pno in range(len(self.ms_doc)):
            page = self.ms_doc[pno]
            text = page.get_text("text")

            # Ignore Generic Marking Principles / Mathematics Specific Marking Principles pages
            if "Marking Principles" in text or "GENERIC MARKING" in text:
                continue

            # Must contain Question & Answer columns
            if not ("Question" in text and "Answer" in text):
                continue

            is_rot90 = (page.rotation == 90)
            words = page.get_text("words")
            found = set()

            for w in words:
                x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4].strip()
                if "/" in word or "UCLES" in word or "Page" in word or word == "Question":
                    continue

                if is_rot90:
                    # In landscape rotated tables, question column has y in ~720 to 778
                    in_col = (720 <= y0 <= 778)
                else:
                    # In portrait tables, question column has x in ~35 to 105
                    in_col = (35 <= x0 <= 105 and 60 <= y0 <= page.rect.height - 60)

                if in_col:
                    m = re.match(r"^([1-9][0-9]?)(?:\([a-z0-9]+\))?$", word)
                    if m:
                        try:
                            found.add(int(m.group(1)))
                        except ValueError:
                            pass

            for q in found:
                if q not in q_map:
                    q_map[q] = []
                if pno not in q_map[q]:
                    q_map[q].append(pno)

        return q_map

    def get_available_questions(self) -> List[int]:
        qp_qs = set(self._qp_questions.keys())
        ms_qs = set(self._ms_questions.keys())
        all_qs = sorted(list(qp_qs | ms_qs))
        return all_qs

    def render_question_images(self, q_num: int, zoom: float = 2.0) -> List[Image.Image]:
        chunks = self._qp_questions.get(q_num, [])
        images = []
        mat = fitz.Matrix(zoom, zoom)

        for c in chunks:
            page = self.qp_doc[c["page"]]
            rect = fitz.Rect(c["x0"], c["y0"], c["x1"], c["y1"])
            pix = page.get_pixmap(matrix=mat, clip=rect)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)

        return images

    def render_mark_scheme_images(self, q_num: int, zoom: float = 2.0) -> List[Image.Image]:
        pages = self._ms_questions.get(q_num, [])
        images = []
        mat = fitz.Matrix(zoom, zoom)

        for pno in pages:
            page = self.ms_doc[pno]
            # get_pixmap rotates according to page.rotation so it is rendered upright
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)

        return images
