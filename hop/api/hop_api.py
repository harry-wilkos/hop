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


def upload_file(uploaded_file: UploadFile, location: list, uuid: bool):
    if uuid is True:
        file_name = f"{uuid4()}-{Path(str(uploaded_file.filename)).name}"
    else:
        file_name = Path(str(uploaded_file.filename)).name

    save_path = "."
    for i in location + [file_name]:
        save_path = os.path.join(save_path, i)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "w+b") as file:
        shutil.copyfileobj(uploaded_file.file, file)
    print(save_path)
    return save_path


app = FastAPI()
os.makedirs("static_files", exist_ok=True)
app.mount("/static_files", StaticFiles(directory="static_files"), name="static_files")


@app.post("/discord")
async def send(request: Request, file: UploadFile | None = None):
    form = await request.form()
    message = str(form.get("message"))
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
        if file_location:
            await webhook.send(file_location)

    return {"message": store_message, "file": file_location}


@app.post("/upload")
async def upload(request: Request, file: UploadFile):
    form = await request.form()
    location_str = form.get("location")
    uuid_str = form.get("uuid")
    if type(location_str) is str and type(uuid_str) is str:
        location = json.loads(location_str)
        uuid = json.loads(uuid_str)
        return os.environ["API_ADDRESS"] + upload_file(file, location, uuid)
    return None


@app.post("/delete")
async def delete(request: Request):
    file = await request.json()
    delete_path = ""
    for i in file:
        delete_path = os.path.join(delete_path, i)
    if os.path.exists(delete_path):
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
