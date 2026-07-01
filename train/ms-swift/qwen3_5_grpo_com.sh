ENV_LIB_PATH="/nvme/aijiaxin/anaconda3/envs/qwen35_env/lib"
ENV_CUPTI_PATH="/nvme/aijiaxin/anaconda3/envs/qwen35_env/lib/python3.11/site-packages/nvidia/cuda_cupti/lib"
SYS_CUDA_LIB="/usr/local/cuda/lib64"
SYS_CUPTI_LIB="/usr/local/cuda/extras/CUPTI/lib64"
export LD_LIBRARY_PATH=$ENV_LIB_PATH:$ENV_CUPTI_PATH:$SYS_CUDA_LIB:$SYS_CUPTI_LIB:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 
export SKIP_MULTIMODAL_MTP_VALIDATION=1
export MODELSCOPE_CACHE=/nvme/aijiaxin/.cache/modelscope
export VLLM_USE_V1=0
#!/bin/bash
# ============================================================
# COMCAD Multi-Turn GRPO Training Script
# ========================================================================================================================

# ---------- Reward API ----------
output_dir=""   # TODO: fill in
model_path=""   # TODO: fill in
export TOTAL_VMS=64
export TRITON_CACHE_DIR=/tmp/${USER}/triton_cache_cad_grpo
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,max_split_size_mb:512"
export TORCH_COMPILE_DISABLE=1
nvidia-smi
mkdir -p "${TRITON_CACHE_DIR}"

# ---------- Train ----------
NPROC_PER_NODE=8 \
swift rlhf \
    --rlhf_type grpo \
    --model $model_path \
    \
    `# ---- plugings & reward ----` \
    --external_plugins ms-swift/examples/train/grpo/plugin/my_com/com_grpo_plugin.py \  # TODO: replace with absolute path
    --reward_funcs com_reward \
    \
    `# ---- multi-turn scheduler ----` \
    --multi_turn_scheduler com_scheduler \
    --max_turns 5 \
    \
    `# ---- dataset ----` \
    --dataset 'grpo_shuffle_3d_model_assembly_2d_sketch_without_example_2156.jsonl' \  # TODO: replace with absolute path
    --load_from_cache_file true \
    \
    `# ---- vLLM Colocate ----` \
    --enable_thinking false \
    --use_vllm true \
    --vllm_mode colocate \
    --vllm_gpu_memory_utilization 0.4 \
    --vllm_tensor_parallel_size 1 \
    --vllm_max_model_len 32768 \
    --sleep_level 1 \
    \
    `# ---- training hyper-parameters ----` \
    --tuner_type full \
    --torch_dtype bfloat16 \
    --max_length 32768 \
    --max_completion_length 5000 \
    --num_train_epochs 2 \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --num_generations 4 \
    --temperature 1.0 \
    --top_p 0.9 \
    --top_k 50 \
    --learning_rate 1e-6 \
    --lr_scheduler_type cosine \
    --warmup_ratio 0.05 \
    --max_grad_norm 1.0 \
    --offload_model true \
    --offload_optimizer true \
    \
    `# ---- GRPO parameters ----` \
    --epsilon 0.2 \
    --epsilon_high 0.28 \
    --scale_rewards none \
    \
    `# ---- others ----` \
    --deepspeed zero3 \
    --dataloader_num_workers 8 \
    --save_steps 5 \
    --save_total_limit 100 \
    --logging_steps 1 \
    --log_completions true \
    --vllm_enforce_eager true \
    --output_dir $output_dir \
    --vllm_mm_processor_cache_gb 0
