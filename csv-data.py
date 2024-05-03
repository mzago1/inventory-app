import boto3
import csv
from io import StringIO
import os

# AWS resource initialization
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
sns_client = boto3.client('sns', region_name='eu-central-1')

# Table names and SNS topic from environment variables
inventory_table_name = 'Inventory'
restock_table_name = 'Restock'
sns_topic_arn = os.environ['SNS_TOPIC_ARN']

# DynamoDB tables
inventory_table = dynamodb.Table(inventory_table_name)
restock_table = dynamodb.Table(restock_table_name)

# Lambda function triggered by S3 event
def insert_items_from_csv(event, context):
    try:
        print("Received event:", event)
        
        # Check if 'Records' field exists in the event
        if 'Records' not in event:
            print("No 'Records' field found in the event.")
            return
        
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
                    response = inventory_table.get_item(
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
                    inventory_table.put_item(Item=item)
                    print(f"Successfully inserted/updated: {item}")

                    # Check if the item is below restock threshold
                    restock_response = restock_table.get_item(Key={'ItemId': item_id})
                    restock_item = restock_response.get('Item')
                    if restock_item:
                        restock_limit = restock_item.get('RestockIfBelow')
                        if new_stock_level < restock_limit:
                            # Item is below restock threshold, send notification
                            message = (f"Item ID: {item_id}, Warehouse Name: {warehouse_name} "
                                       f"has its current stock ({new_stock_level}) "
                                       f"below the threshold limit ({restock_limit})")
                            sns_client.publish(
                                TopicArn=sns_topic_arn,
                                Message=message,
                                Subject="Stock Alert"
                            )
                            print("Notification sent successfully!")

                except Exception as e:
                    print(f"Failed to process row: {str(e)}")

            print("CSV item insertion/update completed.")
    except Exception as e:
        print(f"Failed to process CSV file: {str(e)}")
