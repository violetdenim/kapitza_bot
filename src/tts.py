import torch, torchaudio, os
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import tempfile
from git import Repo

class TTSProcessor:
    def __init__(self, checkpoint_path = "../../kapitza_audio_model"):
        # checkpoint_path = "/media/zipa/6C0CE7B5223C084C/TestCode2/xtts_finetune/v2/ready"
        if not os.path.exists(checkpoint_path):
            Repo.clone_from("https://huggingface.co/kzipa/kapitza_voice", checkpoint_path)

        xtts_config = os.path.join(checkpoint_path, "config.json")
        xtts_checkpoint = os.path.join(checkpoint_path, "model.pth")
        xtts_vocab = os.path.join(checkpoint_path, "vocab.json")
        xtts_speaker = os.path.join(checkpoint_path, "speakers_xtts.pth")
        speaker_audio_file = os.path.join(checkpoint_path, "reference.wav")
        
        config = XttsConfig()
        config.load_json(xtts_config)
        self.model = Xtts.init_from_config(config)
        self.model.load_checkpoint(config, checkpoint_path=xtts_checkpoint, vocab_path=xtts_vocab, speaker_file_path=xtts_speaker, use_deepspeed=False)
        if torch.cuda.is_available():
            self.model.cuda()
        self.gpt_cond_latent, self.speaker_embedding = self.model.get_conditioning_latents(audio_path=speaker_audio_file,
                                                                                gpt_cond_len=self.model.config.gpt_cond_len,
                                                                                max_ref_length=self.model.config.max_ref_len,
                                                                                sound_norm_refs=True)

    def get_audio(self, text, format=".wav"):
        out = self.model.inference(text=text, language='ru', gpt_cond_latent=self.gpt_cond_latent, speaker_embedding=self.speaker_embedding,
        temperature=0.2, repetition_penalty=10.0, top_k=50, top_p=0.85, enable_text_splitting=True)
        tmp_filename = next(tempfile._get_candidate_names()) + format
        torchaudio.save(tmp_filename, torch.tensor(out["wav"]).unsqueeze(0), 24_000, backend="soundfile")
        return tmp_filename
