import asyncio
import prog

async def echo(reader, writer):
    while data := await reader.readline():
        res = data.strip().decode()
        try:
            writer.write(f"{prog.sqroots(res)}\n".encode())        
        except Exception:
            pass
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(echo, '0.0.0.0', 1337)
    async with server:
        await server.serve_forever()

def srv():
    asyncio.run(main())
