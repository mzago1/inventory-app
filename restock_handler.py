import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')

def process_restock_thresholds(bucket_name, object_key):
    # Get the DynamoDB table name
    table_name = "Restock"  # Replace with your table name
    
    # Load the restock thresholds JSON file from S3
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        restock_thresholds = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to load file '{object_key}' from bucket '{bucket_name}': {e}")
        raise e
    
    # Update the DynamoDB table with the restock thresholds
    try:
        table = dynamodb.Table(table_name)
        with table.batch_writer() as batch:
            for threshold in restock_thresholds['ThresholdList']:
                item_id = threshold['ItemId']
                restock_if_below = threshold['RestockIfBelow']
                batch.put_item(Item={'ItemId': item_id, 'RestockIfBelow': restock_if_below})
                # Check if the item is below the restock threshold
                response = table.get_item(Key={'ItemId': item_id})
                item = response.get('Item')
                if item and 'StockLevelChange' in item:
                    current_stock_level = int(item['StockLevelChange'])
                    if current_stock_level < restock_if_below:
                        # The item is below the restock threshold, send notification
                        message = f"Item ID: {item_id} has stock level below the restock threshold."
                        sns_client.publish(
                            TopicArn=os.environ['SNS_TOPIC_ARN'],  # Use the environment variable for SNS topic ARN
                            Message=message,
                            Subject="Stock Alert"
                        )
                        print("Notification sent successfully!")
        print(f"Restock thresholds updated successfully in the '{table_name}' table.")
    except Exception as e:
        print(f"Failed to update restock thresholds in the '{table_name}' table: {e}")
        raise e

def lambda_handler(event, context):
    # Check if the event contains the 'Records' key
    if 'Records' in event:
        for record in event['Records']:
            # Get the bucket name and object key from the event
            bucket_name = record['s3']['bucket']['name']
            object_key = record['s3']['object']['key']
            
            # Check if the object is a restock thresholds file
            if object_key.startswith('restock_thresholds'):
                # Process the restock thresholds file
                process_restock_thresholds(bucket_name, object_key)
            else:
                print(f"Object '{object_key}' is not a restock thresholds file. Skipping.")
    else:
        print("Event does not contain the 'Records' key.")
        return {
            'statusCode': 400,
            'body': json.dumps("Event does not contain the 'Records' key.")
        }
