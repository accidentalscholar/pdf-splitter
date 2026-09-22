# ==========================================
# PDF Splitter
# Version: 2.0
# Citation: Pundir, V. (2026, September 22). PDF Splitter Version (2.0). Retrieved from https://github.com/accidentalscholar/pdf-splitter. 
# Citation: RIS and BibTeX files included for referencing software.
# Tested in: Python 3.10.9 64 bit packaged by Anaconda, Inc.
# Reporsitory: https://github.com/accidentalscholar/pdf-splitter
# Provided under: GNU AFFERO GENERAL PUBLIC LICENSE (see accompanying license file)
# ==========================================

import sys
import os
import subprocess
import gc
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import re
import statistics

# Check for path.txt and append custom paths (for restricted environments)
if os.path.exists("path.txt"):
    try:
        with open("path.txt", "r") as f:
            for line in f:
                custom_path = line.strip()
                if custom_path and os.path.exists(custom_path):
                    sys.path.append(custom_path)
    except Exception:
        pass  # Ignore errors if unable to read the file

try:
    import fitz  # PyMuPDF
    from PIL import Image, ImageTk
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "PyMuPDF", "Pillow"])
        import fitz
        from PIL import Image, ImageTk
    except Exception:
        # Fallback for manual installation via Anaconda prompt
        tk.Tk().withdraw()  # Hide root window for the error box
        messagebox.showerror(
            "Missing Dependencies",
            "Failed to automatically install required libraries.\n\n"
            "Please run the following commands in your Anaconda prompt:\n"
            "pip install PyMuPDF\n"
            "pip install Pillow"
        )
        sys.exit(1)


class BulkDocumentSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bulk PDF & EPUB Splitter v2.0")
        self.root.geometry("1100x850")
        
        # Handle Spyder close behavior cleanly so the kernel doesn't hang
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bring window to top briefly, then allow normal window layering
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        
        self.folder_path = None
        self.doc_files = []
        self.current_file_index = -1
        
        # Current active document state
        self.file_path = None
        self.doc = None
        self.total_pages = 0
        self.current_preview_page = 0
        self.bookmarks = []
        self.photo = None
        
        # Container frame for manual UI
        self.main_frame = None
        
        # Start by asking for the folder
        self.select_folder()

    def select_folder(self):
        """Asks user to select a folder and gathers all PDF and EPUB files."""
        self.root.attributes('-topmost', True)
        self.folder_path = filedialog.askdirectory(title="Select Folder Containing PDF or EPUB Files")
        self.root.attributes('-topmost', False)
        
        if not self.folder_path:
            self.root.destroy()
            return

        # Find all PDF and EPUB files (case-insensitive) in the selected folder
        all_files = os.listdir(self.folder_path)
        supported_exts = (".pdf", ".epub")
        self.doc_files = [
            os.path.join(self.folder_path, f) 
            for f in sorted(all_files) 
            if f.lower().endswith(supported_exts)
        ]
        
        if not self.doc_files:
            messagebox.showinfo(
                "No Files Found", 
                "No PDF or EPUB files were found in the selected folder."
            )
            self.root.destroy()
            return

        self.current_file_index = -1
        self.process_next_document()

    def free_current_document_memory(self):
        """Explicitly releases document memory and triggers garbage collection."""
        if self.photo:
            self.photo = None
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None
            
        self.total_pages = 0
        self.bookmarks = []
        self.current_preview_page = 0
        gc.collect()

    def process_next_document(self):
        """Advances to the next PDF/EPUB in the queue or concludes if finished."""
        # Ensure previous file memory is thoroughly cleaned
        self.free_current_document_memory()
        
        # Clear manual UI frame if currently visible
        if self.main_frame is not None:
            self.main_frame.destroy()
            self.main_frame = None

        self.current_file_index += 1
        
        if self.current_file_index >= len(self.doc_files):
            messagebox.showinfo(
                "Batch Processing Complete", 
                f"All {len(self.doc_files)} file(s) in the folder have been processed."
            )
            self.root.destroy()
            return

        self.file_path = self.doc_files[self.current_file_index]
        file_ext = os.path.splitext(self.file_path)[1].upper()
        
        try:
            self.doc = fitz.open(self.file_path)
            self.total_pages = len(self.doc)
        except Exception as e:
            messagebox.showerror(
                f"Error Opening {file_ext}", 
                f"Could not open file:\n{os.path.basename(self.file_path)}\n\nReason: {str(e)}\n\nSkipping to next file."
            )
            self.process_next_document()
            return
            
        if self.total_pages == 0:
            messagebox.showwarning(
                "Empty Document", 
                f"The file {os.path.basename(self.file_path)} has no readable pages. Skipping to next."
            )
            self.process_next_document()
            return

        # Extract bookmark / table of contents data
        # fitz get_toc() returns list of [level, title, page_number_1_based]
        try:
            raw_toc = self.doc.get_toc()
            # Filter for valid entries with legitimate page numbers
            self.bookmarks = [
                entry for entry in raw_toc 
                if len(entry) >= 3 and isinstance(entry[2], int) and 1 <= entry[2] <= self.total_pages
            ]
        except Exception:
            self.bookmarks = []

        if self.bookmarks:
            self.prompt_split_mode()
        else:
            # No bookmarks found; open the manual UI directly
            self.setup_manual_ui()
            self.show_page(0)

    def prompt_split_mode(self):
        """Displays modal asking whether to split automatically via bookmarks/TOC or manually."""
        dialog = tk.Toplevel(self.root)
        current_num = self.current_file_index + 1
        total_num = len(self.doc_files)
        dialog.title(f"TOC / Bookmarks Detected [{current_num}/{total_num}]")
        dialog.geometry("520x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 520) // 2
        y = (dialog.winfo_screenheight() - 280) // 2
        dialog.geometry(f"+{x}+{y}")
        dialog.attributes('-topmost', True)

        msg_frame = tk.Frame(dialog, padx=20, pady=20)
        msg_frame.pack(fill=tk.BOTH, expand=True)

        lbl_file = tk.Label(
            msg_frame,
            text=f"File ({current_num} of {total_num}): {os.path.basename(self.file_path)}",
            font=("Arial", 10, "italic"),
            fg="#555555",
            wraplength=480,
            justify=tk.LEFT
        )
        lbl_file.pack(anchor="w", pady=(0, 6))

        lbl_title = tk.Label(
            msg_frame, 
            text="Bookmarks / Table of Contents Detected!", 
            font=("Arial", 11, "bold"),
            fg="#1b5e20"
        )
        lbl_title.pack(anchor="w", pady=(0, 10))

        file_type_str = "EPUB" if self.file_path.lower().endswith(".epub") else "PDF"
        lbl_desc = tk.Label(
            msg_frame,
            text=(
                f"This {file_type_str} contains {len(self.bookmarks)} chapter/bookmark entries.\n\n"
                "Would you like to split automatically at each bookmarked section, "
                "or proceed manually with page preview and range selectors?"
            ),
            font=("Arial", 10),
            justify=tk.LEFT,
            wraplength=480
        )
        lbl_desc.pack(anchor="w", pady=(0, 20))

        btn_frame = tk.Frame(msg_frame)
        btn_frame.pack(fill=tk.X)

        def on_auto():
            dialog.destroy()
            self.process_automatic_split()

        def on_manual():
            dialog.destroy()
            self.setup_manual_ui()
            self.show_page(0)

        def on_skip():
            dialog.destroy()
            self.process_next_document()

        btn_auto = tk.Button(
            btn_frame, 
            text="Automatically (Bookmarks)", 
            command=on_auto,
            bg="#2e7d32", 
            fg="white", 
            font=("Arial", 10, "bold"),
            padx=8, 
            pady=6
        )
        btn_auto.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        btn_manual = tk.Button(
            btn_frame, 
            text="Manually", 
            command=on_manual,
            bg="#1976d2", 
            fg="white", 
            font=("Arial", 10, "bold"),
            padx=8, 
            pady=6
        )
        btn_manual.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 4))

        btn_skip = tk.Button(
            btn_frame, 
            text="Skip File", 
            command=on_skip,
            bg="#757575", 
            fg="white", 
            font=("Arial", 10, "bold"),
            padx=8, 
            pady=6
        )
        btn_skip.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(4, 0))

        dialog.protocol("WM_DELETE_WINDOW", on_manual)

    def process_automatic_split(self):
        """Splits the active PDF/EPUB based on bookmarks, outputs PDFs, frees memory, and proceeds."""
        base_dir = os.path.dirname(self.file_path)
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]

        # Calculate section ranges based on bookmark start pages
        sections = []
        for i in range(len(self.bookmarks)):
            lvl, title, start_page = self.bookmarks[i]
            if i + 1 < len(self.bookmarks):
                next_start = self.bookmarks[i + 1][2]
                if next_start > start_page:
                    end_page = next_start - 1
                else:
                    end_page = start_page
            else:
                end_page = self.total_pages

            sections.append((title, start_page, end_page))

        try:
            created_count = 0
            # For EPUB files, convert document to in-memory PDF first for clean section slicing
            is_epub = self.file_path.lower().endswith(".epub")
            if is_epub:
                pdf_bytes = self.doc.convert_to_pdf()
                source_pdf = fitz.open("pdf", pdf_bytes)
            else:
                source_pdf = self.doc

            for raw_title, start, end in sections:
                if start > end:
                    continue

                out_doc = fitz.open()
                out_doc.insert_pdf(source_pdf, from_page=start - 1, to_page=end - 1)

                # Sanitize the bookmark title
                clean_title = " ".join(raw_title.split())
                clean_title = re.sub(r'[\\/*?:"<>|]', "", clean_title).strip()
                clean_title = clean_title[:80]

                if clean_title:
                    filename = f"{base_name} - {clean_title}.pdf"
                else:
                    filename = f"{base_name} - Page_{start}-{end}.pdf"

                out_path = os.path.join(base_dir, filename)

                # Resolve duplicate names
                counter = 1
                while os.path.exists(out_path):
                    if clean_title:
                        filename = f"{base_name} - {clean_title}_{counter}.pdf"
                    else:
                        filename = f"{base_name} - Page_{start}-{end}_{counter}.pdf"
                    out_path = os.path.join(base_dir, filename)
                    counter += 1

                out_doc.save(out_path)
                out_doc.close()
                del out_doc
                created_count += 1

            if is_epub:
                source_pdf.close()
                del source_pdf

            messagebox.showinfo(
                "Split Complete",
                f"[{self.current_file_index + 1}/{len(self.doc_files)}] Created {created_count} file(s) for:\n{os.path.basename(self.file_path)}"
            )
        except Exception as e:
            messagebox.showerror(
                "Error Processing Bookmarks", 
                f"An error occurred while splitting {os.path.basename(self.file_path)}:\n{str(e)}"
            )

        # Free memory and advance to next document
        self.process_next_document()

    def setup_manual_ui(self):
        """Constructs the side-by-side preview and range control interface."""
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Left Panel (Preview)
        left_panel = tk.Frame(self.main_frame, bd=2, relief=tk.SUNKEN, bg="gray90")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        self.preview_label = tk.Label(left_panel, bg="gray90")
        self.preview_label.pack(expand=True, pady=10)
        
        # Navigation
        nav_frame = tk.Frame(left_panel, bg="gray90")
        nav_frame.pack(side=tk.BOTTOM, pady=15)
        
        self.btn_prev = tk.Button(nav_frame, text="<< Previous", command=self.prev_page, width=12)
        self.btn_prev.grid(row=0, column=0, padx=20)
        
        self.lbl_page_num = tk.Label(nav_frame, text=f"Page 1 of {self.total_pages}", font=("Arial", 11, "bold"), bg="gray90")
        self.lbl_page_num.grid(row=0, column=1, padx=20)
        
        self.btn_next = tk.Button(nav_frame, text="Next >>", command=self.next_page, width=12)
        self.btn_next.grid(row=0, column=2, padx=20)

        # Right Panel (Controls)
        right_panel = tk.Frame(self.main_frame, width=350)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)
        
        file_ext = os.path.splitext(self.file_path)[1].upper()[1:]
        info_frame = tk.LabelFrame(
            right_panel, 
            text=f"Document Info [{file_ext}] ({self.current_file_index + 1}/{len(self.doc_files)})", 
            font=("Arial", 10, "bold"), 
            padx=10, 
            pady=10
        )
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            info_frame, 
            text=f"File:\n{os.path.basename(self.file_path)}", 
            font=("Arial", 10), 
            justify=tk.LEFT, 
            wraplength=310
        ).pack(anchor="w", pady=5)
        tk.Label(info_frame, text=f"Total Pages: {self.total_pages}", font=("Arial", 10)).pack(anchor="w", pady=5)
        
        action_frame = tk.LabelFrame(right_panel, text="Split Settings", font=("Arial", 10, "bold"), padx=10, pady=15)
        action_frame.pack(fill=tk.X)
        
        tk.Label(action_frame, text="Enter Page Ranges (e.g., 1-5, 8-10):", justify=tk.LEFT).pack(anchor="w", pady=(0, 5))
        
        self.entry_ranges = tk.Entry(action_frame, width=40, font=("Arial", 11))
        self.entry_ranges.pack(fill=tk.X, pady=(0, 15))
        
        self.combine_var = tk.BooleanVar(value=False)
        chk_combine = tk.Checkbutton(
            action_frame, 
            text="Combine all ranges into one file", 
            variable=self.combine_var, 
            justify=tk.LEFT,
            wraplength=300
        )
        chk_combine.pack(anchor="w", pady=(0, 20))
        
        btn_process = tk.Button(
            action_frame, 
            text="Split This Document", 
            command=self.process_manual_document, 
            bg="#2e7d32", 
            fg="white", 
            font=("Arial", 11, "bold"),
            pady=8
        )
        btn_process.pack(fill=tk.X, pady=(0, 8))

        btn_skip = tk.Button(
            action_frame, 
            text="Skip This File", 
            command=self.process_next_document, 
            bg="#757575", 
            fg="white", 
            font=("Arial", 10),
            pady=6
        )
        btn_skip.pack(fill=tk.X)

    def show_page(self, page_index):
        if not self.doc or page_index < 0 or page_index >= self.total_pages:
            return
            
        self.current_preview_page = page_index
        page = self.doc[page_index]
        
        target_height = 700.0
        zoom = target_height / page.rect.height
        if zoom > 2.0:
            zoom = 2.0
            
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        
        # Explicitly release old image reference before creating new one
        self.photo = None
        self.photo = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self.photo)
        
        self.lbl_page_num.config(text=f"Page {page_index + 1} of {self.total_pages}")
        self.btn_prev.config(state=tk.NORMAL if page_index > 0 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if page_index < self.total_pages - 1 else tk.DISABLED)

    def prev_page(self):
        self.show_page(self.current_preview_page - 1)
        
    def next_page(self):
        self.show_page(self.current_preview_page + 1)

    def parse_ranges(self, range_str):
        ranges = []
        parts = [p.strip() for p in range_str.split(',') if p.strip()]
        
        for part in parts:
            if '-' in part:
                bounds = part.split('-')
                if len(bounds) != 2:
                    raise ValueError(f"Invalid range format: '{part}'")
                start = int(bounds[0].strip())
                end = int(bounds[1].strip())
            else:
                start = int(part)
                end = int(part)
                
            if start < 1 or end > self.total_pages or start > end:
                raise ValueError(f"Invalid range or out of bounds: '{part}'. Must be between 1 and {self.total_pages}.")
                
            ranges.append((start, end))
            
        if not ranges:
            raise ValueError("No ranges provided.")
            
        return ranges

    def extract_title_from_page(self, page):
        """Extracts heading or title using the 2.5X font heuristic."""
        text_dict = page.get_text("dict")
        spans = []
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            spans.append({
                                "text": text,
                                "size": span.get("size", 0),
                                "y0": span.get("bbox", (0, 0, 0, 0))[1]
                            })
                            
        if not spans:
            return None
            
        sizes = [round(span["size"] * 2) / 2 for span in spans]
        try:
            body_size = statistics.mode(sizes)
        except statistics.StatisticsError:
            body_size = sizes[0]
            
        total_words = sum(len(span["text"].split()) for span in spans)
        spans.sort(key=lambda x: x["y0"])
        
        candidate_spans = []
        
        if total_words < 20:
            valid_sizes = [s["size"] for s in spans if len(s["text"]) > 1]
            if not valid_sizes:
                valid_sizes = [s["size"] for s in spans]
                
            if valid_sizes:
                max_size = max(valid_sizes)
                candidate_spans = [s for s in spans if s["size"] >= max_size - 1.0]
        else:
            threshold_size = body_size * 2.5
            normal_words_seen = 0
            
            for s in spans:
                if s["size"] >= threshold_size:
                    if normal_words_seen > 20:
                        break
                    candidate_spans.append(s)
                else:
                    normal_words_seen += len(s["text"].split())
            
        if not candidate_spans:
            return None
            
        candidate_spans.sort(key=lambda x: x["y0"])
        top_y = candidate_spans[0]["y0"]
        current_y = top_y
        
        title_parts = []
        for s in candidate_spans:
            if s["y0"] - current_y < s["size"] * 2.5:
                title_parts.append(s["text"])
                if s["y0"] > current_y:
                    current_y = s["y0"]
            else:
                break
                
        potential_title = " ".join(title_parts)
        clean_title = " ".join(potential_title.split())
        clean_title = re.sub(r'[\\/*?:"<>|]', "", clean_title)
        clean_title = clean_title[:60].strip()
        
        if len(clean_title) < 2:
            return None
            
        return clean_title

    def process_manual_document(self):
        """Splits the active PDF/EPUB based on manual ranges, cleans up, and advances."""
        input_str = self.entry_ranges.get()
        try:
            ranges = self.parse_ranges(input_str)
        except ValueError as ve:
            messagebox.showerror("Invalid Input", str(ve))
            return
            
        combine = self.combine_var.get()
        base_dir = os.path.dirname(self.file_path)
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        
        try:
            # Prepare source PDF document (converting EPUB in memory if needed)
            is_epub = self.file_path.lower().endswith(".epub")
            if is_epub:
                pdf_bytes = self.doc.convert_to_pdf()
                source_pdf = fitz.open("pdf", pdf_bytes)
            else:
                source_pdf = self.doc

            if combine:
                out_doc = fitz.open()
                for start, end in ranges:
                    out_doc.insert_pdf(source_pdf, from_page=start-1, to_page=end-1)
                
                first_page = source_pdf[ranges[0][0]-1]
                title = self.extract_title_from_page(first_page)
                
                if title:
                    filename = f"{base_name}_combined_{title}.pdf"
                else:
                    filename = f"{base_name}_combined.pdf"
                    
                out_path = os.path.join(base_dir, filename)
                
                counter = 1
                while os.path.exists(out_path):
                    if title:
                        filename = f"{base_name}_combined_{title}_{counter}.pdf"
                    else:
                        filename = f"{base_name}_combined_{counter}.pdf"
                    out_path = os.path.join(base_dir, filename)
                    counter += 1
                
                out_doc.save(out_path)
                out_doc.close()
                del out_doc
                messagebox.showinfo("Success", f"Successfully created combined file for:\n{os.path.basename(self.file_path)}")
            else:
                created_count = 0
                for start, end in ranges:
                    out_doc = fitz.open()
                    out_doc.insert_pdf(source_pdf, from_page=start-1, to_page=end-1)
                    
                    suffix = f"{start}-{end}" if start != end else f"{start}"
                    first_page = source_pdf[start-1]
                    title = self.extract_title_from_page(first_page)
                    
                    if title:
                        filename = f"{base_name}_{title}.pdf"
                    else:
                        filename = f"{base_name}_{suffix}.pdf"
                        
                    out_path = os.path.join(base_dir, filename)
                    
                    counter = 1
                    while os.path.exists(out_path):
                        if title:
                            filename = f"{base_name}_{title}_{counter}.pdf"
                        else:
                            filename = f"{base_name}_{suffix}_{counter}.pdf"
                        out_path = os.path.join(base_dir, filename)
                        counter += 1
                        
                    out_doc.save(out_path)
                    out_doc.close()
                    del out_doc
                    created_count += 1
                
                messagebox.showinfo("Success", f"Created {created_count} file(s) for:\n{os.path.basename(self.file_path)}")
                
            if is_epub:
                source_pdf.close()
                del source_pdf

            # Free memory and advance to next document
            self.process_next_document()
            
        except Exception as e:
            messagebox.showerror("Error Processing Document", f"An error occurred: {str(e)}")

    def on_closing(self):
        """Cleanly closes resources and triggers garbage collection before exit."""
        self.free_current_document_memory()
        self.root.destroy()
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = BulkDocumentSplitterApp(root)
    root.mainloop()