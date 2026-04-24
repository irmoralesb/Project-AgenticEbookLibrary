# Instructions for Ingestion Section

## Postgres DB

### Setup

Creating the container
```
docker run -d --name postgres-db -e POSTGRES_USER=<YOU_USER> -e POSTGRES_PASSWORD=<YOUR_PASSWORD> -e POSTGRES_DB=elibrary -p 5432:5432 -v postgres_data:/var/lib/postgresql/data postgres:18
```

Running the container

```
docker container start postgres-db
```

### Run the DB Scripts

```

```


## Qdrant Vector DB

### Setup

```
docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /opt/qdrant/storage:/qdrant/storage \
  -e QDRANT__SERVICE__API_KEY=your_secret_key \
  qdrant/qdrant:v1.9.0

```

Running the container

```
docker container start qdrant
```
