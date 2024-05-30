import json
import boto3
import time
import os
from datetime import datetime

sqs = boto3.client('sqs')
s3 = boto3.client('s3')
sns = boto3.client('sns')

def check_transaction(transaction):
    """Long and complex check for each transaction"""
    time.sleep(10)  # "Process" for 10 seconds

def process_file(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')

    transactions = content.split('\n')[1:]  # Skip header
    for transaction in transactions:
        if transaction:
            check_transaction(transaction)

def lambda_handler(event, context):
    QUEUE_URL = os.environ.get('QUEUE_URL')
    SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')  # Get the SNS topic ARN from environment variables

    if not SNS_TOPIC_ARN:
        raise ValueError("SNS_TOPIC_ARN environment variable is not set")
    
    start_time = datetime.now()  # Get the start time

    files_processed = []  # List to store processed files
    
    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )

        if 'Messages' not in response:
            # If no messages left in the queue, break the loop
            break

        for message in response['Messages']:
            body = json.loads(message['Body'])
            bucket = body['bucket']
            key = body['key']
            
            files_processed.append(key)  # Add processed file to the list

            process_file(bucket, key)

            sqs.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )

    # Calculate the total execution time
    finish_time = datetime.now()
    duration = finish_time - start_time

    # Send SNS notification with files processed information
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=f"The Step Function execution has succeeded. No messages left in the SQS queue.\n\nStart Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\nFinish Time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}\nDuration: {duration}\n\nNumber of files: {len(files_processed)}\nFiles processed: {files_processed}",
        Subject="Step Function Execution Succeeded"
    )

    return {
        'statusCode': 200,
        'body': 'Message processed successfully',
        'queueEmpty': True,
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')  # Return the start time
    }
