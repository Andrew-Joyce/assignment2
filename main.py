from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'andrew_joyce'

dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')

def check_credentials(email, password):
    print(f"Checking credentials for email: '{email}', password: '{password}'")
    try:
        response = dynamodb.get_item(
            TableName='login',
            Key={
                'email': {'S': email.strip()}
            }
        )
        print(f"DynamoDB response: {response}")
        if 'Item' in response:
            stored_password = response['Item'].get('password', {}).get('S')
            if stored_password == password:
                return True, email
            else:
                print("Incorrect password retrieved from DynamoDB:", stored_password)
                return False, None
        else:
            print("No item found in DynamoDB for email:", email)
            return False, None
    except ClientError as e:
        error_message = f"Error accessing DynamoDB table: {e.response['Error']['Message']}"
        print(error_message)
        print(e.response)
        return False, None

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        authenticated, _ = check_credentials(email, password)
        if authenticated:
            return redirect(url_for('main_page'))
        else:
            error = 'Email or password is invalid'
        
    return render_template('login.html', error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        try:
            response = dynamodb.get_item(
                TableName='login',
                Key={
                    'email': {'S': email}
                }
            )
            if 'Item' in response:
                flash('Email already registered. Please log in or use a different email.')
                return redirect(url_for('register'))
            else:
                dynamodb.put_item(
                    TableName='login',
                    Item={
                        'email': {'S': email},
                        'username': {'S': username},
                        'password': {'S': password}  
                    }
                )
                flash('Registration successful. Please log in.')
                return redirect(url_for('login'))
        except ClientError as e:
            flash(f"Error accessing DynamoDB: {e.response['Error']['Message']}")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route("/main_page", methods=["GET"])
def main_page():
    return "Welcome to the Main Page! You are logged in."

if __name__ == "__main__":
    app.run(debug=True)
