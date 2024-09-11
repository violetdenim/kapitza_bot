FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 as runtime

ARG DEBIAN_FRONTEND=noninteractive

# Uncomment the lines below to use a 3rd party repository
# to get the latest (unstable from mesa/main) mesa library version
RUN apt-get update && apt install -y software-properties-common
RUN add-apt-repository ppa:oibaf/graphics-drivers -y

RUN apt update && apt install -y \
    vainfo \
    mesa-va-drivers \
    mesa-utils

# RUN conda create -n kap_env python=3.11 && conda activate kap_env && pip install -r requirements.txt 
# ENV LIBVA_DRIVER_NAME=d3d12
# ENV LD_LIBRARY_PATH=/usr/lib/wsl/lib
# CMD vainfo --display drm --device /dev/dri/card0

# COPY environment.yml .
# RUN apt install -y miniconda
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
# Install wget to fetch Miniconda
RUN apt-get update && \
    apt-get install -y wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
# Install Miniconda on x86 or ARM platforms
RUN arch=$(uname -m) && \
    if [ "$arch" = "x86_64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"; \
    elif [ "$arch" = "aarch64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"; \
    else \
    echo "Unsupported architecture: $arch"; \
    exit 1; \
    fi && \
    wget $MINICONDA_URL -O miniconda.sh && \
    mkdir -p /root/.conda && \
    bash miniconda.sh -b -p /root/miniconda3 && \
    rm -f miniconda.sh
RUN apt-get update && apt install -y git
RUN conda create -n kap_env python=3.11

# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "kap_env", "/bin/bash", "-c"]

# install torch in the first place (to avoid errors during flash_attn installation)
RUN pip install torch torchaudio
# CMD python -c "import torch; print(torch.cuda.is_available())"
# RUN pip install -r requirements.txt
RUN pip install flash_attn python-dotenv python-telegram-bot gitpython runorm
RUN pip install llama-index llama-index-embeddings-huggingface
RUN pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121 llama-cpp-python 
RUN pip install llama-index-llms-llama_cpp
RUN pip install TTS pyannote.audio accelerate
COPY . .
RUN pip install huggingface_hub
RUN python hf_login.py
RUN git config --global credential.helper store
RUN apt-get install git-lfs
RUN git lfs install
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "kap_env", "python", "run.py"]
# CMD python run.py