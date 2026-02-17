# Mini Resume Collector API

## Python Version
Python 3.10+

## Installation
pip install -r requirements.txt

## Run Application
uvicorn main:app --reload

Server runs at:
http://127.0.0.1:8000

## API Documentation
http://127.0.0.1:8000/docs

## Example Request

POST /candidate

{
  "name": "Christina Jibin",
  "email": "christinajibin274@gmail.com",
  "phone": "8714512078",
  "skills": ["Python", "FastAPI"]
}

Response:
{
  "message": "Candidate added successfully",
  "id": "generated-id"
}
