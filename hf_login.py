import dotenv, os
from huggingface_hub._login import _login

dotenv.load_dotenv()
token = os.environ.get("HF_AUTH")
_login(token=token, add_to_git_credential=True)