# Keyword Processor

This Flask application takes the Content Gap CSV/XLSX overview with all of the rankings by competitor and adds in branded information and exports it to a JS file for review in the Vercel tool.

## Features

- Upload and process Excel files containing keyword data
- Detect branded keywords based on user-defined terms
- Real-time progress tracking
- File management system
- Dark theme UI with purple accents
- Support for large files (up to 100MB)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd keyword-processor
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- On Windows:
  ```bash
  venv\Scripts\activate
  ```
- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Upload an Excel file and enter brand terms:
   - Select an .xlsx file containing keyword data
   - Enter brand terms separated by commas
   - Click "Process File" to start processing

4. Features available:
   - Progress tracking during processing
   - Download processed JavaScript file
   - Clean temporary files
   - Redownload previously processed file

## Input File Format

The Excel file should contain the following columns:
- Keyword: The keyword to process
- Search Volume: Monthly search volume
- Competitor columns (ending in .com): Competitor rankings
- Keyword Group (Experimental): Category information

## Output Format

The processed data will be saved as a JavaScript file with the following structure:
```javascript
export const keywordData = [
    {
        "keyword": "example keyword",
        "category": "Category",
        "searchVolume": 1000,
        "isBranded": true,
        "competitors": [
            {
                "name": "competitor1.com",
                "rank": 10
            }
        ]
    }
];
```

## Project Structure

```
keyword-processor/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── .gitignore            # Git ignore file
├── uploads/              # Temporary file storage
└── templates/
    └── upload.html       # HTML template
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.