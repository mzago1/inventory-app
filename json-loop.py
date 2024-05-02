import boto3
import json
import datetime

# DynamoDB client settings
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('Restock')

# Function to insert items into DynamoDB from a JSON file
def insert_items_from_json(json_body):
    json_data = json.loads(json_body)
    current_time = datetime.datetime.utcnow().isoformat() + 'Z'  # Get current time in ISO 8601 format
    for threshold in json_data['ThresholdList']:
        try:
            item_id = threshold['ItemId']
            restock_if_below = int(threshold['RestockIfBelow'])

            # Item object for insertion into DynamoDB
            item = {
                'Timestamp': current_time,  # Using the current timestamp
                'ItemId': item_id,
                'RestockIfBelow': restock_if_below
            }

            # Insert item into DynamoDB
            table.put_item(Item=item)
            print(f"Successfully inserted: {item}")
        except Exception as e:
            print(f"Failed to insert: {str(e)}")

# S3 client settings
s3_client = boto3.client('s3')

# Name of your S3 bucket
bucket_name = "unique-name-for-inventory-bucket-example"

# Prefix of the directory in your S3 bucket
prefix = "restock_thresholds/"

# List objects in the S3 bucket
response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

# Iterate over the found objects
for obj in response.get('Contents', []):
    # Get the object name (key)
    object_key = obj['Key']
    
    # Get the S3 object
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    
    # Read the body of the JSON file
    json_body = response['Body'].read().decode('utf-8')
    
    # Process the JSON file and insert items into DynamoDB
    insert_items_from_json(json_body)

print("Insertion of items from all JSON files completed.")
