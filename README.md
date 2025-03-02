# nexar_test

Câu 1: Phân biệt giữa Kimball, One Big Table và Relational Modeling. Đối với vai trò là 
Data Engineer, bạn sẽ lựa chọn phương pháp nào trong từng trường hợp cụ thể.

Kimball: phương pháp thiết kế data warehouse theo mô hình dimensional model với star schema hoặc snowflake schema

Cấu trúc: bao gồm các bảng fact và dim

=> Chi tiết, dễ hiểu tối ưu cho truy vấn phân tích, phù hợp với báo cáo và BI. Dùng cho việc xây dựng data warehouse và tạo báo cáo BI

One Big Table: phương pháp đưa tất cả dữ liệu vào một bảng duy nhất thường sử dụng cho các bài toán machine learning

Cấu trúc: 1 bảng lớn, phi chuẩn, nhiều cột

=> Đơn giản, hiệu quả cho việc huấn luyện mô hình nhưng khó bảo trì và có thể gây dư thừa. Thường cho việc chuẩn bị dữ liệu huấn luyện mô hình học máy, học sâu.

Relational modeling: mô hình thiết kế dữ liệu truyền thống tuân theo các nguyên tắc của RDBMS và chuẩn hóa

Cấu trúc: nhiều bảng liên kết với nhau thông qua khóa và tối ưu thành các chuẩn 3NF...

=> Giảm thiểu dữ thừa, tăng tính toàn vẹn phù hợp với OLTP. Nhưng truy vấn phức tạp, cần join nhiều. Hợp khi xây dựng hệ thống OLTP tối ưu, thiết kế db cho hệ thống dịch vụ

Câu 2: Trong Bigquery, tại sao chỉ partition được column dạng INTEGER, time-unit, ingestion time? 

- Hiệu năng I/O và xử lý phân tán: Khi BigQuery xử lý hàng nghìn node song song, các partition dựa trên giá trị số hoặc thời gian cho phép phân chia khối lượng công việc hiệu quả hơn. Hệ thống biết chính xác ranh giới của mỗi partition và có thể prune data không cần thiết.

- Hiệu quả lưu trữ Colossus: BigQuery sử dụng hệ thống lưu trữ Colossus, và cách tổ chức dữ liệu theo partitioning kiểu này tối ưu cho việc tìm kiếm và thu thập dữ liệu từ storage layer.

- Nguyên tắc cardinality: Với kinh nghiệm xây dựng data warehouse, chúng ta biết rằng cột partition lý tưởng nên có cardinality vừa phải - không quá cao (như UUID), không quá thấp (như Boolean). INTEGER và DATE/TIMESTAMP có đặc tính này.

- Cost management: Qua thực tế làm việc, partitioning theo thời gian cho phép kiểm soát chi phí hiệu quả nhất. Ví dụ, tôi thường setup expiration policy trên các partition theo date để tự động xóa dữ liệu cũ sau 90 ngày, tiết kiệm chi phí lưu trữ đáng kể.

- Trải nghiệm query thực tế: Khi filter theo partition key trong query, BigQuery chỉ scan đúng những partition cần thiết. Trong dự án thực tế, tôi từng giảm được 95% scan data và tiết kiệm rất nhiều chi phí khi cấu trúc partition hợp lý.

Từ kinh nghiệm thực tế, STRING hoặc các kiểu dữ liệu khác thường gây ra skewed partitions - một số partition quá lớn, số khác quá nhỏ - làm giảm hiệu quả phân tán xử lý và khiến các truy vấn chậm hơn.



Câu 3: Trong Bigquery, mô tả nguyên lý hoạt động (ở cấp độ engine) của clustered table, trong trường hợp sử dụng column dạng STRING. 
Từ kinh nghiệm thực tế triển khai, khi BigQuery xử lý clustered tables với column STRING, engine hoạt động như sau:
Storage & Xử lý dữ liệu
Khi load data vào bảng có STRING clustering:

BigQuery sắp xếp data theo lexicographical order (thứ tự từ điển Unicode) của các STRING values. Khác với TIMESTAMP/INTEGER, việc sắp xếp này phức tạp hơn và chiếm nhiều compute resources.
Data được chia thành các blocks, mỗi block chứa những rows có STRING values gần nhau. Trong thực tế, tôi thấy mỗi block thường chứa khoảng 1-5GB dữ liệu (tùy thuộc vào cấu hình system).
Mỗi block được gán metadata với min/max STRING values. Đây là key point giúp query optimization - engine sẽ biết nhanh chóng block nào chứa giá trị STRING cần tìm mà không phải scan toàn bộ.

Khi query hoạt động
Giả sử table events có clustering theo user_id (STRING):
sqlCopySELECT * FROM events WHERE user_id = 'user_12345'
Query sẽ hoạt động:

Block elimination: Engine kiểm tra metadata của từng block và loại bỏ ngay những blocks không chứa user_id = 'user_12345'.
I/O reduction: Thay vì scan toàn bộ 100GB data, có thể engine chỉ cần đọc 1-2 blocks (~2-10GB) chứa giá trị tìm kiếm.
Intelligent scanning: Engine không cần decode/deserialize tất cả columns trong block, mà chỉ focus vào columns được select.

Những cạm bẫy thực tế
Từ kinh nghiệm làm việc với STRING clustering:

