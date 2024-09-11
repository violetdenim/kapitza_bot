from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from pyannote.audio import Model as VADModel
from pyannote.audio.pipelines import VoiceActivityDetection
import torch, torchaudio, os

class ASRProcessor:
    def __init__(self, model_id="openai/whisper-large-v3", hf_token=os.environ.get('HF_AUTH')) -> None:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True,
            attn_implementation="flash_attention_2" )
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
        
    def get_text(self, audio_file):
        rate = 16_000
        sample = torchaudio.load(audio_file)
        voice = torchaudio.functional.resample(sample[0], sample[1], rate)

        parts = self.vad_pipeline({"waveform": voice, "sample_rate": rate})
        text = ""
        for segment, track, label in parts.itertracks(yield_label=True):
            text += self.pipe(voice[0, int(segment.start*rate):int(segment.end*rate)].numpy().flatten())["text"]
            text += '\n' # end of sentence
        return text
