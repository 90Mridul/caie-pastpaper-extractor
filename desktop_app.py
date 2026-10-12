import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import io
import os
import zipfile
from PIL import Image, ImageTk
from downloader import fetch_pair, register_active_file, unregister_active_file
from extractor import CAIEExtractor

class CAIEApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CAIE Question & Mark Scheme Extractor")
        self.geometry("1280x820")
        self.minsize(1000, 650)
        self.configure(bg="#0f172a")

        self.current_extractor = None
        self.current_paper_key = None
        self.loaded_files = []
        self.rendered_images = []

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        header = tk.Frame(self, bg="#1e293b", height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        title_lbl = tk.Label(header, text="CAIE Past Paper & Mark Scheme Extractor", font=("Segoe UI", 16, "bold"), fg="#f8fafc", bg="#1e293b")
        title_lbl.pack(side=tk.LEFT, padx=20, pady=12)

        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#334155", sashrelief=tk.RAISED, sashwidth=4)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # LEFT SIDEBAR
        sidebar = tk.Frame(main_pane, bg="#1e293b", width=320, padx=16, pady=16)
        sidebar.pack_propagate(False)
        main_pane.add(sidebar, minsize=280)

        lbl_style = {"fg": "#94a3b8", "bg": "#1e293b", "font": ("Segoe UI", 10, "bold")}

        tk.Label(sidebar, text="SUBJECT", **lbl_style).pack(anchor="w", pady=(0, 2))
        self.subj_var = tk.StringVar(value="9709 - Mathematics")
        self.subj_cb = ttk.Combobox(sidebar, textvariable=self.subj_var, state="readonly", values=[
            "9709 - Mathematics",
            "9702 - Physics",
            "9701 - Chemistry",
            "9618 - Computer Science",
            "Custom"
        ])
        self.subj_cb.pack(fill=tk.X, pady=(0, 12))
        self.subj_cb.bind("<<ComboboxSelected>>", self.on_subject_change)

        self.custom_code_frame = tk.Frame(sidebar, bg="#1e293b")
        tk.Label(self.custom_code_frame, text="CUSTOM CODE", **lbl_style).pack(anchor="w")
        self.custom_code_var = tk.StringVar(value="9708")
        self.custom_entry = ttk.Entry(self.custom_code_frame, textvariable=self.custom_code_var)
        self.custom_entry.pack(fill=tk.X, pady=(0, 12))

        tk.Label(sidebar, text="YEAR", **lbl_style).pack(anchor="w", pady=(0, 2))
        self.year_var = tk.StringVar(value="2022")
        self.year_cb = ttk.Combobox(sidebar, textvariable=self.year_var, values=[str(y) for y in range(2025, 2014, -1)])
        self.year_cb.pack(fill=tk.X, pady=(0, 12))

        tk.Label(sidebar, text="EXAM SERIES", **lbl_style).pack(anchor="w", pady=(0, 2))
        self.series_var = tk.StringVar(value="October / November (w)")
        self.series_cb = ttk.Combobox(sidebar, textvariable=self.series_var, state="readonly", values=[
            "October / November (w)",
            "May / June (s)",
            "February / March (m)"
        ])
        self.series_cb.pack(fill=tk.X, pady=(0, 12))

        tk.Label(sidebar, text="PAPER VARIANT (e.g. 12, 42)", **lbl_style).pack(anchor="w", pady=(0, 2))
        self.paper_var = tk.StringVar(value="12")
        self.paper_entry = ttk.Entry(sidebar, textvariable=self.paper_var)
        self.paper_entry.pack(fill=tk.X, pady=(0, 16))

        # QUESTION NUMBER TEXT BOX
        tk.Label(sidebar, text="QUESTION NUMBER (e.g. 1, 2, 5)", font=("Segoe UI", 11, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w", pady=(0, 2))
        self.qno_var = tk.StringVar(value="1")
        self.qno_entry = ttk.Entry(sidebar, textvariable=self.qno_var, font=("Segoe UI", 12))
        self.qno_entry.pack(fill=tk.X, pady=(0, 20))
        self.qno_entry.bind("<Return>", lambda e: self.start_extraction())

        # Buttons
        self.btn_extract = tk.Button(sidebar, text="🚀 Extract Question & MS", font=("Segoe UI", 11, "bold"),
                                     bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
                                     relief=tk.FLAT, pady=8, cursor="hand2", command=self.start_extraction)
        self.btn_extract.pack(fill=tk.X, pady=(0, 8))

        self.btn_save = tk.Button(sidebar, text="💾 Save to ZIP", font=("Segoe UI", 10),
                                  bg="#059669", fg="white", activebackground="#047857", activeforeground="white",
                                  relief=tk.FLAT, pady=6, cursor="hand2", command=self.save_zip)
        self.btn_save.pack(fill=tk.X, pady=(0, 8))

        self.btn_clear = tk.Button(sidebar, text="🗑️ Clear Display", font=("Segoe UI", 10),
                                   bg="#475569", fg="white", activebackground="#334155", activeforeground="white",
                                   relief=tk.FLAT, pady=6, cursor="hand2", command=self.clear_display)
        self.btn_clear.pack(fill=tk.X, pady=(0, 16))

        self.status_lbl = tk.Label(sidebar, text="Files autodelete 10 mins after clearing", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b", wraplength=260)
        self.status_lbl.pack(fill=tk.X, side=tk.BOTTOM)

        # RIGHT SPLIT VIEW
        content_pane = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, bg="#1e293b", sashrelief=tk.RAISED, sashwidth=4)
        main_pane.add(content_pane, expand=True)

        qp_frame = tk.Frame(content_pane, bg="#0f172a")
        content_pane.add(qp_frame, minsize=400, expand=True)
        tk.Label(qp_frame, text="📝 Question Paper", font=("Segoe UI", 12, "bold"), fg="#f8fafc", bg="#1e293b", pady=6).pack(fill=tk.X)
        self.qp_canvas, self.qp_inner = self.create_scrollable_canvas(qp_frame)

        ms_frame = tk.Frame(content_pane, bg="#0f172a")
        content_pane.add(ms_frame, minsize=400, expand=True)
        tk.Label(ms_frame, text="✅ Mark Scheme", font=("Segoe UI", 12, "bold"), fg="#f8fafc", bg="#1e293b", pady=6).pack(fill=tk.X)
        self.ms_canvas, self.ms_inner = self.create_scrollable_canvas(ms_frame)

    def create_scrollable_canvas(self, parent):
        canvas = tk.Canvas(parent, bg="#0f172a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg="#0f172a")

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(window_id, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", lambda e: None)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return canvas, inner

    def on_subject_change(self, event):
        if self.subj_var.get() == "Custom":
            self.custom_code_frame.pack(fill=tk.X, before=self.year_cb, pady=(0, 12))
        else:
            self.custom_code_frame.pack_forget()

    def get_subject_code(self):
        val = self.subj_var.get()
        if val == "Custom":
            return self.custom_code_var.get().strip()
        return val.split(" ")[0].strip()

    def get_session_code(self):
        v = self.series_var.get()
        if "(w)" in v:
            return "w"
        if "(s)" in v:
            return "s"
        return "m"

    def clear_display(self):
        for widget in self.qp_inner.winfo_children():
            widget.destroy()
        for widget in self.ms_inner.winfo_children():
            widget.destroy()
        self.rendered_images.clear()
        
        # Release extractor and mark files inactive for auto-deletion
        if self.current_extractor:
            self.current_extractor.close()
            self.current_extractor = None
        for f in self.loaded_files:
            unregister_active_file(f)
        self.loaded_files.clear()
        self.current_paper_key = None
        self.status_lbl.config(text="Cleared (files will delete in 10 mins if unused)", fg="#94a3b8")

    def on_close(self):
        self.clear_display()
        self.destroy()

    def start_extraction(self):
        self.btn_extract.config(state=tk.DISABLED)
        self.status_lbl.config(text="Fetching & parsing...", fg="#38bdf8")
        threading.Thread(target=self._run_extract_worker, daemon=True).start()

    def _run_extract_worker(self):
        try:
            subj = self.get_subject_code()
            sess = self.get_session_code()
            year = self.year_var.get().strip()
            paper = self.paper_var.get().strip()
            qno_raw = self.qno_var.get().strip()

            try:
                qno = int(qno_raw)
            except ValueError:
                self.after(0, lambda: messagebox.showerror("Error", "Please enter a valid numeric Question Number (e.g. 1)."))
                return

            paper_key = f"{subj}_{sess}{year[-2:]}_{paper}"

            if self.current_paper_key != paper_key or self.current_extractor is None:
                # Release previous files
                if self.current_extractor:
                    self.current_extractor.close()
                for f in self.loaded_files:
                    unregister_active_file(f)
                self.loaded_files.clear()

                qp_path, ms_path, msg = fetch_pair(subj, sess, year, paper)
                if not qp_path:
                    self.after(0, lambda: messagebox.showerror("Download Error", msg))
                    return
                self.current_extractor = CAIEExtractor(qp_path, ms_path)
                self.current_paper_key = paper_key
                self.loaded_files = [qp_path, ms_path]
                register_active_file(qp_path)
                register_active_file(ms_path)

            ext = self.current_extractor
            qp_imgs = ext.render_question_images(qno)
            ms_imgs = ext.render_mark_scheme_images(qno)

            self.after(0, lambda: self._update_results(qno, qp_imgs, ms_imgs, paper_key))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed: {e}"))
        finally:
            self.after(0, lambda: self.btn_extract.config(state=tk.NORMAL))

    def _update_results(self, qno, qp_imgs, ms_imgs, paper_key):
        for widget in self.qp_inner.winfo_children():
            widget.destroy()
        for widget in self.ms_inner.winfo_children():
            widget.destroy()
        self.rendered_images.clear()

        self.cached_qp_imgs = qp_imgs
        self.cached_ms_imgs = ms_imgs
        self.cached_key = f"{paper_key}_Q{qno}"

        # Populate QP
        if not qp_imgs:
            lbl = tk.Label(self.qp_inner, text=f"Question {qno} not found in this paper.", fg="#f87171", bg="#0f172a", font=("Segoe UI", 11))
            lbl.pack(pady=40)
        else:
            for img in qp_imgs:
                max_w = 600
                w, h = img.size
                if w > max_w:
                    img = img.resize((max_w, int(h * (max_w / w))), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.rendered_images.append(photo)
                lbl = tk.Label(self.qp_inner, image=photo, bg="#0f172a")
                lbl.pack(pady=8, padx=10)

        # Populate MS
        if not ms_imgs:
            lbl = tk.Label(self.ms_inner, text=f"Mark Scheme for Question {qno} not found.", fg="#f87171", bg="#0f172a", font=("Segoe UI", 11))
            lbl.pack(pady=40)
        else:
            for img in ms_imgs:
                max_w = 600
                w, h = img.size
                if w > max_w:
                    img = img.resize((max_w, int(h * (max_w / w))), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.rendered_images.append(photo)
                lbl = tk.Label(self.ms_inner, image=photo, bg="#0f172a")
                lbl.pack(pady=8, padx=10)

        self.status_lbl.config(text=f"Loaded Question {qno} ({paper_key})", fg="#4ade80")

    def save_zip(self):
        if not hasattr(self, "cached_qp_imgs") or (not self.cached_qp_imgs and not self.cached_ms_imgs):
            messagebox.showinfo("Save", "Extract a question first before saving.")
            return

        dest = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP archive", "*.zip")],
            initialfile=f"{self.cached_key}.zip"
        )
        if not dest:
            return

        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for idx, img in enumerate(self.cached_qp_imgs):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                z.writestr(f"{self.cached_key}_QP_part{idx+1}.png", buf.getvalue())
            for idx, img in enumerate(self.cached_ms_imgs):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                z.writestr(f"{self.cached_key}_MS_p{idx+1}.png", buf.getvalue())

        messagebox.showinfo("Saved", f"Successfully saved to:\n{dest}")

if __name__ == "__main__":
    app = CAIEApp()
    app.mainloop()
