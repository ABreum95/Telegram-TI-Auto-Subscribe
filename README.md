# Populate your Telegram with threat intel sources
Sources is based on https://raw.githubusercontent.com/fastfire/deepdarkCTI/refs/heads/main/telegram_threat_actors.md

To run:

python3 -m venv myenv

source myenv/bin/activate

pip install -r requirements.txt

python3 TelegramTI.py --api_id <API ID> --api_hash <API HASH> --phone <Phone nr. international format>