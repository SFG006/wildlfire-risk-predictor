import boto3
import requests as rq
from datetime import datetime
import os

MAP_KEY = os.getenv("map_key")
COUNTRY_CODE = "USA"
today = datetime.today().strftime("%Y-%m-%d")

# API URL
url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{MAP_KEY}/VIIRS_NOAA21_NRT/{COUNTRY_CODE}/7/{today}"

# Make request
response = rq.get(url, timeout=10)

if response.status_code == 200 and "Invalid" not in response.text:
    print("✅ Data fetched successfully.")

    # Save to /tmp (Lambda-style)
    file_name = f"/tmp/viirs_wildfire_{today}.csv"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(response.text)

    # Upload to S3
    s3 = boto3.client("s3")
    s3.upload_file(
        Filename=file_name,
        Bucket="your-bucket-name",  # <-- Replace with real bucket
        Key=f"raw/wildfires/{today}.csv"
    )
    print("✅ File uploaded to S3.")
else:
    print("❌ Failed to fetch data.")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
