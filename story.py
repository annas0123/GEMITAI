import pandas as pd
import time
import base64
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from google import genai
from google.genai import types

def generate_prompt(full_story, current_sentence):
    """Generate a prompt using Gemini API"""
    client = genai.Client(
        vertexai=True,
        project="",
        location="",
    )

    model = "gemini-2.0-flash"
    prompt = f"[Full_story]\n{full_story}\n[Sentence i]\n{current_sentence}\nGenerate a prompt text of this sentence"
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    response_text = ""
    try:
        response_stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        for chunk in response_stream:
            response_text += chunk.text if chunk.text else ""
    except Exception as e:
        # Make sure to fully consume the stream even on error
        try:
            # If response_stream exists, exhaust it to avoid "Response not read" errors
            if 'response_stream' in locals():
                for _ in response_stream:
                    pass
        except Exception as exhaust_error:
            print(f"Error exhausting stream: {exhaust_error}")
        return f"Error: {str(e)}"
    
    return response_text

def process_excel(file_path, progress_var=None, status_var=None):
    """Process the Excel file and generate prompts for each sentence"""
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Ensure the first column exists
        if df.shape[1] < 1:
            return "Error: Excel file must have at least one column"
        
        # Get the sentences from the first column
        sentences = df.iloc[:, 0].tolist()
        
        # Create a new column for generated prompts if it doesn't exist
        if df.shape[1] < 2:
            df["Generated Prompt"] = ""
        
        total_sentences = len(sentences)
        
        # Update status if available
        if status_var:
            status_var.set("Processing sentences...")
        
        # Process each sentence
        for i, sentence in enumerate(sentences):
            # Skip empty sentences
            if pd.isna(sentence) or sentence.strip() == "":
                continue
                
            # Create the full story from processed sentences
            if i == 0:
                full_story = ""
            else:
                full_story = "\n".join(sentences[:i])
            
            # Generate prompt
            generated_prompt = generate_prompt(full_story, sentence)
            
            # Store the result
            df.iloc[i, 1] = generated_prompt
            
            # Update progress if available
            if progress_var:
                progress_var.set((i + 1) / total_sentences * 100)
            
            # Update status if available
            if status_var:
                status_var.set(f"Processed {i+1}/{total_sentences} sentences")
            
            # Wait 4 seconds between API calls (except for the last one)
            if i < total_sentences - 1:
                time.sleep(4)
        
        # Save the results
        output_file = file_path.rsplit(".", 1)[0] + "_with_prompts.xlsx"
        df.to_excel(output_file, index=False)
        
        return f"Processing completed. Results saved to {output_file}"
    
    except Exception as e:
        return f"Error: {str(e)}"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Story Prompt Creator")
        self.root.geometry("600x400")
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection
        ttk.Label(main_frame, text="Select Excel file:").pack(anchor=tk.W, pady=(0, 5))
        
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Process button
        ttk.Button(main_frame, text="Process File", command=self.process_file).pack(pady=(0, 20))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100).pack(fill=tk.X, pady=(0, 10))
        
        # Status
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(main_frame, textvariable=self.status_var).pack(anchor=tk.W)
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def process_file(self):
        file_path = self.file_path_var.get()
        
        if not file_path:
            messagebox.showerror("Error", "Please select an Excel file")
            return
        
        # Reset progress
        self.progress_var.set(0)
        self.status_var.set("Starting...")
        
        # Run processing in a separate thread
        threading.Thread(
            target=self.process_thread, 
            args=(file_path,), 
            daemon=True
        ).start()
    
    def process_thread(self, file_path):
        result = process_excel(file_path, self.progress_var, self.status_var)
        
        # Update UI from main thread
        self.root.after(0, lambda: self.process_complete(result))
    
    def process_complete(self, result):
        self.status_var.set(result)
        
        if result.startswith("Error"):
            messagebox.showerror("Error", result)
        else:
            messagebox.showinfo("Success", result)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop() 