import json
import boto3
import time
import os

sqs = boto3.client('sqs')
s3 = boto3.client('s3')

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
    QUEUE_URL = os.environ['QUEUE_URL']

    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    if 'Messages' not in response:
        return {
            'statusCode': 200,
            'body': json.dumps('No messages to process'),
            'queueUrl': QUEUE_URL
        }

    for message in response['Messages']:
        body = json.loads(message['Body'])
        bucket = body['bucket']
        key = body['key']

        process_file(bucket, key)

        sqs.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=message['ReceiptHandle']
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Message processed successfully'),
        'queueUrl': QUEUE_URL
    }
