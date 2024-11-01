from flask import Flask, jsonify, request, url_for
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote_plus

app = Flask(__name__)  # Initialize the Flask app

# Ensure the results directory exists
RESULTS_DIR = 'static/results'
os.makedirs(RESULTS_DIR, exist_ok=True)

def print_status(message):
    """Print status messages in a consistent format"""
    print(f"[STATUS] {message}")

def log_skipped_car(title):
    """Log the title of skipped cars due to missing elements."""
    with open("skipped_cars.log", "a") as log_file:
        log_file.write(f"Skipped car due to missing link: {title}\n")

# Function to fetch eBay sold listings based on vehicle info
def fetch_ebay_listings(year, make, model, min_price="150", max_price="700", limit=40):
    """Fetch eBay sold listings for the given vehicle details, limiting to 40 results."""
    base_url = "https://www.ebay.com/sch/i.html"
    search_term = quote_plus(f"{year} {make} {model}")
    params = {
        '_from': 'R40',
        '_nkw': search_term,
        '_sacat': '6028',
        '_udlo': min_price,
        '_udhi': max_price,
        'LH_Complete': '1',
        'LH_Sold': '1',
        'rt': 'nc',
        'LH_ItemCondition': '4'
    }
    
    url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'text/html',
        'Accept-Language': 'en-US',
    }
    
    listings = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.s-item__info')[:limit]  # Limit to 40 items
        
        for item in items:
            title_elem = item.select_one('.s-item__title')
            price_elem = item.select_one('.s-item__price')
            date_elem = item.select_one('.s-item__ended-date')
            shipping_elem = item.select_one('.s-item__shipping')
            link_elem = item.select_one('a.s-item__link')
            image_elem = item.find_previous_sibling("div").select_one("img")  # Select the thumbnail image

            # Skip if title contains "Remanufactured" or "Reconditioned" or if title_elem is missing
            if not title_elem or any(keyword in title_elem.text for keyword in ["Remanufactured", "Reconditioned"]):
                continue

            listings.append({
                'Title': title_elem.text.strip(),
                'Price': price_elem.text.strip(),
                'Shipping': shipping_elem.text.strip() if shipping_elem else 'N/A',
                'Date Sold': date_elem.text.replace('Sold', '').strip() if date_elem else 'N/A',
                'Link': link_elem['href'] if link_elem else 'N/A',
                'Image': image_elem['src'] if image_elem else 'https://via.placeholder.com/100'  # Use placeholder if no image
            })

            # Stop collecting results if the limit is reached
            if len(listings) >= limit:
                break

        return listings
    
    except Exception as e:
        print(f"Error fetching eBay listings: {e}")
        return []

@app.route('/generate_sold_results')
def generate_sold_results():
    year = request.args.get('year')
    make = request.args.get('make')
    model = request.args.get('model')
    location = request.args.get('location')
    results = fetch_ebay_listings(year, make, model, limit=40)

    # Generate HTML content in table format with images and row numbers
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sold Listings for {year} {make} {model} - {location}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f0f2f5; }}
            .container {{ padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h2 {{ color: #333; }}
            .back-button {{ display: inline-block; padding: 10px 15px; background-color: #007bff; color: white; border-radius: 4px; text-decoration: none; }}
            .back-button:hover {{ background-color: #0056b3; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background-color: #f8f8f8; font-weight: bold; cursor: pointer; }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            img {{ width: 60px; height: auto; }}
        </style>
        <script>
            function sortTable(n, isNumeric) {{
                const table = document.getElementById("resultsTable");
                let switching = true;
                let direction = "asc";

                while (switching) {{
                    switching = false;
                    const rows = table.rows;
                    for (let i = 1; i < rows.length - 1; i++) {{
                        let shouldSwitch = false;
                        const x = rows[i].getElementsByTagName("TD")[n];
                        const y = rows[i + 1].getElementsByTagName("TD")[n];
                        let xValue = isNumeric ? parseFloat(x.innerText.replace(/[^0-9.-]+/g, "")) : x.innerText.toLowerCase();
                        let yValue = isNumeric ? parseFloat(y.innerText.replace(/[^0-9.-]+/g, "")) : y.innerText.toLowerCase();
                        if ((direction === "asc" && xValue > yValue) || (direction === "desc" && xValue < yValue)) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }}
                    if (shouldSwitch) {{
                        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                        switching = true;
                    }} else if (direction === "asc") {{
                        direction = "desc";
                        switching = true;
                    }}
                }}
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h2>Sold Listings for {year} {make} {model} - {location}</h2>
            <a href="/" class="back-button">Back to Inventory</a>
            <table id="resultsTable">
                <tr>
                    <th>Row</th>
                    <th>Image</th>
                    <th onclick="sortTable(2, false)">Title</th>
                    <th onclick="sortTable(3, true)">Price</th>
                    <th>Shipping</th>
                    <th>Date Sold</th>
                </tr>
    """
    for i, item in enumerate(results, start=1):
        html_content += f"""
                <tr>
                    <td>{i}</td>
                    <td><img src="{item["Image"]}" alt="Item Image"></td>
                    <td><a href="{item["Link"]}" target="_blank">{item["Title"]}</a></td>
                    <td>{item["Price"]}</td>
                    <td>{item["Shipping"]}</td>
                    <td>{item["Date Sold"]}</td>
                </tr>
        """
    
    html_content += """
            </table>
        </div>
    </body>
    </html>
    """

    # Save to an HTML file in the static/results directory
    filename = f"{year}_{make}_{model}_sold_results.html"
    filepath = os.path.join(RESULTS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(html_content)

    # Return the URL to the generated file
    file_url = url_for('static', filename=f"results/{filename}")
    return jsonify({"file_url": file_url})

if __name__ == "__main__":
    print_status("Starting Kenny U-Pull Inventory Scraper with eBay Search Integration...")
    app.run(debug=True, port=5000)
