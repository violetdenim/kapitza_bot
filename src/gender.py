import torch
import torchaudio
from transformers import AutoModelForAudioClassification

# returns F, if woman speaks in audio
# returns M, if man speaks in audio
def detect_gender(audio_file, model_path="alefiury/wav2vec2-large-xlsr-53-gender-recognition-librispeech"):
    device = torch.get_default_device()
    model = AutoModelForAudioClassification.from_pretrained(
        pretrained_model_name_or_path=model_path,
        num_labels=2,
        label2id={"female": 0, "male": 1},
        id2label={0: "female", 1: "male"}
    )
    model.to(device)
    model.eval()
    data, rate = torchaudio.load(audio_file)
    data = torchaudio.functional.resample(data, rate, 16_000)[0:1, :]

    len_audio = data.shape[1]
    max_audio_len = 5
    target_data_len = max_audio_len * 16_000

    # Pad or truncate the audio to match the desired length
    if len_audio < target_data_len:
        # Pad the audio if it's shorter than the desired length
        target = torch.zeros(1, target_data_len)
        target[:, :len_audio] = data
    else:
        # Truncate the audio if it's longer than the desired length
        target = data[:, :target_data_len]

    input_values, attention_mask = target.to(device), None
    logits = model(input_values, attention_mask=attention_mask).logits
    scores = torch.nn.functional.softmax(logits, dim=-1)
    pred = torch.argmax(scores, dim=1).cpu().detach().numpy()[0]
    return "M" if pred else "F"

if __name__ == "__main__":
    test_files = ["files/test.wav", "files/name1.wav", "files/color.wav"]
    for file_name in test_files:
        print(file_name, detect_gender(file_name))