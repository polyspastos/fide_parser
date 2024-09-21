import os
import zipfile
import requests
from datetime import datetime
from dateutil import parser
import re
import sys

# Constants
URL_TEMPLATE = "http://ratings.fide.com/download/standard_{month}{year}frl.zip"
MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
START_YEAR = 2015
OUTPUT_DIR = "fide_files"
CURRENT_YEAR = datetime.now().year
CURRENT_MONTH = datetime.now().month

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_and_extract_files(start_year=START_YEAR):
    for year in range(start_year, CURRENT_YEAR + 1):
        for month_index, month in enumerate(MONTHS):
            if year == CURRENT_YEAR and month_index + 1 > CURRENT_MONTH:
                break
            file_name = f"standard_{month}{str(year)[-2:]}frl.zip"
            zip_path = os.path.join(OUTPUT_DIR, file_name)

            # Check if the file is already present
            if os.path.exists(zip_path):
                print(f"File {file_name} already exists, skipping download.")
                continue

            file_url = URL_TEMPLATE.format(month=month, year=str(year)[-2:])

            # Download the file
            response = requests.get(file_url)
            if response.status_code == 200:
                with open(zip_path, "wb") as file:
                    file.write(response.content)
                print(f"Downloaded {file_name}")

                # Extract the ZIP file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(OUTPUT_DIR)
                print(f"Extracted {file_name}")
            else:
                print(f"Failed to download {file_name}")

def parse_files(federation_code, rating_threshold=None):
    title_holders = {}
    young_im_counts = {}
    young_gm_counts = {}
    tracked_ims = []
    tracked_gms = []
    rating_achievers = {}  # Track players achieving the rating threshold
    rating_count_per_year = {}  # Track count of players crossing the threshold each year

    for year in range(START_YEAR, CURRENT_YEAR + 1):
        for month_index, month in enumerate(MONTHS):
            if year == CURRENT_YEAR and month_index + 1 > CURRENT_MONTH:
                break
            file_name = f"standard_{month}{str(year)[-2:]}frl.txt"
            file_path = os.path.join(OUTPUT_DIR, file_name)
            print(file_path)
            
            if not os.path.exists(file_path):
                continue

            with open(file_path, 'r', encoding='latin-1') as file:
                for line in file:
                    if federation_code.upper() in line:
                        # Check if inactive
                        if line.strip().endswith('i'):
                            continue

                        data = re.split(r'\s+', line.strip())
                        title = data[5]
                        rating = int(data[5]) if data[5].isdigit() else None

                        name = " ".join(data[1:3])
                        # Track players who achieved the rating threshold for the first time
                        if rating and rating >= rating_threshold:
                            if name not in rating_achievers:
                                rating_achievers[name] = {'first_year': year, 'rating': rating}
                                if year not in rating_count_per_year:
                                    rating_count_per_year[year] = 0
                                rating_count_per_year[year] += 1

                        if title not in ['GM', 'IM', 'FM']:
                            continue

                        birth_date_str = data[9]
                        try:
                            birth_date = parser.parse(birth_date_str)
                        except:
                            continue
                        age = year - birth_date.year

                        if age >= 25 or age <= 0:
                            continue
                        
                        age_at_title = age

                        if name not in title_holders:
                            title_holders[name] = {'first_year': year, 'titles': [(title, age_at_title)]}
                        else:
                            # Check if title is upgraded
                            last_title, _ = title_holders[name]['titles'][-1]
                            if last_title != title:
                                title_holders[name]['titles'].append((title, age_at_title))
                                title_holders[name]['first_year'] = year

                        # Track young IMs and GMs
                        if title == 'IM':
                            if name not in tracked_ims:
                                if year not in young_im_counts:
                                    young_im_counts[year] = 0
                                young_im_counts[year] += 1
                                tracked_ims.append(name)
                                
                        elif title == 'GM':
                            if name not in tracked_gms:
                                if year not in young_gm_counts:
                                    young_gm_counts[year] = 0
                                young_gm_counts[year] += 1
                                tracked_gms.append(name)

    return title_holders, young_im_counts, young_gm_counts, rating_achievers, rating_count_per_year

def save_results(federation_code, title_holders, young_im_counts, young_gm_counts, rating_achievers, rating_threshold, rating_count_per_year):
    # Save title holders
    title_file = os.path.join(OUTPUT_DIR, f"title_holders_{federation_code}.txt")
    with open(title_file, 'w', encoding='utf-8') as file:
        for name, info in sorted(title_holders.items()):
            file.write(f"{name} - ")
            title_history = "; ".join([f"{t[0]} at age {t[1]}" for t in info['titles']])
            file.write(f"{title_history} (first appearance: {info['first_year']})\n")

    # Calculate and save general statistics
    stats_file = os.path.join(OUTPUT_DIR, "statistics.txt")
    with open(stats_file, 'w', encoding='utf-8') as file:
        for year in sorted(set(young_im_counts.keys()).union(young_gm_counts.keys())):
            im_count = young_im_counts.get(year, 0)
            gm_count = young_gm_counts.get(year, 0)
            file.write(f"{year}: {im_count} new young IMs overall, {gm_count} new young GMs overall\n")

    # Save rating achievers statistics, ordered by year
    rating_file = os.path.join(OUTPUT_DIR, f"rating_achievers_{rating_threshold}.txt")
    with open(rating_file, 'w', encoding='utf-8') as file:
        sorted_rating_achievers = sorted(rating_achievers.items(), key=lambda x: x[1]['first_year'])
        for name, info in sorted_rating_achievers:
            file.write(f"{name} achieved a rating of {info['rating']} for the first time in {info['first_year']}\n")

    # Save rating achievers count per year
    rating_count_file = os.path.join(OUTPUT_DIR, f"rating_achievers_{rating_threshold}_count_per_year.txt")
    with open(rating_count_file, 'w', encoding='utf-8') as file:
        for year in sorted(rating_count_per_year.keys()):
            count = rating_count_per_year[year]
            file.write(f"{year}: {count} new players achieved a rating of {rating_threshold} or above for the first time\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: python parser.py <federation_code> [rating_threshold]")
        return
    
    federation_code = sys.argv[1].lower()
    rating_threshold = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    download_and_extract_files()
    title_holders, young_im_counts, young_gm_counts, rating_achievers, rating_count_per_year = parse_files(federation_code, rating_threshold)
    save_results(federation_code, title_holders, young_im_counts, young_gm_counts, rating_achievers, rating_threshold, rating_count_per_year)
    print(f"Processing completed for federation: {federation_code.upper()}")

if __name__ == "__main__":
    main()
