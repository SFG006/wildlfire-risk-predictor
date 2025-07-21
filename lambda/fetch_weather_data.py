import boto3
import json
import os
import csv
import requests as rq
from datetime import datetime
from io import StringIO


s3 = boto3.client('s3')
WEATHER_API_KEY = os.getenv('api_key')

def lambda_handler(event, context):
    BUCKET_NAME = os.getenv("bucket_name")
    today = datetime.today().strftime('%Y-%m-%d')
    wildfire_key = f"raw/wildfires/{today}.csv"
    output_key = f"processed/wildfires_weather_enriched_{today}.json"

    # Step 1: Read wildfire CSV from S3
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=wildfire_key)
        csv_content = response['Body'].read().decode('utf-8')
        print("✅ Wildfire CSV fetched.")
    except Exception as e:
        print("❌ Error fetching wildfire CSV:", e)
        return {
            'statusCode': 500,
            'body': "Failed to fetch wildfire data.",
        }
    # Step 2: Parse CSV and filter high-confidence
    reader = csv.DictReader(StringIO(csv_content))
    high_confidence_rows = []

    for row in reader:
        if row.get("confidence") == "h":
            try:
                row["frp"] = float(row.get("frp", 0))
                high_confidence_rows.append(row)

            except ValueError:   # when their is no value so skip that row
                continue

    # Step 3: Sort and select top 10 by FRP
    top_hotspots = sorted(high_confidence_rows, key=lambda row: row["frp"], reverse=True)[:10]
    print("✅ Top 10 high-confidence hotspots selected.")

    # Step 4: Enrich each hotspot with weather info
    enriched = []

    for row in top_hotspots:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            if not lat or not lon:
                continue

            weather_url =  (
                f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
            )

            weather_response = rq.get(weather_url)

            if weather_response.status_code == 200:
                weather_data = weather_response.json()


                row["temp_c"] = weather_data["main"].get("temp")  # Temperature (Celsius)
                row["feels_like_c"] = weather_data["main"].get("feels_like")  # Feels-like temperature
                row["humidity"] = weather_data["main"].get("humidity")  # Humidity (%)
                row["pressure"] = weather_data["main"].get("pressure")  # Atmospheric pressure (hPa)
                row["wind_speed"] = weather_data["wind"].get("speed")  # Wind speed (m/s)
                row["wind_gust"] = weather_data["wind"].get("gust")  # Wind gust (m/s)
                row["wind_deg"] = weather_data["wind"].get("deg")  # Wind direction (degrees)
                row["cloud_cover"] = weather_data["clouds"].get("all")  # Cloudiness (%)
                row["weather_desc"] = weather_data["weather"][0].get("description")  # Weather condition description

            else:
                print(f"⚠️ Weather API error for ({lat}, {lon}) — Code:", weather_response.status_code)

            enriched.append(row)

        except Exception as e:
            print("⚠️ Skipped a row due to error:", e)

    # Step 5: Upload enriched data to S3
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=output_key,
            Body=json.dumps(enriched),
            ContentType="application/json",
        )
        print(f"✅ Enriched data written to S3: {output_key}")
        return {
            'statusCode': 200,
            'body': f"Successfully saved enriched data to {output_key}",
        }
    except Exception as e:
        print("❌ Failed to write enriched JSON to S3:", e)
        return {
            "statusCode": 500,
            "body": "Failed to upload enriched data."
        }
