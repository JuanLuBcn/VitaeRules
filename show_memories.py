import chromadb

client = chromadb.PersistentClient(path="data/chroma")
collection = client.get_collection("memories")

# Get all memories
results = collection.get(include=['documents', 'metadatas'])

print(f"Raw results keys: {results.keys()}")
print(f"Number of IDs: {len(results['ids'])}")

print("\n" + "=" * 80)
print(f"ALL MEMORIES IN DATABASE ({len(results['ids'])} total)")
print("=" * 80 + "\n")

if results['documents']:
    for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
        print(f"{i+1}. {doc}")
        print(f"   Metadata: {meta}")
        print()
else:
    print("No documents found in results.")
