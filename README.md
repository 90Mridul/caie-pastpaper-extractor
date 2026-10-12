# CAIE Past Paper & Mark Scheme Extractor 📚

An intelligent, on-demand question and mark scheme extractor for Cambridge Assessment International Education (CAIE) AS & A Level past papers. 

Extracts the **exact question** (including all subparts like `(a)`, `(b)`, `(c)` alongside diagrams and working space) and the **exact corresponding mark scheme** side by side.

---

## ✨ Features

- **On-Demand Auto-Download**: Enter the syllabus code, exam series, year, and paper variant — the application automatically downloads both the Question Paper (`qp`) and Mark Scheme (`ms`) directly from reliable online mirrors.
- **Unified Multi-part Extraction**: Selecting Question `1` captures all subparts (`1(a)`, `1(b)`, etc.) seamlessly without needing individual part queries.
- **Smart Orientation & Layout Handling**: Handles landscape/rotated CAIE mark scheme tables, keeping all pages oriented upright.
- **Automated 10-Minute Cleanup**: Temporary downloaded PDFs automatically purge 10 minutes after you clear the screen or switch papers, keeping your disk clean.
- **Two User Interfaces**:
  1. **Modern Web UI** (powered by Streamlit)
  2. **Native Desktop GUI** (powered by Tkinter, zero extra browser dependencies)
- **One-Click Export**: Download a bundled ZIP of high-resolution question and mark scheme images anytime.

---

## 🎯 Pre-Configured Subjects

- **9709**: Mathematics
- **9702**: Physics
- **9701**: Chemistry
- **9618**: Computer Science
- **Custom**: Any other 4-digit CAIE syllabus code (e.g., `9708` Economics, `9706` Accounting)

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/caie-pastpaper-extractor.git
cd caie-pastpaper-extractor
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the App

#### Option A: Web App (Streamlit)
```bash
streamlit run app.py
```
*(Or double-click `run_web.bat` on Windows)*. Then open [http://localhost:8501](http://localhost:8501) in your browser.

#### Option B: Desktop GUI (Tkinter)
```bash
python desktop_app.py
```
*(Or double-click `run_desktop.bat` on Windows)*.

---

## 📁 Project Structure

```
caie_extractor/
├── app.py              # Streamlit Web UI
├── desktop_app.py      # Standalone Desktop Tkinter UI
├── downloader.py       # Online paper fetcher, caching & 10-min auto-cleanup
├── extractor.py        # PyMuPDF question & mark scheme parser & renderer
├── run_web.bat         # 1-click Windows launcher for Web App
├── run_desktop.bat     # 1-click Windows launcher for Desktop App
├── requirements.txt    # Project dependencies
├── .gitignore          # Git ignore rules (ignores downloads & pycache)
└── README.md           # Documentation
```

---

## 📄 License

MIT License. Free to use and modify for personal study and non-commercial educational purposes.
