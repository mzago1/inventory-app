import json
import boto3

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Verifica se o evento contém a chave 'Records'
    if 'Records' in event:
        for record in event['Records']:
            # Obtém o nome do bucket e o nome do arquivo do evento
            bucket_name = record['s3']['bucket']['name']
            object_key = record['s3']['object']['key']
            
            # Verifica se o objeto é um arquivo de limiares de reabastecimento
            if object_key.startswith('restock_thresholds'):
                # Processa o arquivo de limiares de reabastecimento
                process_restock_thresholds(bucket_name, object_key)
            else:
                print(f"Object '{object_key}' não é um arquivo de limiares de reabastecimento. Ignorando.")
    else:
        print("Evento não contém a chave 'Records'.")
        return {
            'statusCode': 400,
            'body': json.dumps("Evento não contém a chave 'Records'.")
        }

def process_restock_thresholds(bucket_name, object_key):
    # Obtém o nome da tabela DynamoDB
    table_name = "Restock"  # Substitua pelo nome da sua tabela
    
    # Carrega o arquivo JSON de limiares de reabastecimento do S3
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        restock_thresholds = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"Falha ao carregar o arquivo '{object_key}' do bucket '{bucket_name}': {e}")
        raise e
    
    # Atualiza a tabela DynamoDB com os limiares de reabastecimento
    try:
        table = dynamodb.Table(table_name)
        with table.batch_writer() as batch:
            for threshold in restock_thresholds['ThresholdList']:
                item_id = threshold['ItemId']
                restock_if_below = threshold['RestockIfBelow']
                batch.put_item(Item={'ItemId': item_id, 'RestockIfBelow': restock_if_below})
        print(f"Limiares de reabastecimento atualizados com sucesso na tabela '{table_name}'.")
    except Exception as e:
        print(f"Falha ao atualizar os limiares de reabastecimento na tabela '{table_name}': {e}")
        raise e
