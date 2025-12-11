"""Quick debug test to see parsing output"""
import asyncio
from test_optimized_search import test_search_execution

async def main():
    query = "¿Tengo alguna tarea pendiente relacionada con compras?"
    result = await test_search_execution(query, "Debug Test")
    print(f"\n{'='*80}")
    print(f"RESULT: Time={result['time']:.2f}s, Skipped={result['searches_skipped']}/3")
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())