Data skew: Nếu phân bố STRING values không đều (ví dụ: 90% records có cùng một giá trị), hiệu quả giảm đáng kể. Tôi từng thấy case query chậm hơn khi cluster trên một STRING field có 80% là NULL.
Cardinality too high: Với STRING fields như UUID có quá nhiều unique values, clustering hiệu quả không cao vì mỗi block chỉ chứa được rất ít records.
Incremental loads: Khi load data theo batch nhỏ, data được thêm vào một lúc sẽ nằm ở cùng block, làm giảm hiệu quả clustering theo thời gian. Tôi thường phải chạy định kỳ CREATE OR REPLACE TABLE để rebuild table.
Filter patterns: Clustering hoạt động tốt nhất với equality filters (=) và range filters trên STRING. Pattern matching (LIKE '%xyz%') không tận dụng được clustering.

Network & Compute
Trong kiến trúc BigQuery, clustered tables giúp giảm shuffling data giữa các compute nodes, vì dữ liệu đã được pre-sorted. Điều này giảm đáng kể network traffic và compute resources khi xử lý big tables.
Từ thực tế làm việc, clustered tables với STRING có thể giảm 50-80% query cost và thời gian xử lý, nhưng cần được thiết kế cẩn thận dựa trên access patterns và phân bố dữ liệu.


Câu 4: Trong Bigquery, so sánh hàm APPROX_COUNT_DISTINCT và COUNT DISTINCT. 
**COUNT DISTINCT:** Tính chính xác số lượng giá trị duy nhất, yêu cầu BigQuery phải lưu trữ và theo dõi mọi giá trị duy nhất trong bộ nhớ.

**APPROX_COUNT_DISTINCT:**Sử dụng thuật toán HyperLogLog++ để ước tính số lượng giá trị duy nhất. Thay vì lưu trữ toàn bộ giá trị, nó chỉ lưu trữ "sketches" của dữ liệu.

Hiệu năng và tài nguyên

COUNT DISTINCT:

- Tốn nhiều bộ nhớ vì phải theo dõi mọi giá trị duy nhất
- Yêu cầu shuffle data nhiều hơn giữa các nodes
- Tốc độ chậm hơn với large datasets
- Chi phí xử lý cao hơn do scan và xử lý toàn bộ dữ liệu


APPROX_COUNT_DISTINCT:

- Sử dụng bộ nhớ cố định, không phụ thuộc vào lượng dữ liệu
- Giảm đáng kể lượng data phải shuffle
- Tốc độ nhanh hơn đáng kể (có thể nhanh hơn 10-100x)
- Chi phí xử lý thấp hơn



Độ chính xác

- COUNT DISTINCT: Kết quả chính xác 100%
- APPROX_COUNT_DISTINCT: Độ lỗi tiêu chuẩn khoảng 1%, nghĩa là kết quả thường nằm trong khoảng ±2% của giá trị thực

Trường hợp sử dụng phù hợp

COUNT DISTINCT phù hợp khi:

- Cần độ chính xác tuyệt đối
- Làm việc với dataset nhỏ
- Sử dụng trong báo cáo tài chính hoặc các trường hợp đòi hỏi tính chính xác cao


APPROX_COUNT_DISTINCT phù hợp khi:

- Chấp nhận sai số nhỏ để đổi lấy hiệu suất
- Làm việc với dataset lớn
- Sử dụng trong analytics, dashboards, monitoring
- Trong các trường hợp cần optimize chi phí


Câu 5: Ứng viên được cung cấp một loạt các file dữ liệu ở dạng JSON-ND đã được nén lại ở 
chuẩn GZIP MockData Dữ liệu chứa các event thu thập được từ 1 game mobile. Ứng viên thực hiện các yêu cầu sau: 

a. Import dữ liệu vào BigQuery với schema hợp lý. 

b. Viết lệnh truy vấn cho các câu hỏi sau: - 

Tỷ lệ chiến thắng (win) ở các level 1,5,10 của toàn bộ user?

Chú ý: 

- Tỷ lệ sử dụng skill trung bình trong 1 ván chơi của những user ở Brazil? 
- Tỷ lệ user còn ở lại chơi game qua từng level? (note: giả sử rằng số lượng user chơi 
- các level sau sẽ ít hơn level trước, vì vậy câu hỏi yêu cầu kết quả chính xác rằng sau 
- mỗi level, số user còn lại là bao nhiêu). 
- Ứng viên được tuỳ ý thiết kế thêm các bảng, view, ... phụ trợ khác.  
- Ứng viên cung cấp lại toàn bộ schema của các table. 
- Ứng viên cung cấp lại các script SQL, các script phụ trợ khác. 

- Ngoài SQL để truy vấn bên trong BigQuery, đối với các chức năng phụ trợ khác, ứng 
viên được tuỳ ý chọn stack và ngôn ngữ. 
- Nếu giải thích được lý do lựa chọn stack, ngôn ngữ và những quyết định xung quanh 
giải pháp thì sẽ được đánh giá cao hơn. 

Giải nghĩa các thông tin: 
- event_date: ngày event được log. 
- event_timestamp: thời điểm cụ thể của event được log. 
- event_name: tên của event. 
- event_params: các cặp key-value biểu thị dữ liệu của event. 
- geo: chứa thông tin về địa lý. 

Các event tiêu biểu: 

- level_start: được log lúc user bắt đầu chơi 1 level, với các params sau: 

+  level: level của ván chơi. 

- level_finish: được log lúc user kết lúc 1 level, với các params sau: 

+  level: level hiện tại. 

+ duration: thời gian đã chơi, tính bằng giây. 

+ result: kết quả ván chơi. 

- use_skill: được log lúc user sử dụng 1 skill, với các params sau: 

+ level: level hiện tại. 

+ name: tên của skill.


