from datetime import datetime
import json
import logging
import os
import shutil

import numpy as np

logger = logging.getLogger("myexp.lib_run_single")

def read_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_obs(obs, step_idx, action_timestamp, obs_save_dir):
    """
    Save each key of the observation to the specified path, parsing the correct datatypes.
    """
    file_format = "step_{step_idx}-{key}_{action_timestamp}.{ext}"
    obs_content = {k: None for k in obs.keys()}

    for key, value in obs.items():
        if key in ["accessibility_tree", "user_question", "plan_result"]:
            file_path = os.path.join(obs_save_dir, file_format.format(
                key=key, step_idx=step_idx, action_timestamp=action_timestamp, ext="txt"))
            with open(file_path, "w") as f:
                f.write(value if value else "No data available")
            obs_content[key] = file_path

        elif isinstance(value, bytes):
            file_path = os.path.join(obs_save_dir, file_format.format(
                key=key, step_idx=step_idx, action_timestamp=action_timestamp, ext="png"))
            with open(file_path, "wb") as f:
                f.write(value)
            obs_content[key] = file_path

        elif isinstance(value, (int, float)):
            obs_content[key] = value

        elif isinstance(value, (list, tuple, np.ndarray)) and len(value) > 0 and isinstance(value[0], (int, float)):
            obs_content[key] = value

        elif isinstance(value, str):
            obs_content[key] = value

        elif isinstance(value, np.ndarray):
            file_path = os.path.join(obs_save_dir, file_format.format(
                key=key, step_idx=step_idx, action_timestamp=action_timestamp, ext="npy"))
            np.save(file_path, value)
            obs_content[key] = file_path

        elif "PIL" in str(type(value)):
            file_path = os.path.join(obs_save_dir, file_format.format(
                key=key, step_idx=step_idx, action_timestamp=action_timestamp, ext="png"))
            value.save(file_path)
            obs_content[key] = file_path

        elif isinstance(value, (dict, list)):
            file_path = os.path.join(obs_save_dir, file_format.format(
                key=key, step_idx=step_idx, action_timestamp=action_timestamp, ext="json"))
            with open(file_path, "w") as f:
                json.dump(value, f)
            obs_content[key] = file_path
        else:
            obs_content[key] = f"key: {key}: {type(value)} not saved"
    return obs_content

