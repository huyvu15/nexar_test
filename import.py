from google.cloud import bigquery
import os
import json
import gzip
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account
import tempfile

# Đường dẫn tới file credentials
key_path = "credentials.json"

# Tạo credentials từ file key
credentials = service_account.Credentials.from_service_account_file(
    key_path,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

# Khởi tạo BigQuery client với credentials
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Định nghĩa thông tin dataset và table
dataset_id = "game_analytics"
table_id = "game_events"
full_table_id = f"{client.project}.{dataset_id}.{table_id}"

# Tạo dataset nếu chưa tồn tại
try:
    client.get_dataset(dataset_id)
    print(f"Dataset {dataset_id} đã tồn tại")
except NotFound:
    dataset = bigquery.Dataset(f"{client.project}.{dataset_id}")
    dataset.location = "US"  # Chọn vị trí phù hợp
    dataset = client.create_dataset(dataset)
    print(f"Dataset {dataset_id} đã được tạo")

# Tải schema từ file
with open('schema.json', 'r') as schema_file:
    schema = json.load(schema_file)
schema = [bigquery.SchemaField.from_api_repr(field) for field in schema]

# Tạo bảng với schema
table = bigquery.Table(full_table_id, schema=schema)
try:
    client.get_table(table)
    print(f"Bảng {table_id} đã tồn tại")
except NotFound:
    table = client.create_table(table)
    print(f"Bảng {table_id} đã được tạo")

# Hàm xử lý và tải các file JSON-ND GZIP bằng load job
def load_data_from_gzip(file_path):
    try:
        # Tạo file tạm thời để chứa dữ liệu JSON giải nén
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_file_name = temp_file.name
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    temp_file.write(line.encode('utf-8'))

        # Cấu hình job để tải dữ liệu
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND  # Thêm dữ liệu vào bảng
        )

        # Tải dữ liệu từ file tạm thời
        with open(temp_file_name, "rb") as source_file:
            job = client.load_table_from_file(
                source_file, full_table_id, job_config=job_config
            )

        # Đợi job hoàn thành
        job.result()
        print(f"Đã tải {job.output_rows} hàng từ {file_path} vào {full_table_id}")

    except Exception as e:
        print(f"Lỗi khi tải dữ liệu từ {file_path}: {e}")
    finally:
        # Xóa file tạm thời
        if os.path.exists(temp_file_name):
            os.unlink(temp_file_name)

# Xử lý tất cả các file event dump trong thư mục
data_dir = r"D:\CTV\Nexar_test\MockData"  # Thay bằng thư mục dữ liệu của bạn
for filename in os.listdir(data_dir):
    if filename.startswith("event_dump_") and filename.endswith(".json.gz"):
        file_path = os.path.join(data_dir, filename)
        print(f"Đang xử lý {file_path}")
        load_data_from_gzip(file_path)
        print(f"Hoàn thành xử lý {file_path}")

print("Nhập dữ liệu hoàn tất")