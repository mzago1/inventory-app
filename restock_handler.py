import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')

def process_restock_thresholds(bucket_name, object_key):
    # Get the DynamoDB table name
    table_name = "Restock"  # Replace with your table name
    
    # Extract date from the object key
    date_parts = object_key.split('/')[1:4]  # Extract year, month, day
    update_date = "/".join(date_parts)
    
    # Load the restock thresholds JSON file from S3
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        restock_thresholds = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to load file '{object_key}' from bucket '{bucket_name}': {e}")
        raise e
    
    item_ids_to_restock = []
    
    # Update the DynamoDB table with the restock thresholds
    try:
        table = dynamodb.Table(table_name)
        with table.batch_writer() as batch:
            for threshold in restock_thresholds['ThresholdList']:
                item_id = threshold['ItemId']
                restock_if_below = threshold['RestockIfBelow']
                batch.put_item(Item={'ItemId': item_id, 'RestockIfBelow': restock_if_below})
                item_ids_to_restock.append(item_id)
                
        print(f"Restock thresholds updated successfully in the '{table_name}' table.")
    except Exception as e:
        print(f"Failed to update restock thresholds in the '{table_name}' table: {e}")
        raise e
    
    return item_ids_to_restock, update_date

def send_notification(item_ids, update_date):
    try:
        # Get the DynamoDB table name
        table_name = "Inventory"
        table = dynamodb.Table(table_name)
        
        # Prepare the message with all item IDs
        message = f"Dear manager,\n\n After the new JSON update on {update_date}, the following items have stock levels below the threshold and require your attention:\n"
        for item_id in item_ids:
            message += f"- Item ID: {item_id}\n"
        
        message += "\nThis is an automated email."
        
        # Send the notification if there are items to restock
        if item_ids:
            sns_client.publish(
                TopicArn=os.environ['SNS_TOPIC_ARN'],  # Use the environment variable for SNS topic ARN
                Message=message,
                Subject="Stock Alert"
            )
            print("Notification sent successfully!")
    except Exception as e:
        print(f"Failed to send notification: {e}")

def lambda_handler(event, context):
    # Check if the event contains the 'Records' key
    if 'Records' in event:
        item_ids_to_restock = []
        update_dates = []
        for record in event['Records']:
            # Get the bucket name and object key from the event
            bucket_name = record['s3']['bucket']['name']
            object_key = record['s3']['object']['key']
            
            # Check if the object path structure is correct
            if object_key.startswith('restock_thresholds/') and object_key.endswith('/restock_thresholds.json'):
                # Process the restock thresholds file
                item_ids, update_date = process_restock_thresholds(bucket_name, object_key)
                item_ids_to_restock.extend(item_ids)
                update_dates.append(update_date)
            else:
                print(f"Object '{object_key}' does not match the expected path structure for restock thresholds files. Skipping.")
        
        # Send a single notification with all item IDs to restock
        if item_ids_to_restock:
            unique_dates = list(set(update_dates))  # Get unique update dates
            for date in unique_dates:
                send_notification(item_ids_to_restock, date)
    else:
        print("Event does not contain the 'Records' key.")
        return {
            'statusCode': 400,
            'body': json.dumps("Event does not contain the 'Records' key.")
        }
