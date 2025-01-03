from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from pyannote.audio import Model as VADModel
from pyannote.audio.pipelines import VoiceActivityDetection
import torch, torchaudio, os
import time
try:
    from utils.logger import UsualLoggedClass
except:
    class UsualLoggedClass: pass
from src.enhancer import Enhancer

class ASRProcessor(UsualLoggedClass):
    def __init__(self, model_id="openai/whisper-large-v3", hf_token=os.environ.get('HF_AUTH'), enhancer: Enhancer = None) -> None:
        # use this interface to enable\disable logging on application level
        super().__init__()
        device = torch.get_default_device()
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True,
            #attn_implementation="flash_attention_2" )
        )
        model.to(device)
        processor = AutoProcessor.from_pretrained(model_id)
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=128,
            chunk_length_s=25,
            batch_size=16,
            torch_dtype=torch_dtype,
            device=device,
        )

        model = VADModel.from_pretrained("pyannote/segmentation-3.0", use_auth_token=hf_token)
        self.vad_pipeline = VoiceActivityDetection(segmentation=model)
        HYPER_PARAMETERS = {
            # remove speech regions shorter than that many seconds.
            "min_duration_on": 0.0,
            # fill non-speech regions shorter than that many seconds.
            "min_duration_off": 0.0
        }
        self.vad_pipeline.instantiate(HYPER_PARAMETERS)
        # enable sound enhancing
        self.enhancer = enhancer

       
    def get_text(self, audio_file):
        load_attempts_count = 5
        sleeping_period = 3.0
        for i in range(load_attempts_count):
            try:
                audio, sr = torchaudio.load(audio_file)
                if audio.shape[0] != 1: # keep only first channel
                    audio = audio[0:1, :]
            except Exception as e:
                if i < load_attempts_count - 1:
                    time.sleep(sleeping_period)
                else:
                    # don't kill, just skip
                    print(f"Can not read file {audio_file}.")
                    return None
        default_device = torch.get_default_device()
        
        if self.enhancer is not None:
            audio, sr = self.enhancer.enhance(audio, sr)
        
        rate = 16_000
        if sr != rate:
            audio = torchaudio.functional.resample(audio, sr, rate)
            sr = rate
        parts = self.vad_pipeline({"waveform": audio, "sample_rate": rate})
        
        torch.set_default_device('cpu')
        text = ""
        for segment, _, _ in parts.itertracks(yield_label=True):
            text += self.pipe(audio[0, int(segment.start * rate):int(segment.end * rate)].cpu().numpy().flatten())["text"]
            text += '\n' # end of sentence
        torch.set_default_device(default_device)
        print(f'ASR detected: {text}')
        return text
    
if __name__ == "__main__":
    import torch
    torch.set_default_device(f'cuda:{torch.cuda.device_count()-1}')
    
    asr_proc = ASRProcessor()
    print(asr_proc.get_text("files/name1.wav"))