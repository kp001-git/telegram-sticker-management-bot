import os
import logging
from dotenv import load_dotenv
from telegram import Update, InputSticker, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import RetryAfter, TimedOut, NetworkError
import string
import random
import asyncio
import json
import zipfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from PIL import Image
from translations import TRANSLATIONS

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_user_packs():
    if os.path.exists('user_packs.json'):
        with open('user_packs.json', 'r') as f:
            return json.load(f)
    return {}

def save_user_packs(packs):
    with open('user_packs.json', 'w') as f:
        json.dump(packs, f)

def load_user_langs():
    if os.path.exists('user_langs.json'):
        with open('user_langs.json', 'r') as f:
            return json.load(f)
    return {}

def save_user_langs(langs):
    with open('user_langs.json', 'w') as f:
        json.dump(langs, f)

def get_lang(user_id):
    langs = load_user_langs()
    return langs.get(str(user_id), 'en')

def add_user_pack(user_id, pack_name):
    packs = load_user_packs()
    user_id_str = str(user_id)
    if user_id_str not in packs:
        packs[user_id_str] = []
    if pack_name not in packs[user_id_str]:
        packs[user_id_str].append(pack_name)
    save_user_packs(packs)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id)
    t = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    
    keyboard = [
        [InlineKeyboardButton(t['btn_channel'], url="https://t.me/souldumpp"),
         InlineKeyboardButton(t['btn_menu'], callback_data="menu_commands")],
        [InlineKeyboardButton(t['btn_lang'], callback_data="menu_lang"),
         InlineKeyboardButton(t['btn_about'], callback_data="menu_about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(t['welcome'], reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=t['welcome'], reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id)
    t = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    
    if update.callback_query:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(t['help'], reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=t['help'])

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id)
    t = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    
    if update.callback_query:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(t['about'], reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=t['about'])

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id)
    t = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar"),
         InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa")],
        [InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="setlang_hi")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(t['lang_prompt'], reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=t['lang_prompt'], reply_markup=reply_markup)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "menu_main":
        await start_command(update, context)
    elif query.data == "menu_about":
        await about_command(update, context)
    elif query.data == "menu_commands":
        await help_command(update, context)
    elif query.data == "menu_lang":
        await lang_command(update, context)
    elif query.data.startswith("setlang_"):
        new_lang = query.data.split("_")[1]
        user_id = str(update.effective_user.id)
        langs = load_user_langs()
        langs[user_id] = new_lang
        save_user_langs(langs)
        await start_command(update, context)

WAITING_FOR_STICKER = 1
COLLECTING_MIX_STICKERS = 2
ADD_STICKER_NEW = 3
ADD_STICKER_TARGET = 4
DEL_PACK_TARGET = 5
DEL_STICKER_TARGET = 6
DEL_PACK_CONFIRM = 9
SETPACKICON_TARGET = 10
SETPACKICON_ICON = 11
RENAMEPACK_TARGET = 12
RENAMEPACK_TITLE = 13
EDITSTICKER_TARGET = 14
EDITSTICKER_EMOJI = 15
MAKESTICKER_PHOTO = 16
TOWHATSAPP_TARGET = 17

async def clonepack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_clone")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "Which pack are we borrowing?\nSend me any sticker from it, paste its pack link, or send a custom emoji."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
        
    return WAITING_FOR_STICKER

async def cancel_clone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Cloning cancelled.")
    return ConversationHandler.END

async def clonepack_receive_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Attempt to clear the inline keyboard from the previous message
    try:
        if update.message and update.message.reply_to_message:
            await update.message.reply_to_message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    set_name = None
    if update.message.sticker:
        set_name = update.message.sticker.set_name
    elif update.message.text:
        text = update.message.text
        if "addstickers/" in text:
            # Extract just the pack name from the URL
            set_name = text.split("addstickers/")[-1].split("?")[0].split("/")[0].strip()
        else:
            set_name = text.strip()
            
    if not set_name:
        await update.message.reply_text("I couldn't find a valid pack. Please send a sticker or a valid t.me/addstickers/ link.")
        return WAITING_FOR_STICKER
    
    await update.message.reply_text(f"Found the pack: {set_name}. Cloning has started! This might take a minute...")
    
    try:
        # Get the original sticker set
        sticker_set = await context.bot.get_sticker_set(set_name)
        
        # Get bot username
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        
        # Create a unique short name for the new pack
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        new_pack_name = f"clone_{update.effective_user.id}_{random_string}_by_{bot_username}"
        new_pack_title = f"{sticker_set.title} (Cloned)"
        
        # We can add up to 50 stickers in create_new_sticker_set
        max_initial_stickers = 50
        initial_stickers_list = sticker_set.stickers[:max_initial_stickers]
        remaining_stickers_list = sticker_set.stickers[max_initial_stickers:]
        
        # Determine the format from the first sticker
        first_sticker = sticker_set.stickers[0]
        sticker_format = "animated" if first_sticker.is_animated else ("video" if first_sticker.is_video else "static")
        
        # Instead of downloading the stickers, we can just pass the file_id!
        # This completely bypasses download/upload rate limits because Telegram already has the files.
        input_stickers = []
        for s in initial_stickers_list:
            input_stickers.append(InputSticker(s.file_id, [s.emoji or "👍"], format=sticker_format))
            
        # Create the new sticker set with up to 50 stickers at once
        while True:
            try:
                await context.bot.create_new_sticker_set(
                    user_id=update.effective_user.id,
                    name=new_pack_name,
                    title=new_pack_title,
                    stickers=input_stickers,
                    sticker_type=sticker_set.sticker_type,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=120
                )
                break
            except RetryAfter as e:
                await update.message.reply_text(f"Rate limited while creating pack. Waiting for {e.retry_after} seconds...")
                await asyncio.sleep(e.retry_after + 1)
            except (TimedOut, NetworkError) as e:
                logger.warning(f"Network error during pack creation: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
        
        added_count = len(input_stickers)
        
        # Add the rest of the stickers one by one using file_ids (if there are > 50)
        for s in remaining_stickers_list:
            while True:
                try:
                    await context.bot.add_sticker_to_set(
                        user_id=update.effective_user.id,
                        name=new_pack_name,
                        sticker=InputSticker(s.file_id, [s.emoji or "👍"], format=sticker_format),
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60
                    )
                    break
                except RetryAfter as e:
                    await update.message.reply_text(f"Rate limited by Telegram. Waiting for {e.retry_after} seconds...")
                    await asyncio.sleep(e.retry_after + 1)
                except (TimedOut, NetworkError) as e:
                    logger.warning(f"Network error/timeout during upload: {e}. Retrying in 5 seconds...")
                    await asyncio.sleep(5)
            
            added_count += 1
            if added_count % 10 == 0:
                await update.message.reply_text(f"Cloned {added_count}/{len(sticker_set.stickers)} stickers...")
                
            await asyncio.sleep(0.1) # Add a tiny delay
                
        add_user_pack(update.effective_user.id, new_pack_name)
        
        keyboard = [
            [InlineKeyboardButton("Open pack", url=f"https://t.me/addstickers/{new_pack_name}")],
            [InlineKeyboardButton("Clone another", callback_data="clonepack_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Pack successfully cloned! ({added_count} stickers)\n"
            f"Here is your new pack: t.me/addstickers/{new_pack_name}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error cloning pack: {e}")
        await update.message.reply_text(f"Failed to clone the pack. Error: {e}")
        
    return ConversationHandler.END

async def abort_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation aborted.")
    return ConversationHandler.END

async def addsticker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send the new sticker you want to add. Send /abort to cancel.")
    return ADD_STICKER_NEW

async def addsticker_receive_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.sticker:
        await update.message.reply_text("Please send a sticker.")
        return ADD_STICKER_NEW
    context.user_data['new_sticker_file_id'] = update.message.sticker.file_id
    context.user_data['new_sticker_emoji'] = update.message.sticker.emoji or "👍"
    await update.message.reply_text("Great! Now send me any sticker from the pack you want to add this to.")
    return ADD_STICKER_TARGET

async def addsticker_receive_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.sticker or not update.message.sticker.set_name:
        await update.message.reply_text("Please send a sticker that belongs to a pack you own.")
        return ADD_STICKER_TARGET
    
    set_name = update.message.sticker.set_name
    sticker_format = "animated" if update.message.sticker.is_animated else ("video" if update.message.sticker.is_video else "static")
    
    try:
        await context.bot.add_sticker_to_set(
            user_id=update.effective_user.id,
            name=set_name,
            sticker=InputSticker(context.user_data['new_sticker_file_id'], [context.user_data['new_sticker_emoji']], format=sticker_format)
        )
        await update.message.reply_text(f"✅ Sticker added to t.me/addstickers/{set_name}!")
    except Exception as e:
        await update.message.reply_text(f"Failed to add sticker (make sure you own the pack). Error: {e}")
    return ConversationHandler.END

async def delpack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    packs = load_user_packs()
    user_id_str = str(update.effective_user.id)
    
    if user_id_str not in packs or not packs[user_id_str]:
        await update.message.reply_text("You haven't created any packs with me yet! Nothing to delete.")
        return ConversationHandler.END
        
    keyboard = []
    for pack in packs[user_id_str]:
        keyboard.append([InlineKeyboardButton(pack, callback_data=f"delpack_{pack}")])
    keyboard.append([InlineKeyboardButton("Cancel Pack Deletion", callback_data="cancel_delpack")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Tap on the pack you want to completely DELETE:", reply_markup=reply_markup)
    return DEL_PACK_TARGET

async def delpack_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_delpack":
        await query.edit_message_text("Pack deletion cancelled.")
        return ConversationHandler.END
        
    set_name = query.data.replace("delpack_", "")
    context.user_data['pack_to_delete'] = set_name
    
    keyboard = [
        [InlineKeyboardButton("⚠️ Yes, permanently delete it!", callback_data="confirm_delete")],
        [InlineKeyboardButton("No, go back", callback_data="back_to_delpack")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Are you absolutely sure you want to permanently delete the pack:\n**{set_name}**?", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return DEL_PACK_CONFIRM

async def delpack_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_delpack":
        await query.edit_message_text("Pack deletion cancelled.")
        return ConversationHandler.END
        
    if query.data == "back_to_delpack":
        packs = load_user_packs()
        user_id_str = str(update.effective_user.id)
        
        keyboard = []
        if user_id_str in packs:
            for pack in packs[user_id_str]:
                keyboard.append([InlineKeyboardButton(pack, callback_data=f"delpack_{pack}")])
        keyboard.append([InlineKeyboardButton("Cancel Pack Deletion", callback_data="cancel_delpack")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Tap on the pack you want to completely DELETE:", reply_markup=reply_markup)
        return DEL_PACK_TARGET
        
    set_name = context.user_data.get('pack_to_delete')
    if not set_name:
        await query.edit_message_text("Error: Couldn't find the pack name to delete.")
        return ConversationHandler.END
        
    try:
        await context.bot.delete_sticker_set(name=set_name)
        
        # Remove from our database
        packs = load_user_packs()
        user_id_str = str(update.effective_user.id)
        if user_id_str in packs and set_name in packs[user_id_str]:
            packs[user_id_str].remove(set_name)
            save_user_packs(packs)
            
        await query.edit_message_text(f"✅ Pack **{set_name}** has been permanently deleted.", parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"Failed to delete pack (it might have already been deleted). Error: {e}")
        
    context.user_data['pack_to_delete'] = None
    return ConversationHandler.END

async def delsticker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send the specific sticker you want to REMOVE from its pack. Send /abort to cancel.")
    return DEL_STICKER_TARGET

async def delsticker_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.sticker:
        await update.message.reply_text("Please send the sticker.")
        return DEL_STICKER_TARGET
    try:
        await context.bot.delete_sticker_from_set(sticker=update.message.sticker.file_id)
        await update.message.reply_text("✅ Sticker removed from the pack successfully.")
    except Exception as e:
        await update.message.reply_text(f"Failed to remove sticker. Error: {e}")
    return ConversationHandler.END

# --- SETPACKICON ---
async def setpackicon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    packs = load_user_packs()
    user_id_str = str(update.effective_user.id)
    if user_id_str not in packs or not packs[user_id_str]:
        await update.message.reply_text("You haven't created any packs with me yet!")
        return ConversationHandler.END
    keyboard = []
    for pack in packs[user_id_str]:
        keyboard.append([InlineKeyboardButton(pack, callback_data=f"seticon_{pack}")])
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel_icon")])
    await update.message.reply_text("Select the pack you want to set an icon for:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SETPACKICON_TARGET

async def setpackicon_receive_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_icon":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END
    set_name = query.data.replace("seticon_", "")
    context.user_data['icon_pack'] = set_name
    await query.edit_message_text(f"Send me a sticker to use as the new icon for **{set_name}**.", parse_mode="Markdown")
    return SETPACKICON_ICON

async def setpackicon_receive_icon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.sticker:
        await update.message.reply_text("Please send a sticker.")
        return SETPACKICON_ICON
    set_name = context.user_data['icon_pack']
    sticker_format = "animated" if update.message.sticker.is_animated else ("video" if update.message.sticker.is_video else "static")
    try:
        await context.bot.set_sticker_set_thumbnail(
            name=set_name,
            user_id=update.effective_user.id,
            thumbnail=update.message.sticker.file_id,
            format=sticker_format
        )
        await update.message.reply_text(f"✅ Icon set successfully for t.me/addstickers/{set_name}")
    except Exception as e:
        await update.message.reply_text(f"Failed to set icon. Error: {e}")
    return ConversationHandler.END

# --- RENAMEPACK ---
async def renamepack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    packs = load_user_packs()
    user_id_str = str(update.effective_user.id)
    if user_id_str not in packs or not packs[user_id_str]:
        await update.message.reply_text("You haven't created any packs with me yet!")
        return ConversationHandler.END
    keyboard = []
    for pack in packs[user_id_str]:
        keyboard.append([InlineKeyboardButton(pack, callback_data=f"rename_{pack}")])
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel_rename")])
    await update.message.reply_text("Select the pack you want to rename:", reply_markup=InlineKeyboardMarkup(keyboard))
    return RENAMEPACK_TARGET

async def renamepack_receive_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_rename":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END
    set_name = query.data.replace("rename_", "")
    context.user_data['rename_pack'] = set_name
    await query.edit_message_text(f"Send me the new title for **{set_name}**.", parse_mode="Markdown")
    return RENAMEPACK_TITLE

async def renamepack_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("Please send text for the new title.")
        return RENAMEPACK_TITLE
    set_name = context.user_data['rename_pack']
    try:
        await context.bot.set_sticker_set_title(name=set_name, title=update.message.text)
        await update.message.reply_text(f"✅ Pack renamed successfully to '{update.message.text}'.")
    except Exception as e:
        await update.message.reply_text(f"Failed to rename pack. Error: {e}")
    return ConversationHandler.END

# --- EDITSTICKER ---
async def editsticker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send the specific sticker you want to edit emojis for. Send /abort to cancel.")
    return EDITSTICKER_TARGET

async def editsticker_receive_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.sticker:
        await update.message.reply_text("Please send a sticker.")
        return EDITSTICKER_TARGET
    context.user_data['edit_sticker_id'] = update.message.sticker.file_id
    await update.message.reply_text("Now send me the new emojis for this sticker (e.g. 😃 🔥).")
    return EDITSTICKER_EMOJI

async def editsticker_receive_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("Please send emojis as text.")
        return EDITSTICKER_EMOJI
    emojis = [c for c in update.message.text if not c.isspace()]
    if not emojis:
        await update.message.reply_text("No valid emojis found. Try again.")
        return EDITSTICKER_EMOJI
    try:
        await context.bot.set_sticker_emoji_list(sticker=context.user_data['edit_sticker_id'], emoji_list=emojis)
        await update.message.reply_text("✅ Sticker emojis updated successfully.")
    except Exception as e:
        await update.message.reply_text(f"Failed to update emojis. Error: {e}")
    return ConversationHandler.END

# --- MAKESTICKER ---
async def makesticker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me any picture or image file, and I will instantly turn it into a perfectly formatted Telegram sticker! Send /abort to cancel.")
    return MAKESTICKER_PHOTO

async def makesticker_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('image/'):
        file = await update.message.document.get_file()
    else:
        await update.message.reply_text("Please send an image (like a JPG, PNG, or uncompressed image file).")
        return MAKESTICKER_PHOTO
        
    status_msg = await update.message.reply_text("Processing your image... ⏳")
    
    try:
        # Download file to memory
        file_bytes = await file.download_as_bytearray()
        
        # Process with Pillow
        img = Image.open(BytesIO(file_bytes)).convert("RGBA")
        
        # Telegram requires exactly 512 on one side, <=512 on the other
        width, height = img.size
        if width > height:
            new_width = 512
            new_height = int(512 * (height / width))
        else:
            new_height = 512
            new_width = int(512 * (width / height))
            
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save as WEBP
        out_io = BytesIO()
        img.save(out_io, format="WEBP")
        out_io.seek(0)
        out_io.name = "sticker.webp" # Telegram sometimes requires a filename
        
        # Send back as a sticker
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id, 
            sticker=out_io,
            reply_to_message_id=update.message.message_id
        )
        await status_msg.edit_text("✅ Success! Here is your new sticker. You can now use it, or forward it to /addsticker to add it to a pack.")
        
    except Exception as e:
        logger.error(f"Error making sticker: {e}")
        await status_msg.edit_text(f"Failed to process the image. Error: {e}")
        
    return ConversationHandler.END

# --- TOWHATSAPP ---
async def towhatsapp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a sticker from the pack you want to export to WhatsApp! I'll package it up for you. Send /abort to cancel.")
    return TOWHATSAPP_TARGET

async def towhatsapp_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.sticker:
        await update.message.reply_text("Please send a valid sticker.")
        return TOWHATSAPP_TARGET
        
    set_name = update.message.sticker.set_name
    if not set_name:
        await update.message.reply_text("This sticker doesn't belong to any pack!")
        return ConversationHandler.END
        
    status_msg = await update.message.reply_text(f"Fetching pack '{set_name}'... This might take a minute! ⏳")
    
    try:
        sticker_set = await context.bot.get_sticker_set(set_name)
        
        # WhatsApp limits packs to 30 stickers. We export the first 30 for safety/speed.
        stickers_to_dl = sticker_set.stickers[:30]
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for i, sticker in enumerate(stickers_to_dl):
                file = await context.bot.get_file(sticker.file_id)
                file_bytes = await file.download_as_bytearray()
                # Save into zip (use .webp as they are animated/static webp)
                zip_file.writestr(f"sticker_{i+1}.webp", file_bytes)
                
        zip_buffer.seek(0)
        zip_buffer.name = f"{set_name}_whatsapp.zip"
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=zip_buffer,
            caption=(
                f"✅ **Pack Exported!**\n\n"
                f"I've bundled {len(stickers_to_dl)} stickers into this `.zip` file.\n\n"
                f"**How to use on WhatsApp:**\n"
                f"1. Download and extract this `.zip` file on your phone.\n"
                f"2. Download any free 'Sticker Maker' app from the Play/App Store.\n"
                f"3. Select the extracted images in the app to instantly add them to WhatsApp!"
            ),
            parse_mode="Markdown"
        )
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error exporting pack: {e}")
        await status_msg.edit_text(f"Failed to export pack. Error: {e}")
        
    return ConversationHandler.END



async def vault_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    packs = load_user_packs()
    user_id_str = str(update.effective_user.id)
    
    if user_id_str not in packs or not packs[user_id_str]:
        await update.message.reply_text("Your vault is empty! Try cloning a pack first with /clonepack.")
        return
        
    text = "Here are the sticker packs in your vault:\n\n"
    for idx, pack in enumerate(packs[user_id_str], 1):
        text += f"{idx}. t.me/addstickers/{pack}\n"
        
    await update.message.reply_text(text)

async def mix_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mix_stickers'] = []
    
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_mix")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "Send me the stickers you want to mix into a new pack! 🎨\nSend them one by one. When you're done, tap Finish below or type /done."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
        
    return COLLECTING_MIX_STICKERS

async def mix_receive_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sticker = update.message.sticker
    if not sticker:
        await update.message.reply_text("Please send a sticker, or type /done when finished.")
        return COLLECTING_MIX_STICKERS
        
    context.user_data['mix_stickers'].append(sticker)
    
    keyboard = [
        [InlineKeyboardButton("Finish & Create Pack", callback_data="finish_mix")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_mix")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(f"Added! You have {len(context.user_data['mix_stickers'])} stickers in your mix.", reply_markup=reply_markup)
    return COLLECTING_MIX_STICKERS

async def mix_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        user = update.effective_user
        # Remove buttons
        await message.edit_reply_markup(reply_markup=None)
    else:
        message = update.message
        user = update.effective_user
        
    stickers = context.user_data.get('mix_stickers', [])
    if not stickers:
        await message.reply_text("You didn't send any stickers!")
        return ConversationHandler.END
        
    await message.reply_text("Crafting your mixed pack... This might take a moment!")
    
    try:
        bot_info = await context.bot.get_me()
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        new_pack_name = f"mix_{user.id}_{random_string}_by_{bot_info.username}"
        new_pack_title = f"Mixed Pack {random_string}"
        
        first_sticker = stickers[0]
        sticker_format = "animated" if first_sticker.is_animated else ("video" if first_sticker.is_video else "static")
        
        input_stickers = []
        for s in stickers[:50]:
            input_stickers.append(InputSticker(s.file_id, [s.emoji or "👍"], format=sticker_format))
            
        await context.bot.create_new_sticker_set(
            user_id=user.id,
            name=new_pack_name,
            title=new_pack_title,
            stickers=input_stickers,
            sticker_type="regular",
            read_timeout=120,
            write_timeout=120,
            connect_timeout=120
        )
        
        add_user_pack(user.id, new_pack_name)
        
        keyboard = [
            [InlineKeyboardButton("Open pack", url=f"https://t.me/addstickers/{new_pack_name}")],
            [InlineKeyboardButton("Mix another", callback_data="mix_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            f"✅ Mix successfully created! ({len(input_stickers)} stickers)\n"
            f"Here is your new pack: t.me/addstickers/{new_pack_name}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error creating mixed pack: {e}")
        await message.reply_text(f"Failed to create the mix. Error: {e}")
        
    context.user_data['mix_stickers'] = []
    return ConversationHandler.END

async def cancel_mix_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Mix cancelled.")
    context.user_data['mix_stickers'] = []
    return ConversationHandler.END

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing! Please set it in a .env file.")
        exit(1)
        
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(60).write_timeout(60).connect_timeout(60).pool_timeout(60).build()
    
    start_handler = CommandHandler('start', start_command)
    help_handler = CommandHandler('help', help_command)
    
    clonepack_handler = ConversationHandler(
        entry_points=[
            CommandHandler('clonepack', clonepack_start),
            CallbackQueryHandler(clonepack_start, pattern='^clonepack_start$')
        ],
        states={
            WAITING_FOR_STICKER: [
                MessageHandler(filters.Sticker.ALL | filters.TEXT, clonepack_receive_sticker),
                CallbackQueryHandler(cancel_clone_callback, pattern='^cancel_clone$')
            ]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    )
    
    mix_handler = ConversationHandler(
        entry_points=[
            CommandHandler('mix', mix_start),
            CallbackQueryHandler(mix_start, pattern='^mix_start$')
        ],
        states={
            COLLECTING_MIX_STICKERS: [
                MessageHandler(filters.Sticker.ALL, mix_receive_sticker),
                CommandHandler('done', mix_finish),
                CallbackQueryHandler(mix_finish, pattern='^finish_mix$'),
                CallbackQueryHandler(cancel_mix_callback, pattern='^cancel_mix$')
            ]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    )
    
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(CommandHandler('vault', vault_command))
    application.add_handler(CommandHandler('about', about_command))
    application.add_handler(CommandHandler('lang', lang_command))
    application.add_handler(CallbackQueryHandler(menu_callback, pattern='^(menu_|setlang_)'))
    application.add_handler(clonepack_handler)
    application.add_handler(mix_handler)
    
    # New management handlers
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('addsticker', addsticker_start)],
        states={
            ADD_STICKER_NEW: [MessageHandler(filters.Sticker.ALL, addsticker_receive_new)],
            ADD_STICKER_TARGET: [MessageHandler(filters.Sticker.ALL, addsticker_receive_target)]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('delpack', delpack_start)],
        states={
            DEL_PACK_TARGET: [CallbackQueryHandler(delpack_receive, pattern='^(delpack_|cancel_delpack)')],
            DEL_PACK_CONFIRM: [CallbackQueryHandler(delpack_confirm, pattern='^(confirm_delete|cancel_delpack|back_to_delpack)$')]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('delsticker', delsticker_start)],
        states={
            DEL_STICKER_TARGET: [MessageHandler(filters.Sticker.ALL, delsticker_receive)]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('setpackicon', setpackicon_start)],
        states={
            SETPACKICON_TARGET: [CallbackQueryHandler(setpackicon_receive_pack, pattern='^(seticon_|cancel_icon)')],
            SETPACKICON_ICON: [MessageHandler(filters.Sticker.ALL, setpackicon_receive_icon)]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('renamepack', renamepack_start)],
        states={
            RENAMEPACK_TARGET: [CallbackQueryHandler(renamepack_receive_pack, pattern='^(rename_|cancel_rename)')],
            RENAMEPACK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, renamepack_receive_title)]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('editsticker', editsticker_start)],
        states={
            EDITSTICKER_TARGET: [MessageHandler(filters.Sticker.ALL, editsticker_receive_sticker)],
            EDITSTICKER_EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, editsticker_receive_emoji)]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('makesticker', makesticker_start)],
        states={
            MAKESTICKER_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, makesticker_receive)]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('towhatsapp', towhatsapp_start)],
        states={
            TOWHATSAPP_TARGET: [MessageHandler(filters.Sticker.ALL, towhatsapp_receive)]
        },
        fallbacks=[CommandHandler('abort', abort_command)]
    ))
    
    application.add_handler(CommandHandler('abort', abort_command))
    
    # --- RENDER FREE TIER HACK ---
    # Render requires web services to bind to a port, otherwise it kills the process.
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Sticker Bot is running!")

    def start_dummy_server():
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(('0.0.0.0', port), DummyHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        logger.info(f"Dummy web server listening on port {port}")

    start_dummy_server()
    # -----------------------------
    
    logger.info("Bot is starting...")
    application.run_polling()
