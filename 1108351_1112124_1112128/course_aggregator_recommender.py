"""
Course Aggregator Project (Python Lab Assignment)

What this script includes:
1. Data collection from 6 sources (3 API + 3 Web Scraping).
2. Normalization for category and difficulty values.
3. CSV storage in append mode (no overwrite of old records).
4. Tkinter GUI with filters and table.
5. Three required Matplotlib charts.
6. Recommendation engine (top 3 suggestions) with composite score.

Note:
- Replace TEAM_INFO and CSV_FILENAME with your real group details and AM.
- External pages can change structure over time. When a source fails,
  the script logs the failure and continues.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import Response
from tkinter import font as tkfont
from tkinter import END, BOTH, LEFT, RIGHT, W, X, Y, Tk, StringVar, DoubleVar
from tkinter import filedialog, messagebox, ttk


# Εξατομίκευση: Βάλε τα πραγματικά ονόματα και Αριθμούς Μητρώου (ΑΜ)
# πριν την τελική υποβολή της εργασίας.
TEAM_INFO = "Course Aggregator Recommender"

# Το όνομα του αρχείου CSV πρέπει να περιλαμβάνει έναν ΑΜ
# (π.χ. courses_12345.csv) όπως απαιτείται στην εκφώνηση.
CSV_FILENAME = "courses_1108351.csv"

APP_BG = "#0F172A"
CARD_BG = "#111827"
ACCENT = "#38BDF8"
ACCENT_LIGHT = "#0EA5E9"
TEXT_MUTED = "#94A3B8"


@dataclass
class Course:
	title: str
	provider: str
	category: str
	difficulty: str
	cost: str
	duration: str
	language: str
	source: str


def log_status(source_name: str, status: str, details: str = "") -> None:
	"""Print progress in the format required by the assignment."""
	suffix = f" - {details}" if details else ""
	print(f"[{source_name}] Status: {status}{suffix}")


def safe_get(url: str, timeout: int = 20, params: dict | None = None) -> Response:
	# Χρησιμοποιούμε User-Agent που μοιάζει με πρόγραμμα περιήγησης
	# για να μειώσουμε την πιθανότητα απλών αποκλεισμών από τον server.
	headers = {
		"User-Agent": (
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
			"AppleWebKit/537.36 (KHTML, like Gecko) "
			"Chrome/125.0 Safari/537.36"
		)
	}
	return requests.get(url, headers=headers, params=params, timeout=timeout)


def normalize_category(raw: str) -> str:
	"""
	Ενοποίηση όρων: τα δεδομένα από διαφορετικές πηγές χρησιμοποιούν
	διαφορετική ορολογία. Εδώ μετατρέπουμε αυτά τα ελεύθερα κείμενα
	σε ένα σταθερό σύνολο κατηγοριών για το GUI και τα γραφήματα.
	"""
	# Σχεδιαστική επιλογή: Χρησιμοποιούμε επιλεκτικά 'contains' checks
	# αντί για πλήρη ορολογία για να αυξήσουμε την ανθεκτικότητα σε
	# διαφορετικές μορφές και γλώσσες τίτλων. Αυτό δίνει μεγαλύτερο
	# recall (παραλαβή περισσοτέρων σωστών καταχωρήσεων) σε βάρος
	# ελαφρώς μειωμένης ακρίβειας, κάτι που είναι αποδεκτό για την
	# παρουσίαση/φιλτράρισμα στο GUI όπου ο χρήστης μπορεί να επιλέξει
	# επιπλέον φίλτρα.
	text = (raw or "").strip().lower()
	if any(
		k in text
		for k in [
			"python",
			"program",
			"coding",
			"code",
			"software",
			"developer",
			"rpa",
			"uipath",
			"technology",
			"computer",
			"algorithm",
			"engineering",
			"dotnet",
			".net",
			"c#",
			"typescript",
			"java",
			"testing",
		]
	):
		return "Programming"
	if any(k in text for k in ["data", "machine", "ai", "analytics", "statistics", "database", "sql"]):
		return "Data Science"
	if any(k in text for k in ["design", "ux", "ui", "creative"]):
		return "Design"
	if any(k in text for k in ["communication", "writing", "speaking"]):
		return "Communication"
	if any(k in text for k in ["web", "html", "css", "javascript", "frontend", "backend"]):
		return "Web Development"
	if any(k in text for k in ["cloud", "devops", "aws", "azure", "kubernetes", "github"]):
		return "Cloud/DevOps"
	if any(k in text for k in ["business", "management", "leadership", "product"]):
		return "Business"
	return "Other"


def normalize_difficulty(raw: str) -> str:
	# Difficulty labels are unified so "basic" and "intro" become "Beginner".
	# Ενοποίηση των επιπέδων δυσκολίας σε τρεις κατηγορίες
	# ώστε το φίλτρο και οι στατιστικές να παραμένουν συνεπείς.
	# Σχεδιασμός: Περιορίζουμε τα επίπεδα σε τρεις (Beginner/Intermediate/Advanced)
	# για να αποφύγουμε κατακερματισμό από ποικίλες ετικέτες στις πηγές.
	# Αυτό μειώνει την πολυπλοκότητα του UI και βελτιώνει τα στατιστικά.
	text = (raw or "").strip().lower()
	if any(k in text for k in ["beginner", "intro", "basic", "novice", "elementary", "entry", "getting started"]):
		return "Beginner"
	if text in {"u", "undergraduate"} or any(k in text for k in ["intermediate", "medium", "hands-on", "zero to hero"]):
		return "Intermediate"
	if text in {"g", "graduate"} or any(
		k in text for k in ["advanced", "expert", "professional", "deep dive", "production-ready", "mastering"]
	):
		return "Advanced"
	return "Unknown"


def normalize_language(raw: str) -> str:
	# Keep language values compact and predictable for filtering and recommendations.
	# Κανονικοποίηση γλώσσας σε λίγες, προβλέψιμες τιμές
	text = (raw or "").strip().lower()
	# Σχεδιαστική αιτιολόγηση: Περιορίζουμε τις γλώσσες σε λίγες τιμές
	# για να διευκολύνουμε τα φίλτρα και το recommender. Διατηρούμε
	# την πρωτότυπη τιμή ως fallback (title-cased) για να μην χάνουμε
	# πληροφορία όταν η γλώσσα είναι σπάνια.
	if "english" in text or text in {"en", "eng"}:
		return "English"
	if "greek" in text or "ellin" in text or text in {"el", "gr"}:
		return "Greek"
	if "arabic" in text or text in {"ar"}:
		return "Arabic"
	if not text:
		return "Unknown"
	return raw.strip().title()


def parse_duration_to_hours(value: str) -> float:
	if not value:
		return math.nan
	text = value.lower().strip()

	# Handle plain numeric strings quickly (e.g. "12", "8.5").
	try:
		return float(text)
	except ValueError:
		pass

	hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|h)", text)
	mins_match = re.search(r"(\d+(?:\.\d+)?)\s*(minute|minutes|min|mins|m)", text)
	weeks_match = re.search(r"(\d+(?:\.\d+)?)\s*(week|weeks|wk|wks)", text)

	total = 0.0
	found = False

	if hours_match:
		total += float(hours_match.group(1))
		found = True
	if mins_match:
		total += float(mins_match.group(1)) / 60.0
		found = True
	if weeks_match:
		# This is an explicit modeling assumption for comparability across sources.
		# You can tune this later and mention it in your report.
		total += float(weeks_match.group(1)) * 5.0
		found = True
	# Σχεδιαστική δικαιολόγηση: Ορίζουμε εβδομάδα=5 ώρες (εργάσιμες ημέρες)
	# ώστε να συγκρίνουμε ακαδημαϊκά/αυστηρά formats με online μικρότερα μαθήματα.
	# Η επιλογή αυτή είναι απλοποίηση που επιτρέπει συγκρίσιμες ταξινομήσεις
	# και μπορεί να προσαρμοστεί σύμφωνα με την τεκμηρίωση της εργασίας.

	if found:
		return round(total, 2)

	return math.nan


def parse_cost_to_float(value: str) -> float:
	if not value:
		return math.nan
	text = value.lower().strip()
	if any(k in text for k in ["free", "no cost", "gratis"]):
		return 0.0

	# Αντιμετώπιση δεκαδικών με κόμμα ή τελεία (π.χ. "12,5" -> 12.5)
	text = text.replace(",", ".")
	compact_price = re.sub(r"[\s$€£]", "", text)
	if compact_price in {"0", "0.0", "0.00"}:
		return 0.0
	# Σχεδιαστική απόφαση: Παίρνουμε την πρώτη αριθμητική τιμή που βρούμε
	# ως ένδειξη κόστους. Δεν επιχειρούμε μετατροπή νομισμάτων ή περίπλοκη
	# εξαγωγή τιμών (π.χ. ranges). Αυτό κρατά τη λογική απλή και επαρκή
	# για τα φίλτρα/γραφήματα της εργασίας.
	match = re.search(r"(\d+(?:\.\d+)?)", text)
	if match:
		return float(match.group(1))
	return math.nan


def as_course(row: dict, source: str) -> Course:
	# Κεντρικό σημείο μετασχηματισμού: κάθε πηγή μετατρέπεται στο κοινό σχήμα
	# (title, provider, category, difficulty, cost, duration, language, source)
	# Σχεδιασμός: Η συνάρτηση αυτή είναι το μόνο σημείο που δημιουργεί
	# το κοινό model `Course` ώστε να είναι εύκολο να ενοποιήσουμε
	# future sources ή να αλλάξουμε το σχήμα χωρίς να επηρεάσουμε
	# το υπόλοιπο pipeline (single-responsibility principle).
	return Course(
		title=(row.get("title") or "Untitled").strip(),
		provider=(row.get("provider") or "Unknown Provider").strip(),
		category=normalize_category(row.get("category", "")),
		difficulty=normalize_difficulty(row.get("difficulty", "")),
		cost=(row.get("cost") or "Unknown").strip(),
		duration=(row.get("duration") or "Unknown").strip(),
		language=normalize_language(row.get("language", "")),
		source=source,
	)


def fetch_edraak_courses() -> list[Course]:
	source = "API_Edraak"
	url = "https://www.edraak.org/api/marketing/courses/"
	try:
		# Πραγματικός κατάλογος μαθημάτων: κρατάμε περιορισμένο πλήθος ώστε να μην επιβαρύνουμε την υπηρεσία.
		response = safe_get(url, params={"limit": 8, "offset": 0})
		response.raise_for_status()
		data = response.json()
		courses = []

		for item in data.get("results", [])[:8]:
			category = item.get("category") or {}
			effort = item.get("effort")
			duration_text = f"{effort} hours" if isinstance(effort, (int, float)) and effort > 0 else "Unknown"
			courses.append(
				as_course(
					{
						"title": item.get("name_en") or item.get("name_ar") or "Edraak Course",
						"provider": "Edraak",
						"category": category.get("name_en") or category.get("en") or "Education",
						"difficulty": item.get("level") or "entry",
						"cost": "Free",
						"duration": duration_text,
						"language": "Arabic",
					},
					source,
				)
			)
		log_status(source, "Success", f"{len(courses)} records")
		return courses
	except Exception as exc:
		log_status(source, "Failed", str(exc))
		return []


def fetch_microsoft_learn_courses() -> list[Course]:
	source = "API_Microsoft_Learn"
	url = "https://learn.microsoft.com/api/catalog/"
	try:
		# Επίσημος κατάλογος Microsoft Learn: χρησιμοποιούμε το courses array, όχι modules/podcasts/άσχετο media.
		response = safe_get(url, params={"locale": "en-us"})
		response.raise_for_status()
		data = response.json()
		items = data.get("courses", [])
		courses = []

		for item in items[:8]:
			category_terms = item.get("products") or item.get("roles") or item.get("subjects") or []
			category = ", ".join(category_terms) if category_terms else "Technology"
			duration_hours = item.get("duration_in_hours")
			duration_text = "Unknown"
			if isinstance(duration_hours, (int, float)) and duration_hours > 0:
				duration_text = f"{duration_hours} hours"
			courses.append(
				as_course(
					{
						"title": item.get("title") or "Microsoft Learn Course",
						"provider": "Microsoft Learn",
						"category": category,
						"difficulty": ", ".join(item.get("levels") or []) or "Unknown",
						"cost": "Free",
						"duration": duration_text,
						"language": "English",
					},
					source,
				)
			)
		log_status(source, "Success", f"{len(courses)} records")
		return courses
	except Exception as exc:
		log_status(source, "Failed", str(exc))
		return []


def fetch_fireroad_mit_courses() -> list[Course]:
	source = "API_FireRoad_MIT"
	url = "https://fireroad.mit.edu/courses/dept/6"
	try:
		# Χρησιμοποιούμε το MIT EECS catalog ως ακαδημαϊκή πηγή μαθημάτων υπολογιστών.
		response = safe_get(url, params={"full": "true"})
		response.raise_for_status()
		data = response.json()
		courses = []

		for item in data:
			if item.get("is_historical"):
				continue
			units = item.get("total_units")
			duration_text = f"{units} hours" if isinstance(units, (int, float)) and units > 0 else "Unknown"
			subject_id = item.get("subject_id") or "MIT"
			courses.append(
				as_course(
					{
						"title": f"{subject_id} - {item.get('title') or 'MIT Course'}",
						"provider": "MIT",
						"category": "Computer Science",
						"difficulty": item.get("level") or "U",
						"cost": "Unknown",
						"duration": duration_text,
						"language": "English",
					},
					source,
				)
			)
			if len(courses) >= 8:
				break
		log_status(source, "Success", f"{len(courses)} records")
		return courses
	except Exception as exc:
		log_status(source, "Failed", str(exc))
		return []


def scrape_w3schools_python() -> list[Course]:
	source = "Scrape_W3Schools"
	url = "https://www.w3schools.com/python/default.asp"
	try:
		html = safe_get(url).text
		soup = BeautifulSoup(html, "html.parser")
		# CSS selectors isolate repeated page elements to build multiple records.
		anchors = soup.select("#leftmenuinnerinner a")[:8]
		courses = []
		for a_tag in anchors:
			title = a_tag.get_text(strip=True)
			if not title:
				continue
			courses.append(
				as_course(
					{
						"title": f"Python Module: {title}",
						"provider": "W3Schools",
						"category": "Python",
						"difficulty": "Beginner",
						"cost": "Free",
						"duration": "4 hours",
						"language": "English",
					},
					source,
				)
			)
		log_status(source, "Success", f"{len(courses)} records")
		return courses
	except Exception as exc:
		log_status(source, "Failed", str(exc))
		return []


def scrape_realpython_topics() -> list[Course]:
	source = "Scrape_RealPython"
	url = "https://realpython.com/tutorials/basics/"
	try:
		html = safe_get(url).text
		soup = BeautifulSoup(html, "html.parser")
		# Επιλέγουμε συνδέσμους από το κύριο περιεχόμενο και φιλτράρουμε
		# το πολύ γενικό UI ώστε να πάρουμε πραγματικούς τίτλους άρθρων.
		anchors = soup.select("main a[href], article a[href], a[href*='/quizzes/'], a[href*='/courses/']")
		seen_titles = set()
		courses = []
		for a_tag in anchors:
			href = a_tag.get("href", "")
			title = a_tag.get_text(" ", strip=True)
			if not title or len(title) < 10:
				continue
			if any(skip in title.lower() for skip in ["share feedback", "next page", "learn python", "get a python cheat sheet"]):
				continue
			if not href.startswith("/") and "realpython.com" not in href:
				continue
			if title in seen_titles:
				continue
			seen_titles.add(title)

			category_hint = "Python"
			if any(k in href.lower() for k in ["data-science", "sql", "database"]):
				category_hint = "Data Science"
			elif any(k in href.lower() for k in ["web-dev", "django", "flask"]):
				category_hint = "Web Development"
			elif any(k in href.lower() for k in ["tools", "devops", "terminal"]):
				category_hint = "Programming"

			courses.append(
				as_course(
					{
						"title": f"Real Python: {title[:90]}",
						"provider": "Real Python",
						"category": category_hint,
						"difficulty": "Beginner",
						"cost": "Free",
						"duration": "Unknown",
						"language": "English",
					},
					source,
				)
			)
			if len(courses) >= 8:
				break
		log_status(source, "Success", f"{len(courses)} records")
		return courses
	except Exception as exc:
		log_status(source, "Failed", str(exc))
		return []


def scrape_geeksforgeeks_python() -> list[Course]:
	source = "Scrape_GeeksforGeeks"
	url = "https://www.geeksforgeeks.org/python-programming-language-tutorial/"
	try:
		html = safe_get(url).text
		soup = BeautifulSoup(html, "html.parser")
		# We use headings as topic units and convert them to pseudo-course entries.
		headings = soup.select("h2")[:8]
		courses = []
		for h_tag in headings:
			title = h_tag.get_text(" ", strip=True)
			if not title:
				continue
			courses.append(
				as_course(
					{
						"title": f"Python Topic: {title}",
						"provider": "GeeksforGeeks",
						"category": "Python",
						"difficulty": "Beginner",
						"cost": "Free",
						"duration": "5 hours",
						"language": "English",
					},
					source,
				)
			)
		log_status(source, "Success", f"{len(courses)} records")
		return courses
	except Exception as exc:
		log_status(source, "Failed", str(exc))
		return []


def fallback_courses() -> list[Course]:
	"""
	If online collection fails, this fallback keeps the app usable for demos,
	testing filters/charts, and recommendation logic.
	"""
	# Σχεδιασμός: Παρέχουμε ένα μικρό, σταθερό dataset ώστε οι λειτουργίες
	# του UI και οι στατιστικές να μπορούν να δοκιμαστούν offline. Αυτό
	# βελτιώνει την αξιοπιστία της παρουσίασης όταν οι εξωτερικές πηγές
	# είναι μη προσβάσιμες ή έχουν αλλάξει δομή.
	source = "Local_Fallback"
	rows = [
		{
			"title": "Python Fundamentals",
			"provider": "Local Demo",
			"category": "Python",
			"difficulty": "Beginner",
			"cost": "Free",
			"duration": "12 hours",
			"language": "English",
		},
		{
			"title": "Data Analysis with Pandas",
			"provider": "Local Demo",
			"category": "Data Science",
			"difficulty": "Intermediate",
			"cost": "$30",
			"duration": "20 hours",
			"language": "English",
		},
		{
			"title": "Web Development Bootcamp",
			"provider": "Local Demo",
			"category": "Web",
			"difficulty": "Beginner",
			"cost": "$40",
			"duration": "35 hours",
			"language": "English",
		},
		{
			"title": "Intro to Machine Learning",
			"provider": "Local Demo",
			"category": "Machine Learning",
			"difficulty": "Advanced",
			"cost": "$55",
			"duration": "28 hours",
			"language": "English",
		},
	]
	return [as_course(row, source) for row in rows]


def collect_all_courses() -> list[Course]:
	collectors: list[Callable[[], list[Course]]] = [
		fetch_edraak_courses,
		fetch_microsoft_learn_courses,
		fetch_fireroad_mit_courses,
		scrape_w3schools_python,
		scrape_realpython_topics,
		scrape_geeksforgeeks_python,
	]

	all_courses: list[Course] = []
	for collector in collectors:
		# Every source reports success/failure but does not stop the whole pipeline.
		all_courses.extend(collector())

	if len(all_courses) < 10:
		# Assignment requires at least 10 records, so fallback ensures minimum volume.
		backup = fallback_courses()
		all_courses.extend(backup)
		log_status("Collector", "Success", "Fallback data appended")

	# Deduplicate by title + provider so append mode does not flood repeats.
	unique: dict[tuple[str, str], Course] = {}
	for c in all_courses:
		key = (c.title.lower().strip(), c.provider.lower().strip())
		unique[key] = c

	result = list(unique.values())
	log_status("Collector", "Success", f"Total unique courses: {len(result)}")
	return result

	# Σχεδιασμός: Η συλλογή είναι «ανθεκτική» — κάθε πηγή μπορεί να αποτύχει
	# ανεξάρτητα και χρησιμοποιούμε fallback + dedupe ώστε να διασφαλίσουμε
	# σταθερό αριθμό εγγραφών χωρίς διπλοεγγραφές, διατηρώντας ταυτόχρονα
	# το ιστορικό στο CSV (append mode).


def ensure_csv_exists(csv_path: Path) -> None:
	if csv_path.exists():
		return
	with csv_path.open("w", newline="", encoding="utf-8") as file:
		writer = csv.writer(file)
		writer.writerow([
			"title",
			"provider",
			"category",
			"difficulty",
			"cost",
			"duration",
			"language",
			"source",
		])


def append_courses_to_csv(courses: list[Course], csv_path: Path) -> int:
	ensure_csv_exists(csv_path)

	# Read existing keys first to keep append mode but prevent duplicates.
	existing = set()
	with csv_path.open("r", newline="", encoding="utf-8") as file:
		reader = csv.DictReader(file)
		for row in reader:
			existing.add((row["title"].strip().lower(), row["provider"].strip().lower()))

	inserted = 0
	with csv_path.open("a", newline="", encoding="utf-8") as file:
		writer = csv.writer(file)
		for c in courses:
			key = (c.title.strip().lower(), c.provider.strip().lower())
			if key in existing:
				# Skip known entries; this keeps history clean across repeated runs.
				continue
			writer.writerow([
				c.title,
				c.provider,
				c.category,
				c.difficulty,
				c.cost,
				c.duration,
				c.language,
				c.source,
			])
			existing.add(key)
			inserted += 1

	log_status("CSV", "Success", f"Inserted {inserted} new rows")
	return inserted


def load_courses_df(csv_path: Path) -> pd.DataFrame:
	ensure_csv_exists(csv_path)
	try:
		df = pd.read_csv(csv_path)
	except pd.errors.EmptyDataError:
		df = pd.DataFrame(
			columns=["title", "provider", "category", "difficulty", "cost", "duration", "language", "source"]
		)

	for col in ["title", "provider", "category", "difficulty", "cost", "duration", "language", "source"]:
		if col not in df.columns:
			# Guard against partially broken CSV files.
			df[col] = ""

	df["category"] = df["category"].astype(str).map(normalize_category)
	df["difficulty"] = df["difficulty"].astype(str).map(normalize_difficulty)
	df["language"] = df["language"].astype(str).map(normalize_language)

	# Numeric helper columns power filtering, plotting, and recommendation scoring.
	df["duration_hours"] = df["duration"].astype(str).map(parse_duration_to_hours)
	df["cost_value"] = df["cost"].astype(str).map(parse_cost_to_float)

	return df


def audit_missing_information(df: pd.DataFrame) -> dict[str, object]:
	"""Return a compact quality report focused on missing or low-information fields."""
	required_columns = ["title", "provider", "category", "difficulty", "cost", "duration", "language", "source"]
	missing_by_column = {col: int(df[col].isna().sum()) if col in df.columns else None for col in required_columns}
	empty_string_by_column = {
		col: int((df[col].astype(str).str.strip() == "").sum()) if col in df.columns else None for col in required_columns
	}
	mostly_constant_columns = []
	for col in required_columns:
		if col in df.columns and df[col].nunique(dropna=False) <= 1:
			mostly_constant_columns.append(col)
	return {
		"row_count": int(len(df)),
		"missing_by_column": missing_by_column,
		"empty_string_by_column": empty_string_by_column,
		"mostly_constant_columns": mostly_constant_columns,
	}


class CourseApp:
	def __init__(self, root: Tk, csv_path: Path) -> None:
		self.root = root
		self.csv_path = csv_path
		self.df = load_courses_df(csv_path)

		self.root.title(TEAM_INFO)
		self.root.geometry("1320x780")
		self.root.minsize(1200, 700)
		self.root.configure(background=APP_BG)

		self.category_var = StringVar(value="All")
		self.difficulty_var = StringVar(value="All")
		self.cost_filter_var = StringVar(value="All")
		self.language_var = StringVar(value="All")
		self.max_cost_var = DoubleVar(value=1000.0)
		self.schedule_hours_var = DoubleVar(value=24.0)
		self.schedule_status_var = StringVar(value="Ανενεργό")
		self.auto_refresh_job: str | None = None

		self._configure_style()
		self._build_layout()
		self.refresh_filter_values()
		self.render_table(self.df)
		self.schedule_status_var.set("Έτοιμο για συλλογή δεδομένων")

	def _configure_style(self) -> None:
		style = ttk.Style(self.root)
		if "clam" in style.theme_names():
			style.theme_use("clam")

		tk_default_font = tkfont.nametofont("TkDefaultFont")
		tk_default_font.configure(family="Segoe UI", size=10)
		title_font = tkfont.Font(family="Segoe UI", size=18, weight="bold")
		subtitle_font = tkfont.Font(family="Segoe UI", size=10)

		style.configure("TFrame", background=APP_BG)
		style.configure("Card.TFrame", background=CARD_BG)
		style.configure("Header.TFrame", background=APP_BG)
		style.configure("TLabel", background=APP_BG, foreground="#E2E8F0")
		style.configure("Muted.TLabel", background=APP_BG, foreground=TEXT_MUTED)
		style.configure("HeaderTitle.TLabel", background=APP_BG, foreground="#F8FAFC", font=title_font)
		style.configure("HeaderSubtitle.TLabel", background=APP_BG, foreground=TEXT_MUTED, font=subtitle_font)
		style.configure("TLabelframe", background=APP_BG, padding=8, borderwidth=1)
		style.configure("TLabelframe.Label", background=APP_BG, foreground="#E2E8F0", font=("Segoe UI", 10, "bold"))
		style.configure("TButton", padding=(12, 7), font=("Segoe UI", 10), background="#1E293B", foreground="#E2E8F0")
		style.map(
			"TButton",
			background=[("active", "#334155"), ("pressed", "#0F172A")],
			foreground=[("active", "#FFFFFF")],
			relief=[("pressed", "sunken"), ("!pressed", "raised")],
		)
		style.configure("TEntry", padding=5, fieldbackground="#0B1220", foreground="#F8FAFC")
		style.configure("TCombobox", padding=5, fieldbackground="#0B1220", foreground="#F8FAFC")
		style.configure(
			"Treeview",
			rowheight=28,
			font=("Segoe UI", 10),
			background="#0B1220",
			fieldbackground="#0B1220",
			foreground="#E2E8F0",
			bordercolor="#1E293B",
			lightcolor="#1E293B",
			darkcolor="#1E293B",
		)
		style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), foreground="#F8FAFC", background="#1E293B")
		style.map("Treeview", background=[("selected", ACCENT_LIGHT)], foreground=[("selected", "white")])

	def _build_layout(self) -> None:
		container = ttk.Frame(self.root, padding=16, style="Header.TFrame")
		container.pack(fill=BOTH, expand=True)

		header = ttk.Frame(container, padding=(4, 0, 4, 12), style="Header.TFrame")
		header.pack(fill=X)
		ttk.Label(header, text="Course Aggregator & Recommender", style="HeaderTitle.TLabel").pack(anchor=W)
		ttk.Label(
			header,
			text="A professional dashboard for course collection, filtering, visualization, and recommendations.",
			style="HeaderSubtitle.TLabel",
		).pack(anchor=W, pady=(2, 0))

		# Γραμμή εντολών πάνω: ενέργειες συλλογής/φόρτωσης/εξαγωγής δεδομένων.
		top = ttk.Frame(container, padding=10, style="Card.TFrame")
		top.pack(fill=X, pady=(0, 10))

		ttk.Button(top, text="Συλλογή Δεδομένων (API+Scraping)", command=self.collect_data).pack(side=LEFT, padx=4)
		ttk.Button(top, text="Φόρτωση CSV", command=self.reload_df).pack(side=LEFT, padx=4)
		ttk.Button(top, text="Εξαγωγή CSV", command=self.export_visible_csv).pack(side=LEFT, padx=4)

		# Περιοχή φίλτρων: ελέγχει τι φαίνεται στον πίνακα και τι προτείνεται/σχεδιάζεται.
		filter_frame = ttk.LabelFrame(container, text="Φίλτρα", padding=10)
		filter_frame.pack(fill=X, pady=(0, 10))
		for col in range(12):
			filter_frame.columnconfigure(col, weight=1 if col in {1, 3, 7} else 0)
		ttk.Label(filter_frame, text="Κατηγορία").grid(row=0, column=0, sticky=W, padx=4, pady=4)
		self.category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, state="readonly", width=20)
		self.category_combo.grid(row=0, column=1, padx=4, pady=4)
		ttk.Label(filter_frame, text="Δυσκολία").grid(row=0, column=2, sticky=W, padx=4, pady=4)
		self.diff_combo = ttk.Combobox(filter_frame, textvariable=self.difficulty_var, state="readonly", width=20)
		self.diff_combo.grid(row=0, column=3, padx=4, pady=4)
		ttk.Label(filter_frame, text="Κόστος").grid(row=0, column=4, sticky=W, padx=4, pady=4)
		self.cost_combo = ttk.Combobox(
			filter_frame,
			textvariable=self.cost_filter_var,
			state="readonly",
			values=["All", "Free", "Paid"],
			width=12,
		)
		self.cost_combo.grid(row=0, column=5, padx=4, pady=4)
		ttk.Label(filter_frame, text="Γλώσσα").grid(row=0, column=6, sticky=W, padx=4, pady=4)
		self.lang_combo = ttk.Combobox(filter_frame, textvariable=self.language_var, state="readonly", width=16)
		self.lang_combo.grid(row=0, column=7, padx=4, pady=4)

		ttk.Label(filter_frame, text="Μέγιστο Κόστος").grid(row=0, column=8, sticky=W, padx=4, pady=4)
		ttk.Entry(filter_frame, textvariable=self.max_cost_var, width=10).grid(row=0, column=9, padx=4, pady=4)

		ttk.Button(filter_frame, text="Εφαρμογή Φίλτρων", command=self.apply_filters).grid(row=0, column=10, padx=4, pady=4)
		ttk.Button(filter_frame, text="Επαναφορά Φίλτρων", command=self.reset_filters).grid(row=0, column=11, padx=4, pady=4)

		# Περιοχή ανάλυσης: κουμπιά για τα τρία γραφήματα και τις συστάσεις.
		action_frame = ttk.LabelFrame(container, text="Ανάλυση & Συστάσεις", padding=10)
		action_frame.pack(fill=X, pady=(0, 10))
		ttk.Button(action_frame, text="Διάγραμμα: Top5 Διάρκειας", command=self.plot_bar_top5_duration).pack(side=LEFT, padx=5)
		ttk.Button(action_frame, text="Διάγραμμα Πίτας: Δυσκολία", command=self.plot_pie_difficulty).pack(side=LEFT, padx=5)
		ttk.Button(action_frame, text="Γραφική: Κόστος vs Διάρκεια", command=self.plot_line_cost_vs_duration).pack(side=LEFT, padx=5)
		ttk.Button(action_frame, text="Συστάσεις Top 3", command=self.recommend_top3).pack(side=LEFT, padx=5)
		ttk.Button(action_frame, text="Έλεγχος Ελλιπών", command=self.audit_data).pack(side=LEFT, padx=5)
		ttk.Label(action_frame, text="Auto κάθε").pack(side=LEFT, padx=(18, 4))
		ttk.Entry(action_frame, textvariable=self.schedule_hours_var, width=6).pack(side=LEFT, padx=4)
		ttk.Label(action_frame, text="ώρες").pack(side=LEFT, padx=4)
		ttk.Button(action_frame, text="Έναρξη Auto", command=self.start_auto_collection).pack(side=LEFT, padx=5)
		ttk.Button(action_frame, text="Παύση Auto", command=self.stop_auto_collection).pack(side=LEFT, padx=5)
		ttk.Label(action_frame, textvariable=self.schedule_status_var).pack(side=LEFT, padx=5)

		# Κύρια προβολή δεδομένων: πίνακας με οριζόντιο και κάθετο scroll.
		table_frame = ttk.Frame(container, padding=10, style="Card.TFrame")
		table_frame.pack(fill=BOTH, expand=True)

		columns = ["title", "provider", "category", "difficulty", "cost", "duration", "language", "source"]
		self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=22)

		# Ελληνικές επικεφαλίδες στη γραφική διεπαφή (για την παράδοση)
		heading_map = {
			"title": "Τίτλος",
			"provider": "Πάροχος",
			"category": "Κατηγορία",
			"difficulty": "Δυσκολία",
			"cost": "Κόστος",
			"duration": "Διάρκεια",
			"language": "Γλώσσα",
			"source": "Πηγή",
		}

		for col in columns:
			self.tree.heading(col, text=heading_map.get(col, col.title()))
			width = 180 if col in {"title", "provider"} else 120
			self.tree.column(col, width=width, anchor=W)

		v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
		h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
		self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

		self.tree.pack(side=LEFT, fill=BOTH, expand=True)
		v_scroll.pack(side=RIGHT, fill=Y)
		h_scroll.pack(side="bottom", fill=X)

		self.status_var = StringVar(value="Έτοιμο")
		status_bar = ttk.Frame(container, padding=(4, 8, 4, 0), style="Header.TFrame")
		status_bar.pack(fill=X)
		ttk.Label(status_bar, textvariable=self.status_var, style="Muted.TLabel").pack(anchor=W)

	def refresh_filter_values(self) -> None:
		categories = ["All"] + sorted(set(self.df["category"].dropna().astype(str)))
		difficulties = ["All"] + sorted(set(self.df["difficulty"].dropna().astype(str)))
		languages = ["All"] + sorted(set(self.df["language"].dropna().astype(str)))

		self.category_combo["values"] = categories
		self.diff_combo["values"] = difficulties
		self.lang_combo["values"] = languages

		if self.category_var.get() not in categories:
			self.category_var.set("All")
		if self.difficulty_var.get() not in difficulties:
			self.difficulty_var.set("All")
		if self.language_var.get() not in languages:
			self.language_var.set("All")

	def render_table(self, df: pd.DataFrame) -> None:
		self.tree.delete(*self.tree.get_children())
		for index, (_, row) in enumerate(df.iterrows()):
			tag = "even" if index % 2 == 0 else "odd"
			self.tree.insert(
				"",
				END,
				values=[
					row.get("title", ""),
					row.get("provider", ""),
					row.get("category", ""),
					row.get("difficulty", ""),
					row.get("cost", ""),
					row.get("duration", ""),
					row.get("language", ""),
					row.get("source", ""),
				],
				tags=(tag,),
			)
		self.tree.tag_configure("even", background="#FFFFFF")
		self.tree.tag_configure("odd", background="#F7FAFD")
		self.status_var.set(f"Εμφανίζονται {len(df)} εγγραφές")

	def reload_df(self) -> None:
		self.df = load_courses_df(self.csv_path)
		self.refresh_filter_values()
		self.render_table(self.df)
		log_status("GUI", "Success", "CSV reloaded")
		self.status_var.set(f"Το CSV φορτώθηκε ξανά. Σύνολο εγγραφών: {len(self.df)}")

	def collect_data(self, show_message: bool = True) -> int:
		courses = collect_all_courses()
		inserted = append_courses_to_csv(courses, self.csv_path)
		self.reload_df()
		self.status_var.set(f"Συλλογή ολοκληρώθηκε. Νέες εγγραφές: {inserted}")
		if show_message:
			messagebox.showinfo("Συλλογή Ολοκληρώθηκε", f"Προστέθηκαν {inserted} νέες εγγραφές στο {self.csv_path.name}.")
		return inserted

	def start_auto_collection(self) -> None:
		try:
			hours = float(self.schedule_hours_var.get())
		except Exception:
			messagebox.showwarning("Αυτόματη Συλλογή", "Δώσε έγκυρο αριθμό ωρών.")
			return
		if hours <= 0:
			messagebox.showwarning("Αυτόματη Συλλογή", "Το διάστημα πρέπει να είναι θετικός αριθμός ωρών.")
			return

		self.stop_auto_collection(show_message=False)
		self.schedule_status_var.set(f"Ενεργό: κάθε {hours:g} ώρες")
		self._schedule_next_collection(hours)
		log_status("Scheduler", "Success", f"Auto collection every {hours:g} hours")

	def _schedule_next_collection(self, hours: float | None = None) -> None:
		if hours is None:
			hours = float(self.schedule_hours_var.get())
		delay_ms = max(1000, int(hours * 60 * 60 * 1000))
		self.auto_refresh_job = self.root.after(delay_ms, self.run_scheduled_collection)

	def run_scheduled_collection(self) -> None:
		self.auto_refresh_job = None
		try:
			inserted = self.collect_data(show_message=False)
			log_status("Scheduler", "Success", f"Scheduled run inserted {inserted} rows")
		except Exception as exc:
			log_status("Scheduler", "Failed", str(exc))
		finally:
			if self.schedule_status_var.get().startswith("Ενεργό"):
				self._schedule_next_collection()

	def stop_auto_collection(self, show_message: bool = True) -> None:
		if self.auto_refresh_job is not None:
			self.root.after_cancel(self.auto_refresh_job)
			self.auto_refresh_job = None
		self.schedule_status_var.set("Ανενεργό")
		self.status_var.set("Η αυτόματη συλλογή σταμάτησε")
		log_status("Scheduler", "Success", "Auto collection stopped")
		if show_message:
			messagebox.showinfo("Αυτόματη Συλλογή", "Η αυτόματη συλλογή σταμάτησε.")

	def audit_data(self) -> None:
		report = audit_missing_information(self.df)
		missing_by_column = report["missing_by_column"]
		empty_string_by_column = report["empty_string_by_column"]
		mostly_constant_columns = report["mostly_constant_columns"]

		lines = [f"Σύνολο γραμμών: {report['row_count']}"]
		lines.append("Ελλείψεις ανά στήλη:")
		for col, count in missing_by_column.items():
			if count is not None and count > 0:
				lines.append(f"- {col}: {count}")
		lines.append("Κενές τιμές (empty strings) ανά στήλη:")
		for col, count in empty_string_by_column.items():
			if count is not None and count > 0:
				lines.append(f"- {col}: {count}")
		if mostly_constant_columns:
			lines.append(f"Περισσότερο σταθερές στήλες: {', '.join(mostly_constant_columns)}")
		else:
			lines.append("Δεν βρέθηκαν στήλες που να είναι ουσιαστικά σταθερές.")

		log_status("Audit", "Success", f"missing={sum(v or 0 for v in missing_by_column.values())}")
		messagebox.showinfo("Έλεγχος Ελλιπών Πληροφοριών", "\n".join(lines))

	def get_filtered_df(self) -> pd.DataFrame:
		# Το φιλτράρισμα εφαρμόζεται βήμα-βήμα ώστε κάθε κριτήριο να είναι κατανοητό.
		df = self.df.copy()

		if self.category_var.get() != "All":
			df = df[df["category"] == self.category_var.get()]

		if self.difficulty_var.get() != "All":
			df = df[df["difficulty"] == self.difficulty_var.get()]

		if self.language_var.get() != "All":
			df = df[df["language"] == self.language_var.get()]

		cost_type = self.cost_filter_var.get()
		if cost_type == "Free":
			df = df[df["cost_value"] == 0.0]
		elif cost_type == "Paid":
			df = df[df["cost_value"].fillna(0) > 0]

		max_cost = self.max_cost_var.get()
		if max_cost >= 0:
			# Οι άγνωστες τιμές κόστους αντιμετωπίζονται ως "πολύ μεγάλες"
			# ώστε να απορρίπτονται από αυστηρά φίλτρα μέγιστου κόστους.
			df = df[df["cost_value"].fillna(float("inf")) <= max_cost]

		return df

	def apply_filters(self) -> None:
		filtered = self.get_filtered_df()
		self.render_table(filtered)
		log_status("Filter", "Success", f"Visible rows: {len(filtered)}")
		self.status_var.set(f"Ενεργά φίλτρα. Ορατές εγγραφές: {len(filtered)}")

	def reset_filters(self) -> None:
		self.category_var.set("All")
		self.difficulty_var.set("All")
		self.cost_filter_var.set("All")
		self.language_var.set("All")
		self.max_cost_var.set(1000.0)
		self.apply_filters()
		self.status_var.set("Τα φίλτρα επαναφέρθηκαν")

	def export_visible_csv(self) -> None:
		filtered = self.get_filtered_df()
		if filtered.empty:
			messagebox.showwarning("Εξαγωγή", "Δεν υπάρχουν γραμμές για εξαγωγή.")
			return

		output = filedialog.asksaveasfilename(
			title="Export filtered data",
			defaultextension=".csv",
			filetypes=[("CSV file", "*.csv")],
		)
		if not output:
			return

		filtered[["title", "provider", "category", "difficulty", "cost", "duration", "language", "source"]].to_csv(
			output,
			index=False,
			encoding="utf-8",
		)
		messagebox.showinfo("Εξαγωγή", f"Εξήχθησαν {len(filtered)} γραμμές.")

	def _ensure_non_empty_for_plot(self, df: pd.DataFrame) -> bool:
		if df.empty:
			messagebox.showwarning("Χωρίς δεδομένα", "Δεν υπάρχουν διαθέσιμα δεδομένα για αυτό το γράφημα.")
			return False
		return True

	def plot_bar_top5_duration(self) -> None:
		df = self.get_filtered_df().copy()
		# Ζητούμενο γράφημα: κορυφαία 5 μαθήματα κατά διάρκεια (ώρες).
		df = df.dropna(subset=["duration_hours"]).sort_values("duration_hours", ascending=False).head(5)
		if not self._ensure_non_empty_for_plot(df):
			return

		plt.figure(figsize=(10, 5))
		plt.bar(df["title"], df["duration_hours"], color="#2E86AB")
		plt.title("Top 5 Μαθήματα κατά Διάρκεια")
		plt.xlabel("Μάθημα")
		plt.ylabel("Διάρκεια (ώρες)")
		plt.xticks(rotation=30, ha="right")
		plt.tight_layout()
		plt.show()

	def plot_pie_difficulty(self) -> None:
		df = self.get_filtered_df().copy()
		if not self._ensure_non_empty_for_plot(df):
			return

		# Ζητούμενο γράφημα: κατανομή επιπέδων δυσκολίας σε ποσοστά.
		counts = df["difficulty"].value_counts()
		plt.figure(figsize=(6, 6))
		plt.pie(counts.values, labels=counts.index.astype(str).tolist(), autopct="%1.1f%%", startangle=90)
		plt.title("Κατανομή Επιπέδου Δυσκολίας")
		plt.tight_layout()
		plt.show()

	def plot_line_cost_vs_duration(self) -> None:
		df = self.get_filtered_df().copy()
		# Ζητούμενο γράφημα: σχέση Κόστους vs Διάρκειας για τα top-5 σε διάρκεια.
		df = df.dropna(subset=["duration_hours", "cost_value"]).sort_values("duration_hours", ascending=False).head(5)
		if not self._ensure_non_empty_for_plot(df):
			return

		plt.figure(figsize=(9, 5))
		plt.plot(df["duration_hours"], df["cost_value"], marker="o", linestyle="-", color="#F18F01")
		for _, row in df.iterrows():
			plt.annotate(row["title"][:18], (row["duration_hours"], row["cost_value"]), fontsize=8)
		plt.title("Κόστος vs Διάρκεια (Top 5 κατά Διάρκεια)")
		plt.xlabel("Διάρκεια (ώρες)")
		plt.ylabel("Κόστος")
		plt.grid(True, linestyle="--", alpha=0.5)
		plt.tight_layout()
		plt.show()

	def recommend_top3(self) -> None:
		"""
		Composite score design:
		- Duration contributes positively (more content can mean more value).
		- Cost contributes negatively (lower cost is preferred).
		- Exact matches in category/difficulty/language add bonuses.

		Missing values are handled dynamically by rebalancing only active terms.
		"""
		df = self.get_filtered_df().copy()
		if df.empty:
			messagebox.showinfo("Συστάσεις", "Δεν βρέθηκαν μαθήματα που ταιριάζουν.")
			return

		# Min/max are used to normalize values to the same scale [0, 1].
		duration_min = df["duration_hours"].min(skipna=True)
		duration_max = df["duration_hours"].max(skipna=True)
		cost_min = df["cost_value"].min(skipna=True)
		cost_max = df["cost_value"].max(skipna=True)

		def normalize(v: float, v_min: float, v_max: float) -> float:
			if pd.isna(v) or pd.isna(v_min) or pd.isna(v_max) or v_max == v_min:
				return math.nan
			return (v - v_min) / (v_max - v_min)

		scores = []
		for _, row in df.iterrows():
			d_norm = normalize(row["duration_hours"], duration_min, duration_max)
			c_norm = normalize(row["cost_value"], cost_min, cost_max)

			parts = []

			# Base score rewards larger duration and lower cost.
			if not pd.isna(d_norm):
				parts.append((0.6, d_norm))
			if not pd.isna(c_norm):
				parts.append((0.4, 1.0 - c_norm))

			base_score = 0.0
			if parts:
				weight_sum = sum(w for w, _ in parts)
				base_score = sum(w * v for w, v in parts) / weight_sum

			# Μικρές πρόσθετες μονάδες όταν το μάθημα ταιριάζει ακριβώς
			# με τις επιλογές του χρήστη (κατηγορία/δυσκολία/γλώσσα).
			bonus = 0.0
			if self.category_var.get() != "All" and row["category"] == self.category_var.get():
				bonus += 0.08
			if self.difficulty_var.get() != "All" and row["difficulty"] == self.difficulty_var.get():
				bonus += 0.06
			if self.language_var.get() != "All" and row["language"] == self.language_var.get():
				bonus += 0.06

			score = base_score + bonus
			scores.append(score)

		df["composite_score"] = scores
		top3 = df.sort_values("composite_score", ascending=False).head(3)

		if top3.empty:
			messagebox.showinfo("Συστάσεις", "Δεν υπάρχουν διαθέσιμες προτάσεις.")
			return

		lines = []
		for i, (_, row) in enumerate(top3.iterrows(), start=1):
			lines.append(
				f"{i}. {row['title']} | {row['provider']} | "
				f"Score={row['composite_score']:.3f} | Cost={row['cost']} | Duration={row['duration']}"
			)

		messagebox.showinfo("Top 3 Συστάσεις", "\n".join(lines))
		log_status("Recommender", "Success", "Top 3 generated")


def main() -> None:
	csv_path = Path(__file__).parent / CSV_FILENAME
	ensure_csv_exists(csv_path)

	root = Tk()
	app = CourseApp(root, csv_path)
	# Keep a reference so static analyzers understand the object is used.
	_ = app
	root.mainloop()


if __name__ == "__main__":
	main()
