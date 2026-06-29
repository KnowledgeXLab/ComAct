"""Script to run end-to-end evaluation on the benchmark.
Utils and basic architecture credit to https://github.com/web-arena-x/webarena/blob/main/run.py.
"""
import argparse
import datetime
import json
import logging
import os
import random
import sys
import shutil
import traceback
# import wandb

from tqdm import tqdm

import asyncio

import lib_run_single
from myenv import MyDesktopEnv, MyEnvController
from agent import PromptAgent
import requests

from threading import Event
import signal

### Logger Configs ###
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.propagate = True
datetime_str: str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
formatter = logging.Formatter(
    fmt="\x1b[1;33m[%(asctime)s \x1b[31m%(levelname)s \x1b[32m%(module)s/%(lineno)d-%(processName)s\x1b[1;33m] \x1b[0m%(message)s")


def setup_logging(args):
    logging_dir = os.path.join(args.result_dir, "logs")

    os.makedirs(logging_dir, exist_ok=True)

    file_handler = logging.FileHandler(
        os.path.join(logging_dir, "normal-{}-{}.log".format(args.worker_id, datetime_str)), encoding="utf-8")
    debug_handler = logging.FileHandler(
        os.path.join(logging_dir, "debug-{}-{}.log".format(args.worker_id, datetime_str)), encoding="utf-8")
    stdout_handler = logging.StreamHandler(sys.stdout)
    sdebug_handler = logging.FileHandler(
        os.path.join(logging_dir, "sdebug-{}-{}.log".format(args.worker_id, datetime_str)), encoding="utf-8")

    file_handler.setLevel(logging.INFO)
    debug_handler.setLevel(logging.DEBUG)
    stdout_handler.setLevel(logging.INFO)
    sdebug_handler.setLevel(logging.DEBUG)

    file_handler.setFormatter(formatter)
    debug_handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)
    sdebug_handler.setFormatter(formatter)

    # stdout_handler.addFilter(logging.Filter("desktopenv"))
    # sdebug_handler.addFilter(logging.Filter("desktopenv"))
    stdout_handler.addFilter(logging.Filter("myexp"))
    sdebug_handler.addFilter(logging.Filter("myexp"))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(sdebug_handler)


logger = logging.getLogger("myexp.run")


def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Agent Loop")

    parser.add_argument("--max_steps", type=int, default=3)
    parser.add_argument("--max_trajectory_length", type=int, default=1)

    parser.add_argument("--model", type=str,
                        default="gpt-5")  # gpt-4o-mini or gpt-4-vision-preview or gpt-4o or gpt-4-1106-vision-preview
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top_p", type=float, default=None)
    parser.add_argument("--max_tokens", type=int, default=8192)
    parser.add_argument("--stop_token", type=str, default=None)

    parser.add_argument("--domain", type=str, default="test")
    parser.add_argument("--test_all_meta_path", type=str,
                        default="/data2/ajx/codes/ROCK/my_exp/myexp_run_text2cad_test_batch.json")  # or test_custom.json for a single task
    parser.add_argument("--test_config_base_dir", type=str, default="/data2/ajx/codes/ROCK/my_exp/Text2CAD")

    parser.add_argument("--result_dir", type=str, default="/data2/ajx/codes/ROCK/my_exp/results")
    parser.add_argument("--trial_id", type=str, default="0")

    parser.add_argument("--worker_id", type=int, default=0, help="ID of the worker")
    parser.add_argument("--num_workers", type=int, default=1, help="Total number of workers")

    # api
    # parser.add_argument("--api_server", type=str, default="azure")
    # parser.add_argument("--base_url", type=str, default="https://gpt.yunstorm.com/")
    # parser.add_argument("--api_key", type=str, default="b6d0c8453a36428abb63550487388a48")
    parser.add_argument("--api_server", type=str, default="claudeshop")
    parser.add_argument("--base_url", type=str, default="http://35.220.164.252:3888")
    parser.add_argument("--api_key", type=str, default="sk-jP3p1PFYeQ7mroJCCqMkh10G8CnwS1ConcpBdtMRAFqgxDPN")


    # sandbox_info
    parser.add_argument("--sandbox_info_file", type=str, default=None)

    # others
    parser.add_argument("--with_example", action='store_true')
    parser.add_argument("--task_type", type=str, default="3d_model")
    parser.add_argument("--software", type=str, default="sldworks")
    parser.add_argument("--with_rag", action='store_true')

    args, unknownargs = parser.parse_known_args()
    return args


