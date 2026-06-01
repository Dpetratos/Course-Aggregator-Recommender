# Course Aggregator Recommender

Desktop Python application for collecting course data from multiple sources, normalizing it, storing it in CSV, visualizing it with Matplotlib, and recommending the best matches through a composite score.

## Overview

This project is a Tkinter-based course discovery tool built for a Python lab assignment. It aggregates data from APIs and web scraping sources, cleans and normalizes the records, and presents them through a GUI with filters, charts, and recommendations.

## Features

- Collects course data from APIs and web scraping sources.
- Normalizes category, difficulty, and language values.
- Stores data in CSV append mode without duplicating existing records.
- Provides a Tkinter GUI with filters, a results table, and automatic refresh.
- Generates three visualizations with Matplotlib.
- Produces top-3 course recommendations based on score.
- Includes a fallback dataset so the app still works offline.
- Uses a cleaner dark-themed interface for a more polished presentation.

## Demo Screenshots

Add a few screenshots here when you export them from the app:

- Main dashboard
- Filters applied
- Charts window
- Top 3 recommendations

## Project Structure

- `1108351_1112124_1112128/project1.py` - main application.
- `courses.csv` - course dataset.
- `requirements.txt` - Python dependencies.
- `report_assets/` - generated report assets.
- `report_render/`, `report_render_preview/`, `report_render_word/` - generated output folders.

## Suggested GitHub Topics

`python`, `tkinter`, `data-aggregation`, `web-scraping`, `gui`, `matplotlib`, `pandas`, `recommendation-system`, `csv`, `course-recommender`

## Requirements

- Python 3.10+ recommended.
- Required packages from `requirements.txt`.

## Run

From the `python` folder:

```powershell
python .\1108351_1112124_1112128\project1.py
```

If you use a virtual environment, activate it first.

## Team

- Δημήτρης Πετράτος
- Χρήστος Αυγερινόπουλος
- Ιωάννης Γιανακόπουλος

## Notes

- The app depends on external websites, so some sources may change over time.
- If online collection fails, the fallback dataset keeps the GUI functional.
- Replace the team information in the source file with your final submission details if needed.
- If you want the repository to look even more complete, add a short GIF or a couple of screenshots in this README.
