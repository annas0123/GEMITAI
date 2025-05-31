from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
import pandas as pd
from werkzeug.utils import secure_filename
from app import main

app = Flask(__name__)
app.secret_key = "story_prompt_creator"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        output_filename = f"results_{filename}"
        output_path = os.path.join(app.config['RESULT_FOLDER'], output_filename)
        
        result_path, error = main(file_path, output_path)
        
        if error:
            flash(f"Error: {error}")
            return redirect(url_for('index'))
        
        flash("Processing complete! Download your results.")
        return redirect(url_for('download_file', filename=output_filename))
    
    flash('Please upload an Excel file (.xlsx or .xls)')
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['RESULT_FOLDER'], filename),
                     as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) 