async def test(
        args: argparse.Namespace,
        test_all_meta: dict,
        sandbox_info: dict
) -> None:
    scores = []
    max_steps = args.max_steps

    env = MyDesktopEnv(sandbox_info)
    agent = PromptAgent(
        model=args.model,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        max_steps=args.max_steps,
        max_trajectory_length=args.max_trajectory_length,
        api_server=args.api_server,
        base_url=args.base_url,
        api_key=args.api_key,

        with_example=args.with_example,
        task_type=args.task_type,
        software=args.software,

        with_rag = args.with_rag
    )

    close_window_idx = 0
    for domain in tqdm(test_all_meta, desc="Domain"):
        for example_id in tqdm(test_all_meta[domain], desc="Example", leave=False):
            config_file = os.path.join(args.test_config_base_dir, f"examples/{domain}/{example_id}.json")
            logger.info(f'Config File: {config_file}')

            with open(config_file, "r", encoding="utf-8") as f:
                example = json.load(f)

            # # ### 设置close window，避免每次都重启sldworks/inventor
            # if close_window_idx % 100 == 0:
            #     example['close_window'] = True
            # else:
            #     example['close_window'] = False
            # close_window_idx += 1
            example['close_window'] = True

            ### 修改instruction，加上前缀说明任务类型和软件
            if args.task_type == '3d_model':
                if args.software == 'sldworks':
                    example['instruction'] = "Model this part in Solidworks: "+example['instruction']
                elif args.software == 'inventor':
                    example['instruction'] = "Model this part in Inventor: "+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
                    exit(0)
            elif args.task_type == '2d_sketch':
                if args.software == 'autocad':
                    example['instruction'] = "Draft this sketch in AutoCAD: "+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
                    exit(0)
            elif args.task_type == 'assembly':
                if args.software == 'inventor':
                    example['instruction'] = "Build this assembly in Inventor: "+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
                    exit(0)
            elif args.task_type == 'modify':
                pass    # modify是根据代码，所以不分软件
            elif args.task_type == 'drawing':
                if args.software == 'sldworks':
                    example['instruction'] = ""+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
                    exit(0)
            elif args.task_type == 'mass_property':
                if args.software == 'sldworks':
                    example['instruction'] = ""+example['instruction']
                elif args.software == 'inventor':
                    example['instruction'] = ""+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
                    exit(0)
            elif args.task_type == 'interference_detection':
                if args.software == 'sldworks':
                    example['instruction'] = ""+example['instruction']
                elif args.software == 'inventor':
                    example['instruction'] = ""+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
                    exit(0)
            elif args.task_type == '3d_model+drawing':
                if args.software == 'sldworks':
                    example['instruction'] = ""+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
            elif args.task_type == 'assembly+interference_detection':
                if args.software == 'inventor':
                    example['instruction'] = ""+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
            elif args.task_type == '3d_model+mass_property':
                if args.software in ['sldworks', 'inventor']:
                    example['instruction'] = ""+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
            elif args.task_type == '3d_model+modify':
                if args.software in ['sldworks', 'inventor']:
                    example['instruction'] = ""+example['instruction']
                else:
                    logger.error(f"Invalid software!!! {software}")
            else:
                logger.error(f"Invalid task type!!! {task_type}")
                exit(0)

            logger.info(f"Example: {example}")

            if args.with_example:
                example_result_dir = os.path.join(
                    args.result_dir,
                    'with_example',
                    args.model,
                    args.trial_id,
                    domain,
                    args.software,
                    example_id
                )
                if args.with_rag:
                    example_result_dir = os.path.join(
                        args.result_dir,
                        'with_example',
                        'with_rag',
                        args.model,
                        args.trial_id,
                        domain,
                        args.software,
                        example_id
                    )
            else:
                example_result_dir = os.path.join(
                    args.result_dir,
                    'without_example',
                    args.model,
                    args.trial_id,
                    domain,
                    args.software,
                    example_id
                )
                if args.with_rag:
                    example_result_dir = os.path.join(
                        args.result_dir,
                        'without_example',
                        'with_rag',
                        args.model,
                        args.trial_id,
                        domain,
                        args.software,
                        example_id
                    )

            os.makedirs(example_result_dir, exist_ok=True)
            logger.info(f'Example result dir: {example_result_dir}')

            # Example Logging Config {{{
            os.makedirs(os.path.join(example_result_dir, "logs"), exist_ok=True)
            task_log_handler = logging.FileHandler(
                os.path.join(example_result_dir, "logs", "task-{}-{}.log".format(args.worker_id, datetime_str)),
                encoding="utf-8")
            task_log_handler.setLevel(logging.DEBUG)
            task_log_handler.setFormatter(formatter)
            root_logger.addHandler(task_log_handler)
            # }}} Example Logging Config

            # example start running
            try:
                # env.controller.start_recording()
                lib_run_single.run_single_example(agent, env, max_steps, example, example_result_dir, scores, args.task_type, args.software, args.with_rag)

            except Exception as e:
                logger.error(f"Exception in {domain}/{example_id}: {e}")
                error_traceback = traceback.format_exc()
                logger.error(error_traceback)
                # env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))
                # Write error details to traj.jsonl
                with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                    f.write(json.dumps({
                        "Error": f"Exception in {domain}/{example_id}",
                        "Exception": str(e),
                        "Traceback": error_traceback,
                    }))
                    f.write("\n")
            else:
                logger.info(f"Finished {domain}/{example_id}")
            finally:
                # env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))
                # Cleanup task log handler
                root_logger.removeHandler(task_log_handler)
                task_log_handler.close()

    # env.close()
    # logger.info(f"UPDATED SCORES: {scores}")

    if len(scores) == 0:
        logger.info("No examples finished.")
    else:
        logger.info(f"Average score: {sum(scores) / len(scores)}")


