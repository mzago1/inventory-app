import boto3
import csv
import json
from io import StringIO
from datetime import datetime
import os

# AWS resource initialization
ddb = boto3.resource('dynamodb')
inventory_table = ddb.Table('Inventory')
restock_table = ddb.Table('Restock')
sns_client = boto3.client('sns', region_name='eu-central-1')
sqs_client = boto3.client('sqs', region_name='eu-central-1')
sqs_queue_url = os.environ['SQS_QUEUE_URL']

def handler(event, context):
    try:
        print("Received event:", event)
        
        if 'Records' in event:
            # Lambda triggered by S3 event
            for record in event['Records']:
                # Extract S3 bucket and key
                if 's3' in record and 'bucket' in record['s3'] and 'name' in record['s3']['bucket'] and 'object' in record['s3']:
                    bucket_name = record['s3']['bucket']['name']
                    object_key = record['s3']['object']['key']
                    
                    # Check if the file is an inventory update file
                    if object_key.startswith("inventory_files/") and object_key.endswith("_inventory.csv"):
                        # Read the CSV file from S3
                        s3 = boto3.client('s3')
                        response = s3.get_object(Bucket=bucket_name, Key=object_key)
                        csv_body = response['Body'].read().decode('utf-8')

                        # Process each row of the CSV file
                        csv_data = csv.DictReader(StringIO(csv_body), delimiter=';')
                        for row in csv_data:
                            try:
                                timestamp = datetime.strptime(row['Timestamp'], '%Y-%m-%dT%H:%M:%S.%f%z')
                                warehouse_name = row['WarehouseName']
                                item_id = row['ItemId']
                                item_name = row['ItemName']
                                stock_level_change = int(row['StockLevelChange'])

                                # Update the item in DynamoDB
                                inventory_table.update_item(
                                    Key={'ItemId': item_id, 'WarehouseName': warehouse_name},
                                    UpdateExpression='ADD StockLevelChange :val',
                                    ExpressionAttributeValues={':val': stock_level_change}
                                )

                                print(f"Item {item_id} in warehouse {warehouse_name} updated in DynamoDB.")

                                # Check if the item is below restock threshold
                                restock_response = restock_table.get_item(Key={'ItemId': item_id})
                                restock_item = restock_response.get('Item')
                                if restock_item:
                                    restock_limit = restock_item.get('RestockIfBelow')
                                    response = inventory_table.get_item(
                                        Key={'ItemId': item_id, 'WarehouseName': warehouse_name}
                                    )
                                    item_in_db = response.get('Item')
                                    if item_in_db:
                                        current_stock_level = int(item_in_db.get('StockLevelChange', 0))
                                        if current_stock_level < restock_limit:
                                            # Item is below restock threshold, send notification
                                            message = (f"Item ID: {item_id}, Warehouse Name: {warehouse_name} "
                                                       f"has its current stock ({current_stock_level}) "
                                                       f"below the threshold limit ({restock_limit})")
                                            sns_client.publish(
                                                TopicArn=os.environ['SNS_TOPIC_ARN'],
                                                Message=message,
                                                Subject="Stock Alert"
                                            )
                                            print("Notification sent successfully!")

                            except Exception as e:
                                print(f"Failed to process row: {str(e)}")
                        
                        # Send CSV to SQS
                        sqs_client.send_message(
                            QueueUrl=sqs_queue_url,
                            MessageBody=json.dumps({"bucket": bucket_name, "key": object_key, "content": csv_body})
                        )
                        print(f"CSV file {object_key} sent to SQS.")

                    else:
                        print(f"Skipping file {object_key}. Not an inventory update file.")
        
        return {
            'statusCode': 200,
            'body': 'Inventory update processed successfully'
        }
    except Exception as e:
        print("Error:", e)
        raise e
