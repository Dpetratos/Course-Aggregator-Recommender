# Course Aggregator Project

Desktop Python application for collecting course data from multiple sources, normalizing it, storing it in CSV, visualizing it with Matplotlib, and recommending the best matches through a composite score.

## Features

- Collects course data from APIs and web scraping sources.
- Normalizes category, difficulty, and language values.
- Stores data in CSV append mode without duplicating existing records.
- Provides a Tkinter GUI with filters, a results table, and automatic refresh.
- Generates three visualizations with Matplotlib.
- Produces top-3 course recommendations based on score.
- Includes a fallback dataset so the app still works offline.

## Project Structure

- `1108351_1112124_1112128/project1.py` - main application.
- `courses.csv` - course dataset.
- `requirements.txt` - Python dependencies.

## Requirements

- Python 3.10+ recommended.
- Required packages from `requirements.txt`.

## Run

From the `python` folder:

```powershell
python .\1108351_1112124_1112128\project1.py
```

If you use a virtual environment, activate it first.

## Notes

- The app depends on external websites, so some sources may change over time.
- If online collection fails, the fallback dataset keeps the GUI functional.
- Replace the team information in the source file with your final submission details if needed.
