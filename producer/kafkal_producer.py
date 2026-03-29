from kafka import KafkaProducer
import json

def send_job_to_kafka(job):
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    job = {
        "title": "Data Engineer",
        "company": "ABC Company",
        "location": "Hanoi"
    }

    producer.send("jobs-topic", job)
    producer.flush()

    print("Sent success!!!")