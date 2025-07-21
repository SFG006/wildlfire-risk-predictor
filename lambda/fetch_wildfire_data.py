import os
import boto3
import requests as rq
from datetime import datetime

def lambda_handler(event, context):
    # ✅ Configuration
    MAP_KEY = os.getenv("map_key")
    COUNTRY_CODE = "USA"
    BUCKET_NAME = os.getenv("bucket_name")
    today = datetime.today().strftime("%Y-%m-%d")

    # 🔗 NASA FIRMS API URL
    api_url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/"
        f"{MAP_KEY}/VIIRS_NOAA21_NRT/{COUNTRY_CODE}/7/{today}"
    )

    try:
        # 📡 Make API Request
        response = rq.get(api_url, timeout=10)

        # ✅ Check if data is valid
        if response.status_code == 200 and "Invalid" not in response.text:
            print("✅ Data fetched successfully.")

            # 💾 Save data to /tmp (Lambda's writeable directory)
            file_name = f"/tmp/viirs_wildfire_{today}.csv"
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(response.text)

            # ☁️ Upload CSV to S3
            s3 = boto3.client("s3")
            s3.upload_file(
                Filename=file_name,
                Bucket=BUCKET_NAME,
                Key=f"raw/wildfires/{today}.csv"
            )

            print("✅ File uploaded to S3.")

        else:
            print("❌ Failed to fetch data.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)

    except rq.exceptions.RequestException as e:
        print("🚨 Request failed due to an exception:", str(e))

    except Exception as e:
        print("🚨 An unexpected error occurred:", str(e))
