# ----------------------------------------------
# Evaluation on ComCADBench with base settings
# ----------------------------------------------
TRIAL_ID=0
MAX_STEPS=6
SANDBOX_INFO_FILE="alive_vms.json"  # TODO: fill in path of alive_vms.json
NUM_WORKERS=63

MODEL_NAME="" # TODO: fill in model name
BASE_URL="" # TODO: fill in base url
API_KEY=""  # TODO: fill in api key

MAX_TOKENS=8192
TEMPERATURE=0.2 # Optimal settings: 0.2 for our trained ComActor-9B model, and 1.0 for the base model to encourage exploration.
TOP_P=0.9

# TODO: Convert the following paths to absolute paths.

## 3d_model ###
for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \ 
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/3d_model_test_list_100.json \
    --test_config_base_dir examples/Text2CAD \
    --result_dir results/results_base/results_3d_model \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '3d_model' \
    --software 'sldworks' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait

for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/3d_model_test_list_100.json \
    --test_config_base_dir examples/Text2CAD \
    --result_dir results/results_base/results_3d_model \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '3d_model' \
    --software 'inventor' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait


##### assembly #####
for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/assembly_test_list_100.json \
    --test_config_base_dir examples/Fusion360Gallery_AssemblyJoint \
    --result_dir results/results_base/results_assembly \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type 'assembly' \
    --software 'inventor' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait


##### 2d_sketch #####
for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/2d_sketch_test_list_100.json \
    --test_config_base_dir examples/SketchGraphs \
    --result_dir results/results_base/results_2d_sketch \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '2d_sketch' \
    --software 'autocad' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait


##### 3d_model+drawing #####
for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/3d_model+drawing_test_list_100.json \
    --test_config_base_dir examples/multi_tasks/3d_model+drawing \
    --result_dir results/results_base/results_3d_model+drawing \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '3d_model+drawing' \
    --software 'sldworks' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait


##### 3d_model+mass_property #####
for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/3d_model+property_test_list_100.json \
    --test_config_base_dir examples/multi_tasks/3d_model+mass_property/sldworks \
    --result_dir results/results_base/results_3d_model+mass_property \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '3d_model+mass_property' \
    --software 'sldworks' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait

for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/3d_model+property_test_list_100.json \
    --test_config_base_dir examples/multi_tasks/3d_model+mass_property/inventor \
    --result_dir results/results_base/results_3d_model+mass_property \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '3d_model+mass_property' \
    --software 'inventor' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait


##### assembly+interference_detection #####
for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/assembly+interference_detection_test_list_100.json \
    --test_config_base_dir examples/multi_tasks/assembly+interference_detection \
    --result_dir results/results_base/results_assembly+interference_detection \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type 'assembly+interference_detection' \
    --software 'inventor' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait


##### 3d_model+modify #####
for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/3d_model+modify_test_list_100.json \
    --test_config_base_dir examples/multi_tasks/3d_model+modify/sldworks \
    --result_dir results/results_base/results_3d_model+modify \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '3d_model+modify' \
    --software 'sldworks' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait

for i in $(seq 0 $((NUM_WORKERS - 1))); do
  python run.py \
    --max_steps $MAX_STEPS \
    --max_trajectory_length 1 \
    --model $MODEL_NAME \
    --base_url $BASE_URL \
    --api_key $API_KEY \
    --max_tokens $MAX_TOKENS \
    --domain test \
    --test_all_meta_path benchmarks/comcadbench/3d_model+modify_test_list_100.json \
    --test_config_base_dir examples/multi_tasks/3d_model+modify/inventor \
    --result_dir results/results_base/results_3d_model+modify \
    --num_workers $NUM_WORKERS \
    --worker_id "$i" \
    --sandbox_info_file $SANDBOX_INFO_FILE \
    --task_type '3d_model+modify' \
    --software 'inventor' \
    --trial_id $TRIAL_ID \
    --temperature $TEMPERATURE \
    --top_p $TOP_P &
done

wait
