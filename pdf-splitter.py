# ==========================================
# PDF Splitter
# Version: 1.7
# Citation: Pundir, V. (2026, September 12). PDF Splitter Version (1.7). Retrieved from https://github.com/accidentalscholar/pdf-splitter. 
# Citation: RIS and BibTeX files included for referencing software.
# Tested in: Python 3.10.9 64 bit packaged by Anaconda, Inc.
# Reporsitory: https://github.com/accidentalscholar/pdf-splitter
# Provided under: GNU AFFERO GENERAL PUBLIC LICENSE (see accompanying license file)
# ==========================================

import sys
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
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
        pass # Ignore errors if unable to read the file

# Check and install PyMuPDF and Pillow automatically to the user directory
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
        tk.Tk().withdraw() # Hide root window for the error box
        messagebox.showerror(
            "Missing Dependencies",
            "Failed to automatically install required libraries.\n\n"
            "Please run the following commands in your Anaconda prompt:\n"
            "pip install PyMuPDF\n"
            "pip install Pillow"
        )
        sys.exit(1)

class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Splitter v1.7")
        # Widen the window to comfortably fit a side-by-side layout
        self.root.geometry("1100x850")
        
        # Handle Spyder close behavior cleanly so the kernel doesn't hang
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Briefly bring window to top, then allow standard layering behavior
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        
        self.pdf_path = None
        self.pdf_doc = None
        self.total_pages = 0
        self.current_preview_page = 0
        
        self.select_pdf()

    def select_pdf(self):
        # Temporarily ensure the dialog stays on top over other applications
        self.root.attributes('-topmost', True)
        self.pdf_path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF Files", "*.pdf")]
        )
        self.root.attributes('-topmost', False)
        
        # If user cancels the file dialog, exit the app
        if not self.pdf_path:
            self.root.destroy()
            return
            
        self.pdf_doc = fitz.open(self.pdf_path)
        self.total_pages = len(self.pdf_doc)
        
        if self.total_pages == 0:
            messagebox.showerror("Error", "The selected PDF has no pages.")
            self.root.destroy()
            return
            
        self.setup_ui()
        self.show_page(0) # Load the first page into preview

    def setup_ui(self):
        # Main container for side-by-side layout
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ================= LEFT PANEL (Preview) =================
        left_panel = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN, bg="gray90")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Preview Image Area
        self.preview_label = tk.Label(left_panel, bg="gray90")
        self.preview_label.pack(expand=True, pady=10)
        
        # Pagination Controls
        nav_frame = tk.Frame(left_panel, bg="gray90")
        nav_frame.pack(side=tk.BOTTOM, pady=15)
        
        self.btn_prev = tk.Button(nav_frame, text="<< Previous", command=self.prev_page, width=12)
        self.btn_prev.grid(row=0, column=0, padx=20)
        
        self.lbl_page_num = tk.Label(nav_frame, text=f"Page 1 of {self.total_pages}", font=("Arial", 11, "bold"), bg="gray90")
        self.lbl_page_num.grid(row=0, column=1, padx=20)
        
        self.btn_next = tk.Button(nav_frame, text="Next >>", command=self.next_page, width=12)
        self.btn_next.grid(row=0, column=2, padx=20)

        # ================= RIGHT PANEL (Controls) =================
        right_panel = tk.Frame(main_frame, width=350)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False) # Keep width fixed so it doesn't shift
        
        # Top right: Document Info
        info_frame = tk.LabelFrame(right_panel, text="Document Information", font=("Arial", 10, "bold"), padx=10, pady=10)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Wraplength ensures long filenames don't break the layout
        tk.Label(info_frame, text=f"File:\n{os.path.basename(self.pdf_path)}", font=("Arial", 10), justify=tk.LEFT, wraplength=310).pack(anchor="w", pady=5)
        tk.Label(info_frame, text=f"Total Pages: {self.total_pages}", font=("Arial", 10)).pack(anchor="w", pady=5)
        
        # Middle right: Inputs and Actions
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
        chk_combine.pack(anchor="w", pady=(0, 25))
        
        btn_process = tk.Button(
            action_frame, 
            text="Split PDF", 
            command=self.process_pdf, 
            bg="#2e7d32", 
            fg="white", 
            font=("Arial", 12, "bold"),
            pady=8
        )
        btn_process.pack(fill=tk.X)

    def show_page(self, page_index):
        if page_index < 0 or page_index >= self.total_pages:
            return
            
        self.current_preview_page = page_index
        page = self.pdf_doc[page_index]
        
        # Dynamically calculate zoom to make it large enough for the left panel 
        # (Assuming ~700 pixels available height for the preview area)
        target_height = 700.0
        zoom = target_height / page.rect.height
        
        # Prevent it from zooming too much on tiny pages
        if zoom > 2.0:
            zoom = 2.0
            
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        
        self.photo = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self.photo)
        
        self.lbl_page_num.config(text=f"Page {page_index + 1} of {self.total_pages}")
        
        # Update button states depending on bounds
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
        """Extracts heading or title based on font size contrast."""
        text_dict = page.get_text("dict")
        spans = []
        
        # Gather all text spans with their text, font size, and vertical position
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            spans.append({
                                "text": text,
                                "size": span.get("size", 0),
                                "y0": span.get("bbox", (0,0,0,0))[1]
                            })
                            
        if not spans:
            return None
            
        # Calculate the most common font size (body text size)
        sizes = [round(span["size"] * 2) / 2 for span in spans]
        try:
            body_size = statistics.mode(sizes)
        except statistics.StatisticsError:
            body_size = sizes[0]
            
        total_words = sum(len(span["text"].split()) for span in spans)
        
        # Sort all spans top-to-bottom for chronological reading order
        spans.sort(key=lambda x: x["y0"])
        
        candidate_spans = []
        
        if total_words < 20:
            # Sparse page (e.g., cover page). Focus on the absolute largest text.
            # Try to filter out valid sizes that are just 1 character (dropcaps/artifacts)
            valid_sizes = [s["size"] for s in spans if len(s["text"]) > 1]
            if not valid_sizes:
                valid_sizes = [s["size"] for s in spans] # Fallback
                
            if valid_sizes:
                max_size = max(valid_sizes)
                candidate_spans = [s for s in spans if s["size"] >= max_size - 1.0]
        else:
            # Dense page. Candidate must be at least 2.5X the normal text size.
            threshold_size = body_size * 2.5
            normal_words_seen = 0
            
            for s in spans:
                if s["size"] >= threshold_size:
                    # If we've already seen a significant amount of normal text (e.g., a full paragraph),
                    # this large text is likely in the middle/bottom (e.g., pull quote). Reject it.
                    if normal_words_seen > 20:
                        break
                    candidate_spans.append(s)
                else:
                    normal_words_seen += len(s["text"].split())
            
        if not candidate_spans:
            return None
            
        # Sort candidates top-to-bottom
        candidate_spans.sort(key=lambda x: x["y0"])
        
        # Grab the topmost candidate's y0
        top_y = candidate_spans[0]["y0"]
        current_y = top_y
        
        # Collect spans that are part of this topmost prominent heading group
        title_parts = []
        for s in candidate_spans:
            # Group lines that are vertically close to each other
            if s["y0"] - current_y < s["size"] * 2.5:
                title_parts.append(s["text"])
                # Update current_y only if it's a new line, to prevent diagonal walking
                if s["y0"] > current_y:
                    current_y = s["y0"]
            else:
                break
                
        potential_title = " ".join(title_parts)
        
        # Sanitize string for use as a filename
        clean_title = " ".join(potential_title.split())
        clean_title = re.sub(r'[\\/*?:"<>|]', "", clean_title)
        clean_title = clean_title[:60].strip() # Truncate to reasonable length
        
        # Prevent isolated dropcaps or blank strings from becoming the title
        if len(clean_title) < 2:
            return None
            
        return clean_title

    def process_pdf(self):
        """Handles the splitting logic based on parsed ranges and user preferences"""
        input_str = self.entry_ranges.get()
        try:
            ranges = self.parse_ranges(input_str)
        except ValueError as ve:
            messagebox.showerror("Invalid Input", str(ve))
            return
            
        combine = self.combine_var.get()
        base_dir = os.path.dirname(self.pdf_path)
        base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        
        try:
            if combine:
                # Output all ranges into a single PDF
                out_doc = fitz.open()
                for start, end in ranges:
                    out_doc.insert_pdf(self.pdf_doc, from_page=start-1, to_page=end-1)
                
                # Check for a title on the first page of the first range
                first_page = self.pdf_doc[ranges[0][0]-1]
                title = self.extract_title_from_page(first_page)
                
                if title:
                    filename = f"{base_name}_combined_{title}.pdf"
                else:
                    filename = f"{base_name}_combined.pdf"
                    
                out_path = os.path.join(base_dir, filename)
                
                # Handle potential duplicate filenames
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
                messagebox.showinfo("Success", "Successfully combined requested ranges into a single file in the source directory.")
            else:
                # Output each range to a separate PDF
                created_count = 0
                for start, end in ranges:
                    out_doc = fitz.open()
                    out_doc.insert_pdf(self.pdf_doc, from_page=start-1, to_page=end-1)
                    
                    suffix = f"{start}-{end}" if start != end else f"{start}"
                    
                    # Try to extract title from the first page of the range
                    first_page = self.pdf_doc[start-1]
                    title = self.extract_title_from_page(first_page)
                    
                    if title:
                        filename = f"{base_name}_{title}.pdf"
                    else:
                        filename = f"{base_name}_{suffix}.pdf"
                        
                    out_path = os.path.join(base_dir, filename)
                    
                    # Handle potential duplicate filenames
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
                    created_count += 1
                
                messagebox.showinfo("Success", f"Successfully created {created_count} file(s) in the source directory.")
        except Exception as e:
            messagebox.showerror("Error Processing PDF", f"An error occurred: {str(e)}")

    def on_closing(self):
        """Cleanly close resources before killing the application."""
        if self.pdf_doc:
            self.pdf_doc.close()
        self.root.destroy()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()