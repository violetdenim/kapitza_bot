import torch
import torchaudio
import os
import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import tempfile
from git import Repo


class TTSProcessor:
    def __init__(self, checkpoint_path, hf_token=os.environ.get("HF_AUTH"), output_dir='.generated'):
        self.folder = output_dir
        if os.path.exists(self.folder):
            for f in os.listdir(self.folder):
                os.remove(os.path.join(self.folder, f))
            os.removedirs(self.folder)
        os.makedirs(self.folder, 0o777, True)

        files = [os.path.join(checkpoint_path, f) for f in [
            "config.json", "model.pth", "vocab.json", "speakers_xtts.pth", "reference.wav"]]
        download = not os.path.exists(checkpoint_path)
        for f in files:
            if not os.path.exists(f):
                download = True
        if download:
            Repo.clone_from(
                url=f"https://user:{hf_token}@huggingface.co/kzipa/kapitza_voice", to_path=checkpoint_path)
        assert (os.path.exists(checkpoint_path))
        xtts_config, xtts_checkpoint, xtts_vocab, xtts_speaker, speaker_audio_file = files

        config = XttsConfig()
        config.load_json(xtts_config)
        self.model = Xtts.init_from_config(config)
        self.model.load_checkpoint(config, checkpoint_path=xtts_checkpoint,
                                   vocab_path=xtts_vocab, speaker_file_path=xtts_speaker, use_deepspeed=False)

        if torch.cuda.is_available():
            self.model.cuda()
        self.gpt_cond_latent, self.speaker_embedding = self.model.get_conditioning_latents(audio_path=speaker_audio_file,
                                                                                           gpt_cond_len=self.model.config.gpt_cond_len,
                                                                                           max_ref_length=self.model.config.max_ref_len,
                                                                                           sound_norm_refs=True)

    def get_audio(self, text, format=".wav", output_name=None):
        out = self.model.inference(text=text, language='ru', gpt_cond_latent=self.gpt_cond_latent, speaker_embedding=self.speaker_embedding,
                                   temperature=0.2, repetition_penalty=10.0, top_k=50, top_p=0.85,
                                   speed=0.95,
                                   enable_text_splitting=True)
        if output_name is None:
            tmp_filename = next(tempfile._get_candidate_names()) + format
            tmp_filename = os.path.join(self.folder, tmp_filename)
        else:
            tmp_filename = output_name
        torchaudio.save(tmp_filename, torch.tensor(out["wav"]).unsqueeze(
            0), 24_000, encoding="PCM_S", backend="soundfile")
        return tmp_filename
