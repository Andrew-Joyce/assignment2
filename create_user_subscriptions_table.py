import boto3

def create_user_subscriptions_table(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')

    table_name = 'user_subscriptions'
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'  
                },
                {
                    'AttributeName': 'music_id',
                    'KeyType': 'RANGE'  
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'music_id',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"Table '{table_name}' creation initiated, waiting for it to be created...")
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"Table '{table_name}' created successfully.")
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")

if __name__ == '__main__':
    create_user_subscriptions_table()
