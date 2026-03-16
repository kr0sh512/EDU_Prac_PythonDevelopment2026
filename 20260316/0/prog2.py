import asyncio

async def echo(reader, writer):
    while data := await reader.readline():
        writer.write(data.swapcase())
    writer.close()

    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(echo, "0.0.0.0", 1337)
    
    async with server:
        await server.serve_forever()

asyncio.run(main())

