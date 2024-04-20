import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

app = Flask(__name__)
app.secret_key = 'andrew_joyce'

dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
music_table = dynamodb.Table('music')

def check_credentials(email, password):
    try:
        response = boto3.client('dynamodb').get_item(
            TableName='login',
            Key={
                'email': {'S': email.strip()}
            }
        )
        if 'Item' in response:
            stored_password = response['Item'].get('password', {}).get('S')
            if stored_password == password:
                return True, email
            else:
                return False, None
        else:
            return False, None
    except ClientError as e:
        error_message = f"Error accessing DynamoDB table: {e.response['Error']['Message']}"
        print(error_message)
        print(e.response)
        return False, None

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']  
        password = request.form['password']  
        authenticated, _ = check_credentials(email, password)  
        if authenticated:
            session['logged_in'] = True  
            session['email'] = email  
            app.logger.debug(f"User logged in: {email}")  
            return redirect(url_for('main_page'))  
        else:
            flash('Email or password is invalid')  
    return render_template('login.html') 


@app.route('/main_page', methods=['GET', 'POST'])
def main_page():
    if 'logged_in' in session and session['logged_in']:
        email = session.get('email')

        if not email:
            flash('User email not found in session', 'error')
            return redirect(url_for('logout'))

        subscriptions = []

        try:
            response = music_table.scan(
                FilterExpression=Attr('subscriptions').contains(email)
            )
            subscriptions = response['Items']
        except ClientError as e:
            logging.error(f"Error fetching user subscriptions: {e.response['Error']['Message']}")
            flash('An error occurred while fetching your subscriptions.', 'error')

        results = []

        if request.method == 'POST':
            title = request.form.get('title', '')
            artist = request.form.get('artist', '')
            year = request.form.get('year', '')

            condition = None
            if title:
                condition = Attr('title').contains(title)
            if artist:
                condition = (condition & Attr('artist').contains(artist)) if condition else Attr('artist').contains(artist)
            if year:
                condition = (condition & Attr('year').contains(year)) if condition else Attr('year').contains(year)

            if condition:
                response = music_table.scan(FilterExpression=condition)
                results = response['Items']

        return render_template('main_page.html', results=results, subscriptions=subscriptions)

    else:
        return redirect(url_for('login'))


@app.route('/search', methods=['POST'])
def search_music():
    title = request.form.get('title', '')
    artist = request.form.get('artist', '')
    year = request.form.get('year', '')

    condition = None
    if title:
        condition = Attr('title').eq(title)
    if artist:
        condition = (condition & Attr('artist').eq(artist)) if condition else Attr('artist').eq(artist)
    if year:
        condition = (condition & Attr('year').eq(year)) if condition else Attr('year').eq(year)

    if condition:
        response = music_table.scan(FilterExpression=condition)
        results = response['Items']
    else:
        results = []

    return render_template('main_page.html', results=results)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    if 'logged_in' in session:
        email = session.get('email')
        data = request.get_json()
        title = data.get('title')
        artist = data.get('artist')

        if not email or not title or not artist:
            return jsonify({'error': 'Missing title or artist data for subscription.'}), 400

        try:
            response = music_table.update_item(
                Key={
                    'title': title,
                    'artist': artist
                },
                UpdateExpression="SET subscriptions = list_append(if_not_exists(subscriptions, :empty_list), :email)",
                ExpressionAttributeValues={
                    ':email': [email],
                    ':empty_list': [],
                },
                ReturnValues="UPDATED_NEW"
            )
            
            subscribed_music = {
                'title': title,
                'artist': artist,
                'img_url': data.get('img_url')  
            }
            
            return jsonify({'success': 'Subscription added successfully!', 'subscribed_music': subscribed_music}), 200
        except ClientError as e:
            logging.error(f"Error subscribing to music: {e.response['Error']['Message']}")
            return jsonify({'error': f"An error occurred while subscribing to music: {e.response['Error']['Message']}"}), 500
    else:
        return jsonify({'error': 'You must be logged in to subscribe.'}), 401

from botocore.exceptions import ClientError

@app.route('/remove_subscription', methods=['POST'])
def remove_subscription():
    if 'logged_in' in session and session.get('email'):
        email = session['email'] 
        data = request.get_json()
        title = data.get('title')
        artist = data.get('artist')

        if not title or not artist:
            logging.error("Missing title or artist data for removing subscription.")
            return jsonify({'error': 'Missing title or artist data for removing subscription.'}), 400

        try:
            dynamodb = boto3.resource('dynamodb')
            music_table = dynamodb.Table('music')
            response = music_table.get_item(
                Key={
                    'title': title,
                    'artist': artist
                }
            )
            item = response.get('Item')
            if not item:
                logging.error(f"Music item not found: {title}, {artist}")
                return jsonify({'error': 'Music item not found.'}), 404

            subscriptions = item.get('subscriptions', [])
            if email in subscriptions:
                subscriptions.remove(email)
                response = music_table.update_item(
                    Key={
                        'title': title,
                        'artist': artist
                    },
                    UpdateExpression="SET subscriptions = :subscriptions",
                    ExpressionAttributeValues={
                        ':subscriptions': subscriptions
                    },
                    ReturnValues="UPDATED_NEW"
                )
                logging.info(f"Subscription removed successfully for user: {email} on music: {title}, {artist}")
                return jsonify({'success': 'Subscription removed successfully!'}), 200
            else:
                logging.error(f"User {email} is not subscribed to this music: {title}, {artist}")
                return jsonify({'error': 'User is not subscribed to this music.'}), 400

        except ClientError as e:
            logging.error(f"Error removing subscription: {e.response['Error']['Message']}")
            return jsonify({'error': f"An error occurred while removing subscription: {e.response['Error']['Message']}"}), 500
    else:
        logging.error("Attempt to remove subscription without being logged in or missing email in session.")
        return jsonify({'error': 'You must be logged in and email must be present to remove subscription.'}), 401


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('subscriptions', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
