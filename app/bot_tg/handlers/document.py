"""
app/bot_tg/handlers/document.py

It will decide what happens when a documents will comes here
"""

from pathlib import Path


from telegram import Update
from telegram.ext import ContextTypes

#


# Resolve the download directory relative to the project working directory.
DOWNLOAD_DIR = (Path.cwd() / "downloads" / "auto_download").resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def handle_document_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    document = message.effective_attachment

    if document is None:
        await message.reply_text("Please send a file as a document.")
        return

    print("A Document comes here", document)

    try:
        filename = Path(document.file_name or "no_name_file").name
        destination = DOWNLOAD_DIR / filename

        file_id = document.file_id
        new_file = await context.bot.get_file(file_id)

        print("NEW FILE IS:", new_file)
        print("NEW FILE PATH IS:", new_file.file_path)
        print("TYPE OF NEW FILE IS:", type(new_file))

        location = await new_file.download_to_drive(custom_path=destination)
        print("Type of locaion is:", type(location), location)

        await message.reply_text(
            f"✅ File downloaded successfully!\n" f"📁 Location: {location}"
        )

    except Exception as e:
        print("ERRRRRr", e)

        await message.reply_text("❌ Download Fails")
