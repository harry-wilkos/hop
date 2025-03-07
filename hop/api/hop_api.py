import os
import shutil
from pathlib import Path
from uuid import uuid4
import json
from fastapi import FastAPI, UploadFile, Request
from fastapi.staticfiles import StaticFiles
import uvicorn
import aiohttp
from discord import Webhook
import logging

logging.basicConfig(level=logging.INFO)
app = FastAPI()
os.makedirs("static_files", exist_ok=True)
app.mount("/static_files", StaticFiles(directory="static_files"), name="static_files")


def upload_file(uploaded_file: UploadFile, location: list, uuid: bool):
    if uuid is True:
        dir = os.path.basename(str(uploaded_file.filename).replace('\\', '/'))
        file_name = f"{uuid4()}-{dir}"
    else:
        file_name = Path(str(uploaded_file.filename)).name

    save_path = "."
    for i in location + [file_name]:
        save_path = os.path.join(save_path, i)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    logging.info(f"Writing -> {save_path}")
    with open(save_path, "w+b") as file:
        shutil.copyfileobj(uploaded_file.file, file)
    return save_path


@app.post("/discord")
async def send(request: Request, file: UploadFile | None = None):
    form = await request.form()
    message_str = form.get("message")
    if type(message_str) is not str:
        return None
    message = str(json.loads(message_str))
    store_message = message
    file_location = None
    if file:
        file_location = os.environ["API_ADDRESS"] + upload_file(
            file, ["static_files"], True
        ).lstrip(".")

    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(
            f"https://discord.com/api/webhooks/{os.environ['DISCORD_KEY']}",
            session=session,
        )
        await webhook.send(message)
        logging.info(f"Posting to Discord -> {message}")
        if file_location:
            await webhook.send(file_location)

    return {"message": store_message, "file": file_location}


@app.post("/upload")
async def upload(request: Request, file: UploadFile):
    form = await request.form()
    location_str = form.get("location")
    uuid_str = form.get("uuid")
    print(location_str, type(location_str))
    if type(location_str) is not str or type(uuid_str) is not str:
        return
    location = list(json.loads(location_str))
    uuid = bool(json.loads(uuid_str))
    return os.environ["API_ADDRESS"] + upload_file(file, location, uuid)


@app.post("/delete")
async def delete(request: Request):
    form = await request.form()
    location_str = form.get("location")
    if type(location_str) is not str:
        return None
    file = json.loads(location_str)
    delete_path = file[0]
    for i in file[1:]:
        delete_path = os.path.join(delete_path, i)
    if os.path.exists(delete_path):
        logging.info(f"Removing -> {delete_path}")
        os.remove(delete_path)
    return file


if __name__ == "__main__":
    uvicorn.run(
        f"{__name__}:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        workers=4,
    )
