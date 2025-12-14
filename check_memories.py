"""Check what memories exist in ChromaDB."""
import chromadb

client = chromadb.PersistentClient(path='data/chroma')
coll = client.get_collection('memories')
results = coll.get(limit=20, include=['metadatas', 'documents'])

print(f'Total: {len(results["ids"])} memories\n')
print("="*80)

for i in range(len(results['ids'])):
    print(f'\n{i+1}. ID: {results["ids"][i][:8]}...')
    print(f'   Document: {results["documents"][i][:200]}...')
    print(f'   Metadata: {results["metadatas"][i]}')
    print("-"*80)
