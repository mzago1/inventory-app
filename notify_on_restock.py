import boto3

def lambda_handler(event, context):
    try:
        # Connecting to the SNS service
        sns = boto3.client('sns')
        
        # Email message
        subject = "New item for restock"
        message = "A new item has been added to the restock list."
        
        # Publishing the message to the SNS topic
        response = sns.publish(
            TopicArn='arn:aws:sns:eu-central-1:975050363201:restock_notifications_topic',
            Subject=subject,
            Message=message
        )
        
        print("Message published successfully:", response)
        
        return {
            'statusCode': 200,
            'body': 'Message published successfully'
        }
    except Exception as e:
        print("Error publishing message:", e)
        raise e
