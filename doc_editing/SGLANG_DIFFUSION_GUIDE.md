# Agent Guide: SGLang Diffusion, Qwen Image, Ubuntu 24 on NVIDIA GB10

This guide is written for an agent setting up an NVIDIA GB10 machine to host Qwen Image through SGLang Diffusion.

## Target Outcome

By the end, the target machine should:

1. Run the vendor-supported Ubuntu-based DGX OS / Ubuntu 24.04 environment.
2. Have GPU, CUDA, Docker, Python, and Hugging Face access verified.
3. Run SGLang Diffusion locally.
4. Generate a smoke-test image with Qwen Image.
5. Host Qwen Image behind an OpenAI-compatible image-generation API.
6. Expose the API only through localhost or an SSH tunnel unless a trusted LAN deployment is explicitly required.

## Important Naming Note

The request says "Qwen Image 2". Public naming is ambiguous:

- SGLang Diffusion currently lists Qwen Image model IDs including `Qwen/Qwen-Image`, `Qwen/Qwen-Image-2512`, `Qwen/Qwen-Image-Edit`, `Qwen/Qwen-Image-Edit-2509`, `Qwen/Qwen-Image-Edit-2511`, and `Qwen/Qwen-Image-Layered`.
- Hugging Face has public model cards for `Qwen/Qwen-Image` and `Qwen/Qwen-Image-2512`.
- Qwen has public Qwen-Image-2.0 technical reports, but the exact public weight repo may differ by the time this guide is executed.

Default to `Qwen/Qwen-Image-2512` for a current hosted image-generation setup. If the executor confirms a real `Qwen/Qwen-Image-2.0` or successor repo exists and SGLang supports it, substitute that model ID everywhere `MODEL_ID` appears.

## Hardware and OS Baseline

The target machine is an NVIDIA GB10 Grace Blackwell system. Treat it like a DGX Spark-compatible ARM64 AI workstation, not a generic x86 Ubuntu desktop.

Expected baseline:

- CPU/GPU: NVIDIA GB10 Grace Blackwell.
- CPU architecture: ARM64 / `aarch64`.
- Memory: 128 GB coherent unified LPDDR5x.
- OS: NVIDIA DGX OS, Ubuntu-based. Use the official DGX Spark OS image and recovery path, not generic Ubuntu, unless the user explicitly asks for a clean unsupported install.
- Networking: 10 GbE plus ConnectX-7 for high-speed multi-system networking.

First boot options:

- Local: attach display, keyboard, mouse, and Ethernet before applying power.
- Network appliance: connect from another machine to the setup hotspot printed on the quick-start card, then finish setup in a browser.

During setup, do not power off while the first-time update/install process is running.

## Initial System Setup

Run these after first boot and account creation:

```bash
uname -m
lsb_release -a || cat /etc/os-release
nvidia-smi
python3 --version
docker --version
df -h
```

Expected:

- `uname -m` is `aarch64`.
- OS reports Ubuntu 24.04 or NVIDIA DGX OS based on Ubuntu 24.04.
- `nvidia-smi` can see the NVIDIA GPU. On unified-memory GB10 systems, some memory fields may not look like a discrete GPU.
- At least 100 GB free for model cache and outputs; 150 GB or more is more comfortable.

Install basic tools:

```bash
sudo apt update
sudo apt install -y git git-lfs curl jq ffmpeg python3-venv python3-pip
git lfs install
```

Update the system using the NVIDIA/DGX OS update path first. If using `apt`, reboot afterward:

```bash
sudo apt full-upgrade -y
sudo reboot
```

After reboot:

```bash
nvidia-smi
docker run --rm --gpus all lmsysorg/sglang:latest-cu130 nvidia-smi
```

If the Docker command fails, fix Docker/NVIDIA Container Toolkit before continuing.

## Hugging Face Access

Use a Hugging Face token even for public models so large downloads do not hit anonymous-rate limits.

```bash
mkdir -p ~/models/huggingface
cat >> ~/.bashrc <<'EOF'
export HF_HOME=$HOME/models/huggingface
export HF_HUB_ENABLE_HF_TRANSFER=1
EOF
source ~/.bashrc

python3 -m venv ~/hf-tools
source ~/hf-tools/bin/activate
pip install -U pip "huggingface_hub[cli]" hf_transfer
huggingface-cli login
```

