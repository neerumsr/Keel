from huggingface_hub import snapshot_download as s
for m in ["Qwen/Qwen3.5-2B","Qwen/Qwen3.5-0.8B","Qwen/Qwen3.5-4B"]:
    print(s(m, local_dir="C:/KeelWork/models/"+m.split("/")[1]), flush=True)
