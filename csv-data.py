import boto3
import csv
from io import StringIO

# DynamoDB client configuration
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('Inventory')

# Lambda function triggered by S3 event
def insert_items_from_csv(event, context):
    try:
        # Dictionary to store last stock level for each item
        last_stock_levels = {}

        # Iterate over records in S3 event
        for record in event['Records']:
            # Extract information from S3 event record
            s3_bucket = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']

            # Download CSV file from S3
            s3_client = boto3.client('s3')
            response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            lines = response['Body'].read().decode('utf-8').split('\n')

            # Read CSV file and update stock levels for each item
            csv_reader = csv.DictReader(lines, delimiter=';')
            for row in csv_reader:
                try:
                    timestamp = row['Timestamp']
                    warehouse_name = row['WarehouseName']
                    item_id = row['ItemId']
                    item_name = row['ItemName']
                    stock_level_change = int(row['StockLevelChange'])

                    # Get the last stock level for the item
                    last_stock_level = last_stock_levels.get(item_id, 0)

                    # Calculate the new stock level
                    new_stock_level = stock_level_change + last_stock_level

                    # Update the last stock level for the item
                    last_stock_levels[item_id] = new_stock_level

                    # Item object for insertion into DynamoDB
                    item = {
                        'Timestamp': timestamp,
                        'WarehouseName': warehouse_name,
                        'ItemId': item_id,
                        'ItemName': item_name,
                        'StockLevelChange': new_stock_level
                    }

                    # Insert item into DynamoDB
                    table.put_item(Item=item)
                    print(f"Successfully inserted: {item}")
                except Exception as e:
                    print(f"Failed to process row: {str(e)}")

            print("CSV item insertion completed.")
    except Exception as e:
        print(f"Failed to process CSV file: {str(e)}")
