# Qdrant


https://hub.docker.com/r/qdrant/qdrant


## Server

```
docker run -p 6333:6333 qdrant/qdrant
```

## Client

```
pip install qdrant-client
```

```
from qdrant_client import QdrantClient
qdrant = QdrantClient(":memory:") # Create in-memory Qdrant instance, for testing, CI/CD
# OR
client = QdrantClient(path="path/to/db")  # Persists changes to disk, fast prototyping
```

or

```
qdrant = QdrantClient("http://localhost:6333") # Connect to existing Qdrant instance
```