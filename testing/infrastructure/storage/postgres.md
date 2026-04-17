# Postgres

Used to store the ebook data before creating the embeddings

```
docker run -d \
  --name postgres-ebooks \
  -e POSTGRES_USER=ebooks \
  -e POSTGRES_PASSWORD=your_secret_password \
  -e POSTGRES_DB=library \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16
  ```

