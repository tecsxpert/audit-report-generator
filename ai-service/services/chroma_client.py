import chromadb

client = chromadb.PersistentClient(path="./chroma_data")

collection = client.get_or_create_collection("audit_docs")

collection.add(
    documents=["Security audit guidelines"],
    ids=["1"]
)
