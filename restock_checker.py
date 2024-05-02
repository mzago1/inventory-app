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
    
    # Item ID to be queried
    item_id = '4a2792ab6d76b3e56b5e0caec8009d8bb97fe2ba7c5a9d9ba37a0940d46b96fd'
    
    # Warehouse name for the range key
    warehouse_name = 'HAMBURG I'  # Replace with the correct Warehouse name
    
    try:
        # Query the item quantity in the Inventory table
        inventory_response = inventory_table.get_item(Key={'ItemId': item_id, 'WarehouseName': warehouse_name})
        inventory_item = inventory_response.get('Item')
        
        # Query the restock limit for the item in the Restock table
        restock_response = restock_table.get_item(Key={'ItemId': item_id})
        restock_item = restock_response.get('Item')
        
        if inventory_item and restock_item:
            # If the item exists in both tables, extract the quantity and restock limit
            quantity = inventory_item.get('StockLevelChange')
            restock_limit = restock_item.get('RestockIfBelow')
            
            if quantity is not None and restock_limit is not None:
                # If quantity and limit are valid, check if quantity is below the limit
                if quantity < restock_limit:
                    # If quantity is below the limit, send an email notification
                    message = f"Dear Manager,\n\nThe quantity of item {item_id} ({quantity}) is below the restock limit ({restock_limit}).\n\nThis is an automated message."
                    sns_client.publish(
                        TopicArn=sns_topic_arn,
                        Message=message,
                        Subject="Stock Alert"
                    )
                    print("Notification sent successfully!")
                else:
                    print(f"The quantity of item {item_id} ({quantity}) is not below the restock limit ({restock_limit}).")
            else:
                print(f"The quantity ({quantity}) or the restock limit ({restock_limit}) for item {item_id} is invalid.")
        else:
            print(f"The item with ID {item_id} was not found in either the Inventory or Restock tables.")
            
    except Exception as e:
        print(f"Error querying the quantity of item {item_id}: {e}")

    return {
        'statusCode': 200,
        'body': 'Function executed successfully!'
    }
