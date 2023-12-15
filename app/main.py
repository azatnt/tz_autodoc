from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import pika
import json
import uuid
import os


app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
FILES_DIR = os.path.join(BASE_DIR, "files")

rabbitmq_host = os.getenv('RABBITMQ_HOST', '')
rabbitmq_port = int(os.getenv('RABBITMQ_PORT', ''))
rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER', '')
rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS', '')


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(FILES_DIR, f"temp_{file.filename}")
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port, credentials=credentials)
    )
    channel = connection.channel()
    channel.queue_declare(queue='task_queue')

    # Publish a message to the queue with the file path
    correlation_id = str(uuid.uuid4())
    response_queue = channel.queue_declare(queue='', exclusive=True).method.queue
    channel.basic_publish(
        exchange='',
        routing_key='task_queue',
        body=json.dumps({'file_path': file_location}),
        properties=pika.BasicProperties(
            reply_to=response_queue,
            correlation_id=correlation_id,
        )
    )

    response = {}

    def on_response(ch, method, props, body):
        if props.correlation_id == correlation_id:
            nonlocal response
            response = json.loads(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            ch.stop_consuming()

    channel.basic_consume(
        queue=response_queue,
        on_message_callback=on_response,
        auto_ack=False
    )

    channel.start_consuming()
    connection.close()

    if 'file_path' in response:
        file_path = os.path.join(FILES_DIR, os.path.basename(response['file_path']))
        return FileResponse(path=file_path, filename=os.path.basename(file_path))
    else:
        return {"error": response.get("error", "Unknown Error")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
