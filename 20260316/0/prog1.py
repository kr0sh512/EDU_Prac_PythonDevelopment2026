import asyncio

async def echo(reader, writer):
    while data := await reader.readline():
        data_str = str(data, "utf-8")

        try:
            if data_str.startswith("print "):
                writer.write((" ".join(data_str.split()[1:]) + "\n").encode("utf-8"))
            elif data_str.startswith("info "):
                arg = data_str.split()[1]
                
                if arg == "host":
                    writer.write(
                        (str(writer.get_extra_info("peername")[0]) + "\n").encode(
                            "utf-8"
                        )
                    )
                if arg == "port":
                    writer.write(
                        (str(writer.get_extra_info("peername")[1]) + "\n").encode(
                            "utf-8"
                        )
                    )
            else:
                raise RuntimeError("Unknown command")
        except Exception as e:
            writer.write((str(e) + "\n").encode("utf-8"))
    
    writer.close()
    
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(echo, "0.0.0.0", 1337)
    
    async with server:
        await server.serve_forever()

asyncio.run(main())

