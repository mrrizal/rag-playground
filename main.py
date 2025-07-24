import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings())

collection = client.create_collection("my_collection")
collection.add(
    documents=["hello world", "machine learning"],
    metadatas=[{"source": "note1"}, {"source": "note2"}],
    ids=["id1", "id2"]
)
results = collection.query(
    query_texts=["hello"],
    n_results=1
)
print(results)