If the machine already has a populated Hugging Face cache elsewhere, either keep using that path consistently or copy it into `~/models/huggingface` before large downloads.

## Install SGLang Diffusion

Prefer a Python virtualenv first. Use Docker as the fallback if ARM64 wheels or CUDA bindings are not available for the current SGLang Diffusion release.

```bash
mkdir -p ~/ai/sglang-qwen-image
cd ~/ai/sglang-qwen-image
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip uv
uv pip install "sglang[diffusion]" --prerelease=allow
```

Verify the CLI:

```bash
sglang --help
sglang generate --help
sglang serve --help
```

If the install fails because a dependency has no ARM64/GB10 wheel:

1. Try the official SGLang CUDA 13 container path:

   ```bash
   docker pull lmsysorg/sglang:latest-cu130
   docker run --rm --gpus all \
     --ipc=host \
     --shm-size 32g \
     -v "${HF_HOME:-$HOME/.cache/huggingface}:/root/.cache/huggingface" \
     -e HF_TOKEN="$HF_TOKEN" \
     lmsysorg/sglang:latest-cu130 \
     nvidia-smi
   ```

2. If diffusion extras are missing inside the container, build/install SGLang from source inside a development container following the current SGLang Diffusion install docs:

   ```bash
   git clone https://github.com/sgl-project/sglang.git
   cd sglang
   pip install -e "python[diffusion]"
   ```

## Choose the Model ID

Set one model ID for the whole setup:

```bash
export MODEL_ID="Qwen/Qwen-Image-2512"
```

If a true Qwen Image 2 repo exists and is supported:

```bash
export MODEL_ID="Qwen/Qwen-Image-2.0"
```

Run a lightweight metadata check:

```bash
python - <<'PY'
import os
from huggingface_hub import model_info

model_id = os.environ["MODEL_ID"]
info = model_info(model_id)
print(info.id)
print(info.sha)
print(info.last_modified)
PY
```

## One-Off Generation Smoke Test

Start with the smallest useful smoke test. Qwen Image quality improves with full-size aspect ratios and enough inference steps, but the first test is only to prove the stack works.

```bash
cd ~/ai/sglang-qwen-image
source .venv/bin/activate

sglang generate \
  --model-path "$MODEL_ID" \
  --prompt "A clean product photo of a compact desktop AI workstation on a desk, with the text 'Qwen Image' clearly printed on a small label." \
  --save-output
```

Success criteria:

- The model downloads without authentication or disk errors.
- CUDA initializes successfully.
- An image file is saved.
- The image roughly matches the prompt.

If the CLI supports explicit size and step flags on the installed version, run a second quality test:

```bash
sglang generate \
  --model-path "$MODEL_ID" \
  --prompt "A crisp poster for an internal AI lab, with readable text: 'Qwen Image'." \
  --width 1328 \
  --height 1328 \
  --save-output
```

Use `sglang generate --help` for the exact flag names in the installed version before adding optional quality flags to automation.

## Start the Hosted API

Run the server bound to localhost first:

```bash
cd ~/ai/sglang-qwen-image
source .venv/bin/activate

sglang serve \
  --model-path "$MODEL_ID" \
  --host 127.0.0.1 \
  --port 30010
```

From the target machine, test the OpenAI-compatible image endpoint:

```bash
curl -s http://127.0.0.1:30010/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$MODEL_ID"'",
    "prompt": "A simple square icon with readable text Qwen",
    "size": "1024x1024",
    "response_format": "b64_json"
  }' \
  | jq -r ".data[0].b64_json" \
  | base64 -d > qwen-image-api-smoke.png

file qwen-image-api-smoke.png
```

If the server returns a path or URL instead of `b64_json`, inspect the JSON response and adapt the client. The important check is that the API returns a generated image for a standard image-generation request.

## Remote Access

Preferred access is SSH tunneling from the user's laptop or workstation:

```bash
ssh -L 30010:127.0.0.1:30010 <ai-host-user>@<ai-hostname>.local
```

Then call the API from the laptop at:

```text
http://127.0.0.1:30010/v1/images/generations
```

Only bind to `0.0.0.0` if a trusted LAN service is explicitly required:

