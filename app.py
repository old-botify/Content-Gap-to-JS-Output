from flask import Flask, request, render_template, send_file, jsonify
import pandas as pd
import json
from pathlib import Path
import re
from werkzeug.utils import secure_filename
import os
import time
import glob
import logging
import shutil

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configure folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')

# Create necessary folders
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Global variable to track processing progress
processing_progress = 0

def clean_directory(directory):
    """Clean all files in a directory"""
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f"Error removing {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning directory {directory}: {e}")

def allowed_file(filename):
    """Check if file extension is allowed"""
    return filename.lower().endswith(('.xlsx', '.csv'))

def is_branded(keyword, brand_terms):
    """Check if keyword contains any brand terms"""
    keyword = keyword.lower()
    expanded_terms = set()
    for term in brand_terms:
        term = term.lower().strip()
        if not term:
            continue
        expanded_terms.add(term)
        expanded_terms.add(f"{term}'s")
        expanded_terms.add(term.replace("'", ""))
        expanded_terms.add(f" {term} ")
    
    return any(term in f" {keyword} " for term in expanded_terms)

def read_file(file_path):
    """Read either CSV or XLSX file"""
    if file_path.lower().endswith('.csv'):
        return pd.read_csv(file_path)
    else:
        return pd.read_excel(file_path, engine='openpyxl')

def save_json_file(data, filename, minified=False):
    """Save JSON data to a file, with error checking"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if minified:
                json.dump(data, f, separators=(',', ':'))
            else:
                json.dump(data, f, indent=2)
        
        # Verify file was written correctly
        if not os.path.exists(filepath):
            raise Exception(f"File {filepath} was not created")
        
        file_size = os.path.getsize(filepath)
        logger.debug(f"Successfully wrote {filename} ({file_size} bytes)")
        
        # Verify file can be read back
        with open(filepath, 'r', encoding='utf-8') as f:
            _ = json.load(f)
            
        return filepath
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        raise

def process_excel(file_path, brand_terms):
    """Process Excel/CSV file and check for branded keywords"""
    global processing_progress
    
    try:
        processing_progress = 5
        df = read_file(file_path)
        processing_progress = 20
        
        logger.debug(f"DataFrame Info:\n{df.info()}")
        logger.debug(f"First few rows:\n{df.head()}")
        
        # Find all competitor columns that end in either .com or .net
        competitor_columns = [col for col in df.columns if str(col).lower().endswith(('.com', '.net','.org','.io','.gov'))]
        logger.debug(f"Found competitor columns: {competitor_columns}")
        
        keyword_data = []
        total_rows = len(df)
        
        for idx, row in df.iterrows():
            try:
                processing_progress = 20 + int((idx / total_rows) * 70)
                
                competitors = []
                for comp in competitor_columns:
                    if pd.notna(row[comp]):
                        try:
                            rank = float(row[comp])
                            competitors.append({
                                "name": comp,
                                "rank": int(rank)
                            })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error processing competitor {comp} for row {idx}: {e}")
                            continue
                
                search_volume = 0
                if 'Search Volume' in row:
                    try:
                        if pd.notna(row['Search Volume']):
                            sv_str = str(row['Search Volume']).replace(',', '')
                            search_volume = int(float(sv_str))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing search volume for row {idx}: {e}")
                
                keyword = str(row.get('Keyword', '')).lower().strip()
                if not keyword:
                    logger.warning(f"Skipping row {idx}: Empty keyword")
                    continue
                
                category = str(row.get('Keyword Group (Experimental)', 'Other'))
                if pd.isna(category) or not category.strip():
                    category = 'Other'
                
                keyword_entry = {
                    "keyword": keyword,
                    "category": category,
                    "searchVolume": search_volume,
                    "isBranded": is_branded(keyword, brand_terms),
                    "competitors": sorted(competitors, key=lambda x: x['rank'])
                }
                
                if idx < 5 or len(competitors) > 0:
                    logger.debug(f"Processed keyword entry: {json.dumps(keyword_entry, indent=2)}")
                
                keyword_data.append(keyword_entry)
                
            except Exception as e:
                logger.error(f"Error processing row {idx + 2}: {str(e)}", exc_info=True)
                continue
        
        processing_progress = 100
        return keyword_data
        
    except Exception as e:
        processing_progress = 0
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise

@app.route('/progress')
def get_progress():
    """Get current processing progress"""
    return jsonify({'progress': processing_progress})

@app.route('/clean-files', methods=['POST'])
def clean_files():
    """Clean all files in upload and output directories"""
    try:
        clean_directory(app.config['UPLOAD_FOLDER'])
        clean_directory(app.config['OUTPUT_FOLDER'])
        return jsonify({'success': True, 'message': 'All files cleaned successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download-js')
def download_js():
    """Download the processed JavaScript file"""
    try:
        # Try to find both versions
        js_file = os.path.join(app.config['OUTPUT_FOLDER'], 'keyword_data.js')
        js_file_min = os.path.join(app.config['OUTPUT_FOLDER'], 'keyword_data.min.js')
        
        if os.path.exists(js_file):
            return send_file(js_file, as_attachment=True, download_name='keyword_data.js')
        elif os.path.exists(js_file_min):
            return send_file(js_file_min, as_attachment=True, download_name='keyword_data.js')
        else:
            return jsonify({'success': False, 'error': 'No processed file found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Handle file upload and processing"""
    global processing_progress
    
    if request.method == 'POST':
        try:
            processing_progress = 0
            
            if 'file' not in request.files:
                return render_template('upload.html', error='No file uploaded')
            
            file = request.files['file']
            brand_terms = request.form.get('brand_terms', '').split(',')
            
            if file.filename == '':
                return render_template('upload.html', error='No file selected')
            
            if not allowed_file(file.filename):
                return render_template('upload.html', error='Only .xlsx and .csv files are allowed')
            
            # Clean output directory before processing
            clean_directory(app.config['OUTPUT_FOLDER'])
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            
            try:
                keyword_data = process_excel(filepath, brand_terms)
                
                # Save both versions with proper JS export
                js_output_readable = "export const keywordData = " + json.dumps(keyword_data, indent=2) + ";"
                js_output_minified = "export const keywordData=" + json.dumps(keyword_data, separators=(',', ':')) + ";"
                
                # Save both versions with error checking
                output_path_readable = os.path.join(app.config['OUTPUT_FOLDER'], 'keyword_data.js')
                output_path_min = os.path.join(app.config['OUTPUT_FOLDER'], 'keyword_data.min.js')
                
                with open(output_path_readable, 'w', encoding='utf-8') as f:
                    f.write(js_output_readable)
                
                with open(output_path_min, 'w', encoding='utf-8') as f:
                    f.write(js_output_minified)
                
                # Verify files were created
                if not (os.path.exists(output_path_readable) and os.path.exists(output_path_min)):
                    raise Exception("Output files were not created properly")
                
                # Log file sizes
                readable_size = os.path.getsize(output_path_readable)
                min_size = os.path.getsize(output_path_min)
                logger.debug(f"Readable file size: {readable_size} bytes")
                logger.debug(f"Minified file size: {min_size} bytes")
                
                # Clean up upload
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                # Return the readable version
                return send_file(output_path_readable, as_attachment=True, download_name='keyword_data.js')
                
            except Exception as e:
                logger.error("Error processing file", exc_info=True)
                if os.path.exists(filepath):
                    os.remove(filepath)
                return render_template('upload.html', error=f'Error processing file: {str(e)}')
            
        except Exception as e:
            logger.error("Error uploading file", exc_info=True)
            return render_template('upload.html', error=f'Error uploading file: {str(e)}')
            
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)