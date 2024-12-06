import boto3
import csv
import pg8000
import os
from datetime import datetime
from collections import defaultdict

s3 = boto3.client('s3')

def lambda_handler(event, context):
    bucket_name = event['bucket_name']
    file_name = event['file_name']
    tmp_file = f"/tmp/{file_name}"

    tmp_dir = os.path.dirname(tmp_file)
    if not os.path.exists(tmp_dir):
        try:
            os.makedirs(tmp_dir)  
            print(f"Diretório {tmp_dir} criado com sucesso.")
        except Exception as e:
            print(f"Erro ao criar diretório: {e}")
            return {"status": "error", "message": f"Erro ao criar diretório: {e}"}

    try:
        s3.download_file(bucket_name, file_name, tmp_file)
    except Exception as e:
        print(f"Error downloading file: {e}")
        return {"status": "error", "message": f"Error downloading file: {e}"}

    if not os.path.exists(tmp_file):
        return {"status": "error", "message": f"File not found: {tmp_file}"}


    results = defaultdict(int)
    try:
        with open(tmp_file, 'r', encoding="utf-8", errors='replace') as f:
            reader = csv.DictReader(f, delimiter=';')
            vehicle_columns = ['automovel', 'bicicleta', 'caminhao', 'moto', 'onibus', 'outros']

            for row in reader:
                road_name = row.get('trecho', 'N/A')
                for vehicle in vehicle_columns:
                    if vehicle in row and row[vehicle].isdigit() and int(row[vehicle]) > 0:
                        results[(road_name, vehicle)] += int(row[vehicle])
    except Exception as e:
        return {"status": "error", "message": f"Erro ao processar o arquivo CSV: {e}"}
    
    formatted_results = [
        {
            "created_at": datetime.now(),
            "road_name": road_name,
            "vehicle": vehicle,
            "number_deaths": number_deaths
        }
        for (road_name, vehicle), number_deaths in results.items()
    ]

    try:
        conn = pg8000.connect(
            host=os.environ['DB_HOST'],
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASS'],
            port=int(os.environ.get('DB_PORT', 5432))
        )
        cursor = conn.cursor()

        for result in formatted_results:
            cursor.execute("""
                INSERT INTO accident_data (created_at, road_name, vehicle, number_deaths)
                VALUES (%s, %s, %s, %s)
            """, (result['created_at'], result['road_name'], result['vehicle'], result['number_deaths']))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return {"status": "error", "message": f"Error inserting data into database: {e}"}

    for result in formatted_results:
        result['created_at'] = result['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    return {"status": "success", "processed_records": len(formatted_results), "data": formatted_results}