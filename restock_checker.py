import os
import boto3

def restock_checker(event, context):
    # AWS resource initialization
    dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
    sns_client = boto3.client('sns', region_name='eu-central-1')
    
    # Table names and SNS topic from environment variables
    inventory_table_name = 'Inventory'
    restock_table_name = 'Restock'
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    
    # DynamoDB Tables
    inventory_table = dynamodb.Table(inventory_table_name)
    restock_table = dynamodb.Table(restock_table_name)
    
    try:
        # Scan the Inventory table to find items below restock limit
        response = inventory_table.scan()
        items_to_restock = []
        
        for item in response['Items']:
            item_id = item['ItemId']
            warehouse_name = item['WarehouseName']
            stock_level_change = item['StockLevelChange']
            
            # Query the restock limit for the item in the Restock table
            restock_response = restock_table.get_item(Key={'ItemId': item_id})
            restock_item = restock_response.get('Item')
            
            if restock_item:
                restock_limit = restock_item.get('RestockIfBelow')
                
                if stock_level_change is not None and restock_limit is not None:
                    if stock_level_change < restock_limit:
                        items_to_restock.append((item_id, warehouse_name, stock_level_change, restock_limit))
        
        if items_to_restock:
            # If there are items to restock, send an email notification
            message = "Dear Manager,\n\nThe following items are below the restock limit:\n\n"
            for item in items_to_restock:
                message += f"Item ID: {item[0]}, at {item[1]}, has its current stock ({item[2]}) below the threshold limit ({item[3]})\n"
            message += "\nThis is an automated message."
            
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Message=message,
                Subject="Stock Alert"
            )
            print("Notification sent successfully!")
        else:
            print("No items found below restock limit.")
            
    except Exception as e:
        print(f"Error querying items below restock limit: {e}")

    return {
        'statusCode': 200,
        'body': 'Function executed successfully!'
    }
