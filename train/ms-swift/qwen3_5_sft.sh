ENV_LIB_PATH="/nvme/aijiaxin/anaconda3/envs/qwen35_env/lib"
ENV_CUPTI_PATH="/nvme/aijiaxin/anaconda3/envs/qwen35_env/lib/python3.11/site-packages/nvidia/cuda_cupti/lib"
SYS_CUDA_LIB="/usr/local/cuda/lib64"
SYS_CUPTI_LIB="/usr/local/cuda/extras/CUPTI/lib64"
export LD_LIBRARY_PATH=$ENV_LIB_PATH:$ENV_CUPTI_PATH:$SYS_CUDA_LIB:$SYS_CUPTI_LIB:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 
export SKIP_MULTIMODAL_MTP_VALIDATION=1
export PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True'
export TRITON_CACHE_DIR="/tmp/triton_cache_${USER}"
export MODELSCOPE_CACHE=/nvme/aijiaxin/.cache/modelscope
mkdir -p $TRITON_CACHE_DIR
nvidia-smi

bsz=1
output_dir=""   # TODO: Fill in
FPS_MAX_FRAMES=10 \
NPROC_PER_NODE=8 \
MAX_PIXELS=65536 \
swift sft \
    --model /nvme/public_models/Qwen3.5-9B \
    --model_type qwen3_5 \
    --dataset '/nvme/aijiaxin/dataset/COMCAD_new/sft/msswift_data_new/shuffle_two_stages_single_and_multi_tasks_with_and_without_example_30k.jsonl' \
    --train_type full \
    --lora_rank 8 \
    --lora_alpha 32 \
    --torch_dtype bfloat16 \
    --num_train_epochs 1 \
    --per_device_train_batch_size $bsz \
    --learning_rate 1e-5 \
    --target_modules all-linear \
    --gradient_accumulation_steps 4 \
    --save_strategy steps \
    --save_steps 100 \
    --max_length 16384 \
    --save_total_limit 100 \
    --logging_steps 5 \
    --output_dir $output_dir \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 4 \
    --deepspeed zero2 \
    --attn_impl flash_attn \
    --use_logits_to_keep true \
    --padding_free true \