```bash
sglang serve \
  --model-path "$MODEL_ID" \
  --host 0.0.0.0 \
  --port 30010
```

If exposing on LAN, add a firewall rule scoped to the trusted subnet, not the public internet.

## Optional systemd User Service

Create an environment file:

```bash
mkdir -p ~/.config
cat > ~/.config/sglang-qwen-image.env <<'EOF'
MODEL_ID=Qwen/Qwen-Image-2512
HF_HUB_ENABLE_HF_TRANSFER=1
EOF
```

Create the user service:

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/sglang-qwen-image.service <<'EOF'
[Unit]
Description=SGLang Diffusion Qwen Image server
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/ai/sglang-qwen-image
EnvironmentFile=%h/.config/sglang-qwen-image.env
Environment=HF_HOME=%h/models/huggingface
ExecStart=%h/ai/sglang-qwen-image/.venv/bin/sglang serve --model-path ${MODEL_ID} --host 127.0.0.1 --port 30010
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now sglang-qwen-image.service
systemctl --user status sglang-qwen-image.service
journalctl --user -u sglang-qwen-image.service -f
```

To keep it running after logout:

```bash
sudo loginctl enable-linger "$USER"
```

## Operational Checks

Before handing off, record:

```bash
date -Is
hostname
uname -m
cat /etc/os-release | sed -n '1,8p'
nvidia-smi
python3 --version
docker --version
systemctl --user status sglang-qwen-image.service --no-pager
curl -s http://127.0.0.1:30010/v1/models | jq .
```

Acceptance checklist:

- First boot and DGX OS updates completed.
- `nvidia-smi` works.
- Docker GPU test works or the native Python path is documented as the active path.
- `sglang generate` saves an image.
- `/v1/images/generations` returns an image.
- Service is bound to localhost unless a trusted LAN exposure was requested.
- Model ID and exact SGLang version are recorded.

## Troubleshooting

- `nvidia-smi` works but memory usage looks odd: GB10 uses unified system memory, so discrete-GPU memory reporting can differ from normal RTX/A100 systems.
- Docker cannot see the GPU: verify NVIDIA Container Toolkit, Docker daemon status, and that the test command from the NVIDIA/SGLang playbook works.
- Model download stalls or fails: set `HF_TOKEN`, check free disk, and use `HF_HUB_ENABLE_HF_TRANSFER=1`.
- Import errors after `sglang[diffusion]`: use the container fallback or install from source. ARM64 wheels can lag x86_64 releases.
- Image endpoint shape differs: inspect `curl -s ... | jq .`; SGLang Diffusion is OpenAI-compatible, but response fields can vary by version and request options.
- Poor text rendering: try the full Qwen-recommended resolution/aspect ratios and a more explicit prompt. Qwen Image is especially strong at text rendering, but tiny smoke-test images are not quality benchmarks.

## Source Links

- SGLang Diffusion overview: https://docs.sglang.io/docs/sglang-diffusion
- SGLang Diffusion installation: https://docs.sglang.io/docs/sglang-diffusion/installation
- SGLang Diffusion model compatibility: https://docs.sglang.io/docs/sglang-diffusion/compatibility_matrix
- SGLang Diffusion CLI reference: https://docs.sglang.io/docs/sglang-diffusion/api/cli
- SGLang Diffusion OpenAI API reference: https://docs.sglang.io/docs/sglang-diffusion/api/openai_api
- Qwen/Qwen-Image model card: https://huggingface.co/Qwen/Qwen-Image
- Qwen/Qwen-Image-2512 model card: https://huggingface.co/Qwen/Qwen-Image-2512
- Qwen-Image-2.0 technical report: https://arxiv.org/abs/2605.10730
- Qwen-Image-2.0-RL technical report: https://arxiv.org/abs/2606.27608
- NVIDIA DGX Spark product page and specs: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
- NVIDIA DGX Spark user guide: https://docs.nvidia.com/dgx/dgx-spark/index.html
- NVIDIA DGX Spark first boot guide: https://docs.nvidia.com/dgx/dgx-spark/first-boot.html
- NVIDIA DGX Spark local network access playbook: https://build.nvidia.com/spark/connect-to-your-spark
- NVIDIA SGLang on DGX Spark playbook: https://build.nvidia.com/spark/sglang
