import uuid

import pika
import json
import pandas as pd
import datetime
import os

from app.main import rabbitmq_user, rabbitmq_password, rabbitmq_host, rabbitmq_port


def process_file(file_path, uid):
    try:
        df = pd.read_excel(file_path)

        df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y')

        missing_sales_df = df[df['Date'].isna()]

        if not missing_sales_df.empty:
            output_file = os.path.join(os.path.dirname(file_path), "missing_sales_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".xlsx")
            missing_sales_df.to_excel(output_file, index=False)

            return output_file
        else:
            return "No missing sales found"
    except Exception as e:
        error_description = str(e)
        log_error(uid, error_description)
        raise


def on_request(ch, method, props, body):
    data = json.loads(body)
    file_path = data['file_path']
    uid = str(uuid.uuid4())

    print(f"Получен запрос на обработку файла: {file_path}")

    try:
        result_file = process_file(file_path, uid)

        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            body=json.dumps({'file_path': result_file}),
            properties=pika.BasicProperties(correlation_id=props.correlation_id)
        )
    except Exception as e:
        error_response = json.dumps({'error': str(e), 'uid': uid})
        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            body=error_response,
            properties=pika.BasicProperties(correlation_id=props.correlation_id)
        )

    ch.basic_ack(delivery_tag=method.delivery_tag)


credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port, credentials=credentials)
)
channel = connection.channel()
channel.queue_declare(queue='task_queue')


def callback(ch, method, properties, body):
    process_file(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue='task_queue', on_message_callback=callback, auto_ack=False)

print('Worker started. Waiting for messages...')
channel.start_consuming()
