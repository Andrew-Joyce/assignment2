import boto3

dynamodb = boto3.resource('dynamodb')

try:
    table = dynamodb.create_table(
        TableName='music',
        KeySchema=[
            {
                'AttributeName': 'title',
                'KeyType': 'HASH'  
            },
            {
                'AttributeName': 'artist',
                'KeyType': 'RANGE'  
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'title',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'artist',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )

    table.meta.client.get_waiter('table_exists').wait(TableName='music')
    print(f"Table {table.table_name} created successfully!")
except boto3.exceptions.botocore.client.ClientError as e:
    if e.response['Error']['Code'] == 'ResourceInUseException':
        print("Table already exists. Continue with the next operations.")
    else:
        raise
