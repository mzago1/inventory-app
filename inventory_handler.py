import boto3
import csv
import json
from datetime import datetime

# Conexão com o DynamoDB
ddb = boto3.resource('dynamodb')
inventory_table = ddb.Table('Inventory')

def handler(event, context):
    try:
        if 'Records' in event:
            for record in event['Records']:
                # Extrair informações do evento S3
                if 's3' in record and 'bucket' in record['s3'] and 'name' in record['s3']['bucket'] and 'object' in record['s3']:
                    bucket_name = record['s3']['bucket']['name']
                    object_key = record['s3']['object']['key']
                    
                    # Verificar se o arquivo é um arquivo de atualização de inventário
                    if object_key.startswith("inventory_files/") and object_key.endswith("_inventory.csv"):
                        # Ler o arquivo CSV do S3
                        s3 = boto3.client('s3')
                        response = s3.get_object(Bucket=bucket_name, Key=object_key)
                        lines = response['Body'].read().decode('utf-8').splitlines()
                        reader = csv.DictReader(lines, delimiter=';')

                        # Processar cada linha do arquivo CSV
                        for row in reader:
                            # Extrair dados da linha
                            timestamp = datetime.strptime(row['Timestamp'], '%Y-%m-%dT%H:%M:%S.%f%z')
                            warehouse_name = row['WarehouseName']
                            item_id = row['ItemId']
                            item_name = row['ItemName']
                            stock_level_change = int(row['StockLevelChange'])
                            
                            # Atualizar o item no DynamoDB
                            inventory_table.update_item(
                                Key={
                                    'ItemId': item_id,
                                    'WarehouseName': warehouse_name
                                },
                                UpdateExpression='ADD StockLevelChange :val',
                                ExpressionAttributeValues={
                                    ':val': stock_level_change
                                }
                            )
                            
                            print(f"Item {item_id} in warehouse {warehouse_name} updated in DynamoDB.")
                    else:
                        print(f"Skipping file {object_key}. Not an inventory update file.")
        
        return {
            'statusCode': 200,
            'body': 'Inventory update processed successfully'
        }
    except Exception as e:
        print("Error:", e)
        raise e
