import json
import boto3
import time
import os

sqs = boto3.client('sqs')
s3 = boto3.client('s3')
sns = boto3.client('sns')

QUEUE_URL = os.environ['SQS_QUEUE_URL']  # Updated environment variable name
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

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
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )
    
    if 'Messages' not in response:
        return {
            'statusCode': 200,
            'body': json.dumps('No messages to process')
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
        
        # Publish notification to SNS
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=f'Validation of transactions in file {key} from bucket {bucket} has been completed.'
        )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Message processed and notification sent successfully')
    }
