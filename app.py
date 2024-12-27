from flask import Flask, request, jsonify
import boto3
import os
import time

app = Flask(__name__)

# Initialize Textract and S3 clients
textract = boto3.client('textract')
s3 = boto3.client('s3')

# Configure your S3 bucket
S3_BUCKET = 'your-s3-bucket-name'  # Replace with your S3 bucket name

@app.route('/')
def home():
    return jsonify({"message": "Welcome to InsightDocuments MVP!"})

@app.route('/extract', methods=['POST'])
def extract_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    file_path = os.path.join('uploads', file.filename)

    # Save the uploaded file locally
    os.makedirs('uploads', exist_ok=True)
    file.save(file_path)

    try:
        # Upload file to S3
        s3.upload_file(file_path, S3_BUCKET, file.filename)
        document_location = {
            'S3Object': {
                'Bucket': S3_BUCKET,
                'Name': file.filename
            }
        }

        # Start Textract job
        response = textract.start_document_analysis(
            DocumentLocation=document_location,
            FeatureTypes=['TABLES', 'FORMS']
        )

        # Extract the job ID
        job_id = response['JobId']

        # Poll for job completion
        while True:
            job_status = textract.get_document_analysis(JobId=job_id)
            status = job_status['JobStatus']
            if status in ['SUCCEEDED', 'FAILED']:
                break
            time.sleep(2)

        if status == 'FAILED':
            return jsonify({"error": "Textract job failed"}), 500

        # Extract text blocks from the completed job
        blocks = job_status.get('Blocks', [])
        extracted_text = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']

        return jsonify({"extracted_text": extracted_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)