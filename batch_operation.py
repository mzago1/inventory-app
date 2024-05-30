import json
import boto3
import time
import os

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
    
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    if 'Messages' not in response:
        # Send SNS notification if no messages are left in the queue
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message="The Step Function execution has succeeded. No messages left in the SQS queue.",
            Subject="Step Function Execution Succeeded"
        )
        
        return {
            'statusCode': 200,
            'body': 'No messages to process',
            'queueEmpty': True
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
        'body': 'Message processed successfully',
        'queueEmpty': False
    }
