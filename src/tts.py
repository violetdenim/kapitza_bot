import torch
import torchaudio
import os
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import tempfile
from git import Repo
try:
    from utils.logger import UsualLoggedClass
except:
    class UsualLoggedClass: pass
try:
    from src.enhancer import Enhancer
except:
    from enhancer import Enhancer
try:
    import deepspeed
    HAS_DEEPSPEED = True
except:
    HAS_DEEPSPEED = False

from queue import Queue
import threading
import dotenv
dotenv.load_dotenv()


class TTSProcessor(UsualLoggedClass):
    def __init__(self, checkpoint_path, hf_token=os.environ.get("HF_AUTH"), output_dir='.generated', enhancer: Enhancer=None):
        super().__init__()
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
                                   vocab_path=xtts_vocab, speaker_file_path=xtts_speaker, use_deepspeed=HAS_DEEPSPEED)

        if torch.cuda.is_available():
            self.model.to(torch.get_default_device())
        self.gpt_cond_latent, self.speaker_embedding = self.model.get_conditioning_latents(audio_path=speaker_audio_file,
                                                                                           gpt_cond_len=self.model.config.gpt_cond_len,
                                                                                           max_ref_length=self.model.config.max_ref_len,
                                                                                           sound_norm_refs=True)
        self.enhancer = enhancer
        self.last_name = None
        self.last_index = 0

    def get_audio(self, text, format=".wav", output_name=None):
        out = self.model.inference(text=text, language='ru', gpt_cond_latent=self.gpt_cond_latent, speaker_embedding=self.speaker_embedding,
                                   temperature=0.2, repetition_penalty=10.0, top_k=50, top_p=0.85, speed=0.95,
                                   enable_text_splitting=True)
        if output_name is None:
            tmp_filename = next(tempfile._get_candidate_names()) + format
            tmp_filename = os.path.join(self.folder, tmp_filename)
        else:
            tmp_filename = output_name
        # modified bits_per_sample for LipSync
        # modified frame rate for offline lipsync
        wave, sr = torch.tensor(out["wav"]).unsqueeze(0), 24_000
        if self.enhancer:
            wave, sr = self.enhancer.enhance(wave, sr)
        if sr != 16_000:
            wave = torchaudio.functional.resample(wave, sr, 16_000)
        torchaudio.save(tmp_filename, wave.cpu(), 16_000, encoding="PCM_S", backend="soundfile", bits_per_sample=16)
        return tmp_filename
    
    def get_stream_audio(self, text, output_name):
        root_name = os.path.splitext(output_name)[0]
        if self.last_name != root_name:
            self.last_name = root_name
            self.last_index = 0

        for out in self.model.inference_stream(text=text, language='ru', gpt_cond_latent=self.gpt_cond_latent, speaker_embedding=self.speaker_embedding,
                                   temperature=0.2, repetition_penalty=10.0, top_k=50, top_p=0.85, speed=0.95, enable_text_splitting=True):
            # modified bits_per_sample for LipSync
            # modified frame rate for offline lipsync
            wave, sr = out.unsqueeze(0), 24_000
            if self.enhancer:
                wave, sr = self.enhancer.enhance(wave, sr)
            if sr != 16_000:
                wave = torchaudio.functional.resample(wave, sr, 16_000)

            chunk_name = f"{root_name}_{self.last_index}.wav"
            torchaudio.save(chunk_name, wave.cpu(), 16_000, encoding="PCM_S", backend="soundfile", bits_per_sample=16)
            self.last_index += 1
            yield chunk_name


# retrieves sentences from one queue and pushes audio into another
class TTSThread(threading.Thread):
    """ Thread accepts audio files using socket and puts their names into queue"""
    def __init__(self, input: Queue, output: Queue, **params):
        self.device = torch.get_default_device()
        threading.Thread.__init__(self)
        self.input = input
        self.engine = TTSProcessor(**params)
        self.output = output
        self._kill = threading.Event()
        self._enabled = threading.Event()
        

    def run(self):
        torch.set_default_device(self.device)
        while True:
            if self._kill.wait(0.05):
                print("Killing TTSThread: kill signal")
                return
            if self._enabled.wait(0.05):
                package = self.input.get(block = True)
                if isinstance(package, int) and package == 9: # kill
                    self.input.task_done()
                    print("Killing TTSThread: end of queue")
                    return
                assert(isinstance(package, tuple) or isinstance(package, list))
                assert((len(package) == 3) or (len(package) == 2))    
                if len(package) == 3:    
                    text, format, output_name = package
                    do_stream = False
                else:
                    text, output_name = package
                    do_stream = True
                if package[1] == "":
                    end_marker = os.path.join(self.engine.folder, output_name)
                    # write 'done' marker
                    print(f"Saving {end_marker}")
                    with open(end_marker, 'w') as m:
                        m.write('')
                    result = output_name
                    if self.output:
                        self.output.put(result)
                else:
                    if not do_stream:
                        result = self.engine.get_audio(text=text, format=format, output_name=output_name)
                        if self.output:
                            self.output.put(result)
                    else:
                        for result in self.engine.get_stream_audio(text=text, output_name=output_name):
                            if self.output:
                                self.output.put(result)
                self.input.task_done()
            
    def kill(self):
        self._kill.set()
    
    def enable(self):
        self._enabled.set()
    
    def disable(self):
        self._enabled.clear()

