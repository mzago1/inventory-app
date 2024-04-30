import boto3
import csv
from io import StringIO
from decimal import Decimal

# DynamoDB client configuration
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('Inventory')

# Lambda function triggered by S3 event
def insert_items_from_csv(event, context):
    try:
        # Iterate over records in S3 event
        for record in event['Records']:
            # Extract information from S3 event record
            s3_bucket = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']

            # Download CSV file from S3
            s3_client = boto3.client('s3')
            response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            csv_body = response['Body'].read().decode('utf-8')

            # Read CSV file
            csv_data = csv.DictReader(StringIO(csv_body), delimiter=';')
            for row in csv_data:
                try:
                    timestamp = row['Timestamp']
                    warehouse_name = row['WarehouseName']
                    item_id = row['ItemId']
                    item_name = row['ItemName']
                    stock_level_change = int(row['StockLevelChange'])

                    # Check if the item exists in the DynamoDB table
                    response = table.get_item(
                        Key={'ItemId': item_id, 'WarehouseName': warehouse_name}
                    )
                    item_in_db = response.get('Item')

                    if item_in_db:
                        # Item exists in DynamoDB, update the stock level
                        current_stock_level = int(item_in_db['StockLevelChange'])
                        new_stock_level = current_stock_level + stock_level_change
                    else:
                        # Item doesn't exist in DynamoDB, set the initial stock level
                        new_stock_level = stock_level_change

                    # Put item into DynamoDB
                    item = {
                        'Timestamp': timestamp,
                        'WarehouseName': warehouse_name,
                        'ItemId': item_id,
                        'ItemName': item_name,
                        'StockLevelChange': new_stock_level
                    }
                    table.put_item(Item=item)
                    print(f"Successfully inserted/updated: {item}")

                except Exception as e:
                    print(f"Failed to process row: {str(e)}")

            print("CSV item insertion/update completed.")
    except Exception as e:
        print(f"Failed to process CSV file: {str(e)}")
