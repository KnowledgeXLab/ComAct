import asyncio
from concurrent.futures import ThreadPoolExecutor
# asyncio.get_event_loop().set_default_executor(ThreadPoolExecutor(max_workers=256))

import json
import re
import time
from typing import Any, Dict, List, Tuple, Union
import base64
import os
import httpcore
import httpx
import requests

from eval_cd import *
from eval_cd_sketch import *


# logger = get_logger()

class MyComEnv():
    def __init__(self, vm_url):
        self.vm_url = vm_url
        self.controller = MyEnvController(http_server=self.vm_url)
        self.task_config = None

    async def _get_obs(self):
        screenshot = await asyncio.to_thread(self.controller.get_screenshot)  # bytes
        return {
            "screenshot": screenshot,
            "terminal": {},
        }
    
    async def reset(self, config):
        # print("Resetting environment...")
        task_config = config.data_dict
        # print("Closing current opened windows")
        # self.controller.close_all_window()

        if task_config['close_window']:
            # print("Closing current opened windows")
            # self.controller.close_all_window()
            await asyncio.to_thread(self.controller.close_all_window)

        # print("Cleaning up task files...")
        # self.controller.clean_up_files()
        await asyncio.to_thread(self.controller.clean_up_files)

        observation = await self._get_obs()
        return observation    

    def parse_py_codes(self, response: str):
        matches = re.findall(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if matches:
            return matches[-1].strip()
        else:
            return None
    
    def parse_decision(self, response: str):
        matches = re.findall(r'```decision\s*(.*?)\s*```', response, re.DOTALL)
        if matches:
            return matches[-1].strip()
        else:
            return None

    async def test_step(self):
        terminal_outputs = await asyncio.to_thread(self.controller.run_codes, 'C:/Users/Docker/Downloads/pycodes.py')

        observation = await self._get_obs()
        observation['terminal'] = terminal_outputs
        return observation

    async def step(self, action):
        # completion = action[-1]['content']

        # py_code = self.parse_py_codes(completion)
        # decision = self.parse_decision(completion)

        py_code = self.parse_py_codes(action)
        decision = self.parse_decision(action)

        reward = 0.0
        terminated = False
        done = False
        fail = False

        #####
        if not decision:
            decision = 'CODE'
        #####

        if py_code and decision:
            if 'DONE' in decision.upper():
                done = True
                terminated=True
            elif 'FAIL' in decision.upper():
                fail = True
                terminated=True  # TODO: 没有惩罚输出错误decision的
            
            # self.controller.create_file(path='C:/Users/Docker/Downloads/pycodes.py', content=py_code)
            # terminal_outputs = self.controller.run_codes(path='C:/Users/Docker/Downloads/pycodes.py')
            await asyncio.to_thread(self.controller.create_file, 'C:/Users/Docker/Downloads/pycodes.py', py_code)
            terminal_outputs = await asyncio.to_thread(self.controller.run_codes, 'C:/Users/Docker/Downloads/pycodes.py')

            observation = await self._get_obs()
            observation['terminal'] = terminal_outputs

            step_info = {
                "task_config": self.task_config,
                # "completion": completion,
                "completion": action,
                "py_code": py_code,
                "decision": decision,
                "terminated": terminated,
                "done": done,
                "fail": fail,
                "terminal_outputs": observation['terminal']
            }
        else:
            observation = await self._get_obs()
            observation['terminal'] = "No parsed pycodes or decision!"

            step_info = {
                "task_config": self.task_config,
                # "completion": completion,
                "completion": action,
                "py_code": py_code if py_code else "Invalid",
                "decision": decision if decision else "Invalid",
                "terminated": terminated,
                "done": done,
                "fail": fail,
                "terminal_outputs": observation['terminal']
            }
        return observation, reward, terminated, done, fail, step_info

    async def evaluate(self):
        if self.task_config['task_type'] in ['3d_model', 'assembly']:
            # return self.evaluate_3d_model()
            return await asyncio.to_thread(self.evaluate_3d_model)
        elif self.task_config['task_type'] == '2d_sketch':
            # return self.evaluate_2d_sketch()
            return await asyncio.to_thread(self.evaluate_2d_sketch)
        else:
            pass    # TODO

    

    def evaluate_3d_model(self):
        print('In evaluate_3d_model...')
        GT_STL_DIR = '/nvme/aijiaxin/dataset/COMCAD_new/grpo/GT_STL'
        GEN_STL_DIR = '/nvme/aijiaxin/cache/msswift/gen_stl'

        gt_stl = os.path.join(GT_STL_DIR, self.task_config['id']+'.stl')
        tau = 1e-3

        gen_stl_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.stl')

        file_content = self.controller.get_file(file_path=gen_stl_path)
        gen_stl_content = file_content if file_content else None
        gen_stl = os.path.join(GEN_STL_DIR, self.task_config['id']+'_gen.stl')

        # ### gen_step
        # gen_step_path = os.path.join('C:/Users/Docker/Downloads/', self.task_config['id'] + '.step')
        # gen_step_content = self.controller.get_file(file_path=gen_step_path) if self.controller.get_file(file_path=gen_step_path) else None
        # gen_step = os.path.join(GEN_STEP_DIR, self.task_config['id']+'_gen.step')

        # os.makedirs(os.path.dirname(gen_stl), exist_ok=True)
        # os.makedirs(os.path.dirname(gen_step), exist_ok=True)

        # if gen_stl_content and gen_step_content:
        if gen_stl_content:
            with open(gen_stl, 'wb') as f:
                f.write(gen_stl_content)
            try:
                print(f'GT_STL: {gt_stl}; GEN_STL: {gen_stl}')
                cd = chamfer_dist(
                    normalize_pc(stl2pc(gt_stl, n_points=10000, seed=123)),
                    normalize_pc(stl2pc(gen_stl, n_points=10000, seed=123))
                )
                print(f'=============== CD: {cd} =================')

                if cd <= 1e-5:
                    reward = 1.0
                elif cd > 1e-3:
                    reward = 0.0
                else:
                    slope = (0.01 - 1.0) / (1e-3 - 1e-5)
                    reward = max(0.0, 1.0 + (cd - 1e-5) * slope)


                # if cd <= 1e-5:
                #     reward = 1.0
                # elif cd > 0.01:
                #     reward = 0.0
                # else:
                #     slope = (0.01 - 1.0) / (0.01 - 1e-5)
                #     reward = max(0.0, 1.0 + (cd - 1e-5) * slope)

                return reward, cd

            except Exception as e:
                print(f'Calculate CD Failed! {e}')
                return 0.0, -2
        else:
            return 0.0, -1

    def evaluate_2d_sketch(self):
        print('In evaluate_2d_sketch...')
        GT_DXF_DIR = '/nvme/aijiaxin/dataset/COMCAD_new/grpo/GT_DXF'
        GEN_DXF_DIR = '/nvme/aijiaxin/cache/msswift/gen_dxf'
        gt_dxf = os.path.join(GT_DXF_DIR, self.task_config['id']+'.dxf')
        tau = 1e-30

        gen_dxf_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.dxf')

        file_content = self.controller.get_file(file_path=gen_dxf_path)
        gen_dxf_content = file_content if file_content else None
        gen_dxf = os.path.join(GEN_DXF_DIR, self.task_config['id']+'_gen.dxf')

        # os.makedirs(os.path.dirname(gen_dxf), exist_ok=True)

        if gen_dxf_content:
            with open(gen_dxf, 'wb') as f:
                f.write(gen_dxf_content)

            try:
                print(f'GT_DXF: {gt_dxf}; GEN_DXF: {gen_dxf}')
                cd = chamfer_dist_2d(normalize_pc_2d(dxf2pc(gt_dxf, n_samples=1000)), normalize_pc_2d(dxf2pc(gen_dxf, n_samples=1000)))
                print(f'=============== CD: {cd} =================')
                # if cd <= tau:
                #     reward = 1.0
                # else:
                #     reward = 0.0
                # return reward, cd

                if cd <= 1e-32:
                    reward = 1.0
                elif cd > 1e-30:
                    reward = 0.0
                else:
                    log_cd = math.log10(cd)
                    log_low = -32 # math.log10(1e-32)
                    log_high = -30 # math.log10(1e-30)
                    # 从 1.0 线性降到 0.01
                    slope = (0.01 - 1.0) / (log_high - log_low)
                    reward = max(0.0, (1.0 + (log_cd - log_low) * slope))

                    # slope = (0.01 - 1.0) / (1e-30 - 1e-32)
                    # reward = max(0.0, 1.0 + (cd - 1e-32) * slope)

                return reward, cd

            except Exception as e:
                print(f'Calculate CD Failed! {e}')
                return 0.0, -2
        else:
            return 0.0, -1

    async def close(self):
        pass



class MyEnvController:
    def __init__(self, http_server: str):
        self.http_server = http_server

    def launch(self, command: Union[str, List[str]], shell=False):
        """
        Launches an application in the VM.
        """
        if not command:
            raise Exception("Empty command to launch.")

        if not shell and isinstance(command, str) and len(command.split()) > 1:
            logger.warning("Command should be a list of strings. Now it is a string. Will split it by space.")
            command = command.split()

        payload = json.dumps({"command": command, "shell": shell})
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.http_server + "/setup/launch", headers=headers, data=payload)
            # print(f"launch_setup(), payload: {payload}")
            # print(f"launch_setup(), response: {response}")
            if response.status_code == 200:
                print("Command executed successfully: %s", response.text)
            else:
                print("Failed to launch application. Status code: %s", response.text)
        except requests.exceptions.RequestException as e:
            print("An error occurred while trying to send the request: %s", e)

    # def launch_sldworks(self):
    #     command = "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"
    #     self.launch(command=command)
    #     time.sleep(15)

    def get_screenshot(self):
        attempt_count = 0
        max_attempts = 5
        while attempt_count < max_attempts:
            try:
                response = requests.get(self.http_server + "/screenshot")
                if response.status_code == 200:
                    return response.content
                else:
                    print("Failed to get screenshot. Status code: %d. Retrying...", response.status_code)
            except Exception as e:
                print(f"An error occurred while trying to get the screenshot: {e}")
            attempt_count += 1
            time.sleep(5)
        return None

    def get_terminal_output(self):
        attempt_count = 0
        max_attempts = 5
        while attempt_count < max_attempts:
            try:
                response = requests.get(self.http_server + "/terminal")
                if response.status_code == 200:
                    return response.json()["output"]
                else:
                    print("Failed to get terminal output. Status code: %d", response.status_code)
            except Exception as e:
                print(f"An error occurred while trying to get the terminal output: {e}")
            attempt_count += 1
            time.sleep(10)
        return None

    def clean_up_files(self):
        payload = json.dumps({})
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(self.http_server + "/setup" + "/clear_task_files", headers=headers, data=payload)
            if response.status_code == 200:
                print("Command executed successfully: %s", response.text)
            else:
                print(f"Failed to clear task files. Status code: %s", response.text)
        except requests.exceptions.RequestException as e:
            print("An error occurred while trying to send the request: %s", e)

    def close_all_window(self):
        payload = json.dumps({})
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(self.http_server + "/setup" + "/close_all", headers=headers, data=payload)
            if response.status_code == 200:
                print("Command executed successfully: %s", response.text)
            else:
                print(f"Failed to close all windows. Status code: %s", response.text)
        except requests.exceptions.RequestException as e:
            print("An error occurred while trying to send the request: %s", e)

    # def create_file(self, path, content=""):
    #     """
    #     Creates a file at the specified path with content.
    #     """
    #     payload = json.dumps({
    #         "path": path,
    #         "content": content
    #     })
    #     headers = {
    #         'Content-Type': 'application/json'
    #     }
    #     try:
    #         response = requests.post(self.http_server + "/setup/create_file", headers=headers, data=payload)
    #         if response.status_code == 200:
    #             print("Command executed successfully: %s", response.text)
    #             return path
    #         else:
    #             print(f"Failed to create file. Status code: %s", response.text)
    #     except Exception as e:
    #         print(f"An error occurred while trying to create a file: %s", e)
    #     return None

    def activate_window(self, window_name, auto_maximize=True):
        """
        Brings a specific window to the foreground.
        """
        payload = {
            "window_name": window_name,
            "strict": False,
            "auto_maximize_window": auto_maximize
        }
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(self.http_server + "/setup/activate_window", headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                print("Activate Window successfully: %s", response.text)
                return True
            else:
                print(f"Failed to activate window. Status code: %s", response.text)
        except Exception as e:
            print(f"Error activating window: {e}")
        return False


    def execute_python_command(self, command, shell=False):
        payload = json.dumps({"command": command, "shell": shell})
        headers = {"Content-Type": "application/json"}
        attempt_count = 0
        max_attempts = 5
        while attempt_count < max_attempts:
            try:
                response = requests.post(self.http_server + "/execute", headers=headers, data=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Failed to execute command. Status: {response.status_code}. Retrying...")
            except Exception as e:
                print(f"Error during executint command: {e}")

            attempt_count += 1
            time.sleep(2)
        return None

    def run_codes(self, path):
        return self.execute_python_command(command=[
            "C:/Users/Docker/AppData/Local/Programs/Python/Python310/python.exe",
            path
        ])

    def get_file(self, file_path):
        attempt_count = 0
        max_attempts = 5
        while attempt_count <= max_attempts:
            try:
                response = requests.post(self.http_server + "/file", data={"file_path": file_path})
                print(f"GET_FILE, file_path: {file_path}")
                if response.status_code == 200:
                    print("File downloaded successfully")
                    return response.content
                else:
                    print("Failed to get file. Status code: %d", response.status_code)
                    return None
            except Exception as e:
                print(f"Error during getting file: {e}")
            attempt_count += 1
            time.sleep(3)
        return None

        def start_recording(self):
        """
        Starts recording the screen.
        """
        response = requests.post(self.http_server + "/start_recording")
        if response.status_code == 200:
            logger.info("Recording started successfully")
        else:
            response = requests.post(self.http_server + "/end_recording")
            response = requests.post(self.http_server + "/start_recording")
            if response.status_code == 200:
                logger.info("Recording started successfully")
            else:
                logger.error("Failed to start recording. Status code: %d", response.status_code)

    def end_recording(self, dest: str):
        """
        Ends recording the screen.
        """
        try:
            response = requests.post(self.http_server + "/end_recording")
            if response.status_code == 200:
                logger.info("Recording stopped successfully")
                with open(dest, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            else:
                logger.error("Failed to stop recording. Status code: %d", response.status_code)
                return None
        except Exception as e:
            logger.error("An error occurred while trying to download the recording: %s", e)


    def create_file(self, path, content="", chunk_size=500):
        """Slice the text, encrypt, then send"""
        if not content:
            return self._send_b64_chunk(path, "", mode='w')

        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            mode = 'w' if i == 0 else 'a' 
            
            success = self._send_b64_chunk(path, chunk, mode)
            if not success:
                print(f"Transfer interupted. Failed to write file {path}!")
                return None
                
        print(f"File {path} transfer success.")
        return path

    def _send_b64_chunk(self, path, text_chunk, mode):
        b64_chunk = base64.b64encode(text_chunk.encode('utf-8')).decode('utf-8')
        
        payload = json.dumps({
            "path": path,
            "content": b64_chunk,
            "mode": mode
        })
        headers = {'Content-Type': 'application/json'}
        
        try:
            # 调用虚拟机里刚才写的新接口
            response = requests.post(self.http_server + "/setup/create_file_b64", 
                                     headers=headers, data=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Network Request Error: {e}")
            return False


import queue
import torch

with open('alive_vms.json','r',encoding='utf-8') as f:  # TODO: Your path of alive_vms.json
    alive_vms = json.load(f)

# 1. Get the current GPU ID (Rank) and the total number of GPUs (World Size).
# Note: Fetching via environment variables is the safest approach, as torch.distributed may not have been initialized yet.
rank = int(os.environ.get("RANK", 0))
world_size = int(os.environ.get("WORLD_SIZE", 1))

# 2. Map the current GPU to its assigned virtual machines (VMs).
total_vms = len(alive_vms)
print('Total VMs:', total_vms)
vms_per_rank = total_vms // world_size 
start_idx = rank * vms_per_rank
# Fallback logic: The last GPU takes all remaining virtual machines.
end_idx = start_idx + vms_per_rank if rank < world_size - 1 else total_vms

# 3. Initialize the global environment dictionary and the thread-safe queue.
mycom_envs = {}
mycom_env_queue = queue.Queue()

# 4. Only instantiate the virtual machines assigned to the current GPU.
for i in range(start_idx, end_idx):
    vm_url = alive_vms[str(i)]['vm_server_url']
    env = MyComEnv(vm_url)
    
    mycom_envs[str(i)] = env  
    mycom_env_queue.put(i) 