def run_single_example(agent, env, max_steps, task_config, example_result_dir, scores, task_type, software, with_rag):
    agent.reset()
    obs = env.reset(task_config)
    logger.info('Initialize done! Successfully reset agent and env.')

    start_time = datetime.now()
    init_timestamp = start_time.strftime("%Y%m%d@%H%M%S")
    traj_data = {
        'instruction': task_config['instruction'],
        'task_type': task_type,
        'software': software,
        'init_timestamp': init_timestamp,
        'init_obs': save_obs(obs, 0, init_timestamp, example_result_dir)
    }
    traj_record_file_path = os.path.join(example_result_dir, 'traj.jsonl')
    with open(traj_record_file_path, 'a') as f:
        f.write(json.dumps(traj_data)+'\n')

    step_count = 0
    thinking_time_sum = 0
    action_time_sum = 0
    get_obs_time_sum = 0
    completion_tokens_sum = 0
    prompt_tokens_sum = 0
    total_tokens_sum = 0

    done = False
    step_idx = 1
    step_ds = []


    ##### rag #####
    if with_rag:
        api_list = read_json(os.path.join('LightRAG/my/retrieval_results',task_type, software, str(task_config['id'])+'.json'))    # TODO: convert to absolute path
    else:
        api_list = []
    ###############

    while step_idx <= max_steps:
        ### thinking ###
        logger.info("Agent: Thinking...")
        thinking_start_time = datetime.now()
        response, py_codes, decision, messages, call_llm_time = agent.predict(
            task_config['instruction'],
            obs,
            api_list
        )

        completion_tokens_sum += int(response['completion_tokens'])
        prompt_tokens_sum += int(response['prompt_tokens'])
        total_tokens_sum += int(response['total_tokens'])

        thinking_time_sum += call_llm_time

        step_data = {
            'step_num': step_idx,
            'thinking': {
                'thinking_start_timestamp': thinking_start_time.strftime("%Y%m%d@%H%M%S"),
                'thinking_time': call_llm_time,
                'response': response,
                'py_codes': py_codes,
                'decision': decision,
                'messages': messages
            }
        }

        ### action ###
        logger.info('Stepping...')
        action_start_time = datetime.now()
        action_start_timestamp = action_start_time.strftime("%Y%m%d@%H%M%S")

        ### log messages, response, py_codes, decision
        messages_save_path = os.path.join(example_result_dir, f"step_{step_idx}-messages_{action_start_timestamp}.json")
        with open(messages_save_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(messages, indent=4))
        response_save_path = os.path.join(example_result_dir, f"step_{step_idx}-response_{action_start_timestamp}.json")
        with open(response_save_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(response, indent=4))
        pycodes_save_path = os.path.join(example_result_dir, f"step_{step_idx}-pycodes_{action_start_timestamp}.py")
        with open(pycodes_save_path, "w", encoding='utf-8') as f:
            f.write(py_codes)
        decision_save_path = os.path.join(example_result_dir, f"step_{step_idx}-decision_{action_start_timestamp}.txt")
        with open(decision_save_path, "w", encoding='utf-8') as f:
            f.write(decision)

        obs, terminated, done, fail, run_code_time = env.step(py_codes, decision)

        action_time = run_code_time
        get_obs_time = obs['get_obs_time']
        action_time_sum += action_time
        get_obs_time_sum += get_obs_time

        step_data['action'] = {
            'action_start_timestamp': action_start_timestamp,
            'action_time': action_time,
            'get_obs_time': get_obs_time,
            'terminated': terminated,
            # 'truncated': truncated,
            'done': done,
            'fail': fail,
            # 'info': info,
            'updated_obs': save_obs(obs, step_idx, action_start_timestamp, example_result_dir)
        }
        step_ds.append(step_data)

        with open(traj_record_file_path, 'a') as f:
            f.write(json.dumps(step_data)+'\n')
        
        # if reward > 0:
        #     break

        if terminated:
            break

        step_idx += 1
        step_count +=1


    traj_end_time = datetime.now()
    traj_elapsed_time = (traj_end_time-start_time).total_seconds()
    logger.info('Example trajectory finished.')

    logger.info('Evaluating...')
    eval_res_data = {
        'traj_start_timestamp': init_timestamp,
        'traj_end_timestamp': traj_end_time.strftime("%Y%m%d@%H%M%S"),
        'Time': {
            'traj_elapsed_time': traj_elapsed_time,
            'thinking_time': thinking_time_sum,
            'action_time': action_time_sum,
            'get_obs_time': get_obs_time_sum,
            'avg_thinking_time': thinking_time_sum / step_count if step_count != 0 else 0,
            'avg_action_time': action_time_sum / step_count if step_count != 0 else 0,
            'avg_get_obs_time': get_obs_time_sum / step_count if step_count != 0 else 0,
        },
        'Steps': {
            'steps_total': step_count,
        },
        'Context_length': {
            'completion_tokens_total': completion_tokens_sum,
            'prompt_tokens_total': prompt_tokens_sum,
            'total_tokens_sum': total_tokens_sum,
            'avg_completion_tokens': completion_tokens_sum / step_count if step_count != 0 else 0,
            'avg_prompt_tokens': prompt_tokens_sum / step_count if step_count != 0 else 0,
            'avg_total_tokens': total_tokens_sum / step_count if step_count != 0 else 0
        },
        'result': {}
    }

    if task_type == '3d_model' or task_type == 'assembly' or task_type == 'modify':
        score, cd, gen_stl, gen_step = env.evaluate_3d_model(example_result_dir)
        eval_res_data['result'] = {
            'Score': score,
            'CD': cd,
            'gen_stl': gen_stl,
            'gen_step': gen_step
        }

        with open(os.path.join(example_result_dir, "cd.txt"), "w", encoding="utf-8") as f:
            f.write(f"{cd}\n")

    elif task_type == '2d_sketch':
        score, cd, gen_dxf = env.evaluate_2d_sketch(example_result_dir)
        eval_res_data['result'] = {
            'Score': score,
            'CD': cd,
            'gen_dxf': gen_dxf
        }

        with open(os.path.join(example_result_dir, "cd.txt"), "w", encoding="utf-8") as f:
            f.write(f"{cd}\n")

    elif task_type == 'drawing':
        score, code_valid, gen_pdf = env.evaluate_draw(example_result_dir)
        eval_res_data['result'] = {
            'Score': score,
            'code_valid': code_valid,
            'gen_pdf': gen_pdf
        }

    elif task_type == 'mass_property':
        score, code_valid, gen_json, gen_mass_properties, gt_mass_properties = env.evaluate_mass_properties(example_result_dir)
        eval_res_data['result'] = {
            'Score': score,
            'code_valid': code_valid,
            'gen_json': gen_json,
            "gen_mass_properties": gen_mass_properties,
            "gt_mass_properties": gt_mass_properties
        }
        
    elif task_type == 'interference_detection':
        score, code_valid, gen_json, gen_interference_detection, gt_interference_detection = env.evaluate_interference_detection(example_result_dir)
        eval_res_data['result'] = {
            'Score': score,
            'code_valid': code_valid,
            'gen_json': gen_json,
            "gen_interference_detection": gen_interference_detection,
            "gt_interference_detection": gt_interference_detection
        }
    elif task_type == '3d_model+drawing':
        score_3d_model, cd, gen_stl, gen_step = env.evaluate_3d_model(example_result_dir)
        score_drawing, code_valid, gen_pdf = env.evaluate_draw(example_result_dir)
        if score_3d_model > 0 and score_drawing > 0:
            score = 1.0
        else:
            score = 0.0
        eval_res_data['result'] = {
            "Score": [score_3d_model, score_drawing],
            "Score_3d_model": score_3d_model,
            "Score_drawing": score_drawing,
            'CD': cd,
            'gen_stl': gen_stl,
            'gen_step': gen_step,
            'code_valid_drawing': code_valid,
            'gen_pdf': gen_pdf
        }
    elif task_type == '3d_model+mass_property':
        score_3d_model, cd, gen_stl, gen_step = env.evaluate_3d_model(example_result_dir)
        score_mass_property, code_valid, gen_json, gen_mass_properties, gt_mass_properties = env.evaluate_mass_properties(example_result_dir)
        if score_3d_model > 0 and score_mass_property > 0:
            score = 1.0
        else:
            score = 0.0
        eval_res_data['result'] = {
            'Score': [score_3d_model, score_mass_property],
            "Score_3d_model": score_3d_model,
            "Score_mass_property": score_mass_property,
            'CD': cd,
            'gen_stl': gen_stl,
            'gen_step': gen_step,
            'code_valid_mass_property': code_valid,
            'gen_json': gen_json,
            "gen_mass_properties": gen_mass_properties,
            "gt_mass_properties": gt_mass_properties
        }
    elif task_type == 'assembly+interference_detection':
        score_assembly, cd, gen_stl, gen_step = env.evaluate_3d_model(example_result_dir)
        score_interference_detection, code_valid, gen_json, gen_interference_detection, gt_interference_detection = env.evaluate_interference_detection(example_result_dir)
        if score_assembly > 0 and score_interference_detection > 0:
            score = 1.0
        else:
            score = 0.0
        eval_res_data['result'] = {
            'Score': [score_assembly, score_interference_detection],
            "Score_assembly": score_assembly,
            "Score_interference_detection": score_interference_detection,
            'CD': cd,
            'gen_stl': gen_stl,
            'gen_step': gen_step,
            'code_valid_interference_detection': code_valid,
            'gen_json': gen_json,
            "gen_interference_detection": gen_interference_detection,
            "gt_interference_detection": gt_interference_detection
        }
    elif task_type == '3d_model+modify':
        score_3d_model, cd_3d_model, gen_stl_3d_model, gen_step_3d_model, score_modify, cd_modify, gen_stl_modify = env.evaluate_3d_model_modify(example_result_dir)
        if score_3d_model > 0 and score_modify > 0:
            score = 1.0
        else:
            score = 0.0
        eval_res_data['result'] = {
            "Score": [score_3d_model, score_modify],
            "Score_3d_model": score_3d_model,
            "Score_modify": score_modify,
            "CD_3d_model": cd_3d_model,
            "CD_modify": cd_modify,
            "gen_stl_3d_model": gen_stl_3d_model,
            "gen_step_3d_model": gen_step_3d_model,
            "gen_stl_modify": gen_stl_modify
        }
    else:
        logger.error(f"Invalid task type!!! {task_type}")
        exit(0)

    scores.append(score)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{score}\n")
  
    with open(traj_record_file_path, 'a') as f:
        f.write(json.dumps(eval_res_data)+'\n')
