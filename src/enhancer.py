import torch, torchaudio
from df.enhance import enhance, init_df
try:
    from utils.logger import UsualLoggedClass
except:
    class UsualLoggedClass: pass

class Enhancer(UsualLoggedClass):
    def __init__(self):
        print('Enhancer init')
        super().__init__()
        self.device = torch.get_default_device()
        self.enhancing_model, self.enhancing_state, _, _ = init_df() 
        self.enhancing_rate = self.enhancing_state.sr()
        self.enhancing_model.to(self.device)
    
    def enhance(self, audio, sr):
        _input_device = audio.device
        if sr != self.enhancing_rate:
            audio = torchaudio.functional.resample(audio, sr, self.enhancing_rate)
        return enhance(self.enhancing_model, self.enhancing_state, audio.to(self.device), self.enhancing_rate).to(_input_device), self.enhancing_rate


if __name__ == "__main__":
    default_device = torch.set_default_device('cpu')

    engine = Enhancer()
    audio, sr = torchaudio.load("test_0.wav")
    audio, sr = engine.enhance(audio.to(default_device), sr)
    torchaudio.save("test_enh.wav", audio.cpu(), sr, encoding="PCM_S", backend="soundfile", bits_per_sample=16)