def _split_text(text, min_length=128):
    import re
    import dotenv
    dotenv.load_dotenv('../.env')
    sentence_list = [s.strip(' ') for s in re.split("(\.|!|\?)", text) if len(s)]
    sentence_list = [sentence_list[i] + sentence_list[i + 1] for i in range(0, len(sentence_list), 2)]
    
    audio_block = ""
    for sentence in sentence_list:
        if len(audio_block) + len(sentence) < min_length: 
            audio_block += " " + sentence
        else:
            if len(audio_block):
                yield audio_block
            audio_block = sentence
    if len(audio_block):
        yield audio_block
    return
    
# function to monitor 
def _do_folder_monitoring(input_folder=".received", output_folder='.generated'):
    for filename in [input_folder, output_folder]:
        if not os.path.exists(filename):
            os.makedirs(filename, 0o777, True)
    import time
    input_queue = Queue()
    
    my_thread = TTSThread(input_queue, None, checkpoint_path=os.environ.get("AUDIO_PATH"), output_dir=output_folder)
    my_thread.start()
    my_thread.enable()
    
    while True:
        time.sleep(0.1)
        files = os.listdir(input_folder)
        # fetch files using creation date
        if len(files):
            sorted_files = list(sorted([os.path.join(input_folder, file_name) for file_name in files], key=lambda x: os.path.getctime(x)))
            for input_file_name in sorted_files:
                if not os.path.exists(input_file_name):
                    continue
                name = os.path.splitext(os.path.split(input_file_name)[-1])[0]
                with open(input_file_name, 'r', encoding='utf-16') as f:
                    user_text = f.read()
                    for i, sentence in enumerate(_split_text(user_text, min_length=128)):
                        input_queue.put([sentence, ".wav", f"{name}_{i}.wav"])
                os.remove(input_file_name)

def _demo_generation(text = """ \
        Hello Science News Explores readers! I am a digital clone of Sergey Kapiitsa. \
        He was a famous scientist who passed away in two thousand twelve. \
        Now, artificial intelligence has made it possible to mimic his voice and likeness. \
        """, enhance=False):
    input_queue = Queue()
    for i, sentence in enumerate(_split_text(text, min_length=128)):
        input_queue.put([sentence, ".wav", f"test_{i}.wav"])
    # input_queue.put(9)
    
    my_thread = TTSThread(input_queue, None, checkpoint_path=os.environ.get("AUDIO_PATH"), enhancer=Enhancer() if enhance else None)
    my_thread.start()
    my_thread.enable()
    input_queue.join()
    print("Empty input_queue!")
    my_thread.kill()

def _demo_generation_streaming(text = """ \
        Hello Science News Explores readers! I am a digital clone of Sergey Kapiitsa. \
        He was a famous scientist who passed away in two thousand twelve. \
        Now, artificial intelligence has made it possible to mimic his voice and likeness. \
        """, enhance=False):
    input_queue = Queue()
    for i, sentence in enumerate(_split_text(text, min_length=128)):
        input_queue.put([sentence, f"test.wav"])
    # input_queue.put(9)
    
    my_thread = TTSThread(input_queue, None, checkpoint_path=os.environ.get("AUDIO_PATH"), enhancer=Enhancer() if enhance else None)
    my_thread.start()
    my_thread.enable()
    input_queue.join()
    print("Empty input_queue!")
    my_thread.kill()
    
def _push_files_to_folder(folder=".received"):
    os.makedirs(folder, 0o777, True)
    text = """Hello Science News Explores readers! I am a digital clone of Sergey Kapiitsa.He was a famous scientist who passed away in two thousand twelve. Now, artificial intelligence has made it possible to mimic his voice and likeness."""
    with open(os.path.join(folder, "test.txt"), "w+", encoding='utf-16') as f:
        f.write(text)
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        mode = int(sys.argv[1])
    else:
        mode = 3
    import torch, time
    torch.set_default_device(f'cuda:0')
    
    match mode:
        case 0: _do_folder_monitoring()
        case 1: _push_files_to_folder()
        case 2: t = time.time_ns(); _demo_generation(text="Здравствуйте! Я цифровой аватар Сергея Капитсы. Для удобства можете обращаться ко мне Сергей Петрович.", enhance=True); print((time.time_ns() - t)//1000.000/1000, " s")
        case 3: t = time.time_ns(); _demo_generation_streaming(text="Здравствуйте! Я цифровой аватар Сергея Капитсы. Для удобства можете обращаться ко мне Сергей Петрович.", enhance=True); print((time.time_ns() - t)//1000.000/1000, " s")