if __name__ == '__main__':
    args = config()
    setup_logging(args)
    logger.info(f'Args: {args}')

    with open(args.sandbox_info_file, 'r', encoding='utf-8') as f:
        sandbox_info = json.load(f)[str(args.worker_id)]

    with open(args.test_all_meta_path, "r", encoding="utf-8") as f:
        test_all_meta = json.load(f)

    logger.info(f"\nTESTING ON TASK JSON PATH: {args.test_all_meta_path}")

    if args.domain != "all":
        test_all_meta = {args.domain: test_all_meta[args.domain]}

    test_file_list = test_all_meta

    # distribute tasks among workers
    # Flatten your dict into a list of tasks
    all_tasks_test = []
    for domain in test_file_list:
        for example_id in test_file_list[domain]:
            if args.with_example:
                example_result_dir = os.path.join(
                    args.result_dir,
                    'with_example',
                    args.model,
                    args.trial_id,
                    domain,
                    args.software,
                    example_id
                )
                if args.with_rag:
                    example_result_dir = os.path.join(
                        args.result_dir,
                        'with_example',
                        'with_rag',
                        args.model,
                        args.trial_id,
                        domain,
                        args.software,
                        example_id
                    )
            else:
                example_result_dir = os.path.join(
                    args.result_dir,
                    'without_example',
                    args.model,
                    args.trial_id,
                    domain,
                    args.software,
                    example_id
                )
                if args.with_rag:
                    example_result_dir = os.path.join(
                        args.result_dir,
                        'without_example',
                        'with_rag',
                        args.model,
                        args.trial_id,
                        domain,
                        args.software,
                        example_id
                    )
            if os.path.exists(os.path.join(example_result_dir, 'result.txt')):
                continue
            else:
                all_tasks_test.append((domain, example_id))

    # Calculate the start and end indices of the tasks for this worker
    tasks_per_worker = len(all_tasks_test) // args.num_workers
    extra = len(all_tasks_test) % args.num_workers  # calculate the number of tasks that can't be evenly distributed

    start_index = args.worker_id * tasks_per_worker + min(args.worker_id,
                                                          extra)  # 就是让前几个worker拿到extra的任务，小于extra的worker_id每个worker多拿一个任务
    if args.worker_id < extra:
        end_index = start_index + tasks_per_worker + 1
    else:
        end_index = start_index + tasks_per_worker

    # Slice the tasks for this worker
    tasks_for_this_worker = all_tasks_test[start_index:end_index]

    # Convert the list of tasks back to a dictionary
    test_file_list_worker = {}
    for domain, example_id in tasks_for_this_worker:
        if domain not in test_file_list_worker:
            # create an empty list to which elements will be appended
            test_file_list_worker[domain] = []
        test_file_list_worker[domain].append(example_id)

    # log which tasks this worker is doing
    logger.info(f"Worker {args.worker_id} is doing tasks: {test_file_list_worker}")

    asyncio.run(test(args, test_file_list_worker, sandbox_info))
