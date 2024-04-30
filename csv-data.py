import boto3
import csv
import io
from datetime import datetime

# Configurações do cliente DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('Inventory')

# Esta função é acionada quando a Lambda é invocada
def insert_items_from_csv(event, context):
    try:
        # Caminho do arquivo CSV no S3
        s3_bucket = "unique-name-for-inventory-bucket-example"
        s3_key = "inventory_files/2024/04/29/202404291604_inventory.csv"

        # Baixar o arquivo CSV do S3
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        lines = response['Body'].read().decode('utf-8').split('\n')

        # Ler o arquivo CSV e inserir os dados no DynamoDB
        csv_reader = csv.DictReader(lines, delimiter=';')
        for row in csv_reader:
            try:
                timestamp = row['Timestamp']
                warehouse_name = row['WarehouseName']
                item_id = row['ItemId']
                item_name = row['ItemName']
                stock_level_change = int(row['StockLevelChange'])

                # Objeto de item para inserção no DynamoDB
                item = {
                    'Timestamp': timestamp,
                    'WarehouseName': warehouse_name,
                    'ItemId': item_id,
                    'ItemName': item_name,
                    'StockLevelChange': stock_level_change
                }

                # Inserir o item no DynamoDB
                table.put_item(Item=item)
                print(f"Inserido com sucesso: {item}")
            except Exception as e:
                print(f"Falha ao inserir: {str(e)}")

        print("Inserção de itens do CSV concluída.")
    except Exception as e:
        print(f"Falha ao processar o arquivo CSV: {str(e)}")
