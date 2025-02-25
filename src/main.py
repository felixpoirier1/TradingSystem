from Gateway import KalshiGateway
from Engine import Engine
import asyncio
async def main():
    engine = Engine()
    await engine.launch()

if __name__ == "__main__":
    asyncio.run(main())
    