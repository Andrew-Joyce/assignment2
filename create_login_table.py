import boto3
import time

dynamodb = boto3.client('dynamodb')

table_name = 'login'

table_schema = [
    {
        'AttributeName': 'email',
        'KeyType': 'HASH' 
    }
]

provisioned_throughput = {
    'ReadCapacityUnits': 5,
    'WriteCapacityUnits': 5
}

try:
    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=table_schema,
        AttributeDefinitions=[
            {
                'AttributeName': 'email',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput=provisioned_throughput
    )
    print(f"Table '{table_name}' creation initiated.")
except dynamodb.exceptions.ResourceInUseException:
    print(f"Table '{table_name}' already exists.")

time.sleep(10) 

table_status = dynamodb.describe_table(TableName=table_name)['Table']['TableStatus']
if table_status == 'ACTIVE':
    print(f"Table '{table_name}' created successfully.")
else:
    print(f"Table '{table_name}' creation failed or still in progress. Table status: {table_status}")

for i in range(10):
    email = f"s3876520{i}@student.rmit.edu.au"
    username = f"AndrewJoyce{i}"
    password = f"{i}01234"

    try:
        response = dynamodb.put_item(
            TableName=table_name,
            Item={
                'email': {'S': email},
                'username': {'S': username},
                'password': {'S': password}
            }
        )
        print(f"Entity {i + 1} added successfully.")
    except Exception as e:
        print(f"Failed to add entity {i + 1}: {e}")
