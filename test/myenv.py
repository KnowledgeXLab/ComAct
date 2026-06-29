import asyncio
from datetime import datetime
import json
import logging
import subprocess
import time
from typing import Optional, Dict, Any, Tuple, Union, List
import base64
import os
import httpcore
import httpx
import requests
from rock.actions.envs.base import Env
from rock.actions import CreateBashSessionRequest
from rock.sdk.sandbox.client import Sandbox
from rock.sdk.sandbox.config import SandboxConfig

import math

from eval_cd import *
from eval_cd_sketch import *
from eval_json import *

logger = logging.getLogger("myexp.myenv")

class MyDesktopEnv(Env):
    def __init__(self,
                 sandbox_info
                 ):

        self.sandbox_info = sandbox_info
        """
        {
            "worker_id": worker_id,
            "sandbox_id": self.sandbox.sandbox_id,
            "sandbox_host_ip": self.sandbox.host_ip,
            "sandbox_host_port": self.sandbox.host_name,
            "browser_url": self.browser_url,
            "vm_server_url": self.vm_url
        }
        """
        self.vm_url = self.sandbox_info['vm_server_url']
        self.controller = MyEnvController(http_server=self.vm_url)
        if not self.controller.get_screenshot():
            exit(0)
        self.task_config = None


    def _get_obs(self):
        start_get_obs_time = datetime.now()
        screenshot = self.controller.get_screenshot()
        if not screenshot:
            exit(0)
        # accessibility_tree = self.controller.get_accessibility_tree(backend=self.a11y_backend) if self.require_a11y_tree else None
        # terminal = self.controller.get_terminal_output()
        end_get_obs_time = datetime.now()
        return {
            "screenshot": screenshot,
            # "accessibility_tree": accessibility_tree,
            "terminal": {},
            # "reward": 0,
            'get_obs_time': (end_get_obs_time - start_get_obs_time).total_seconds()
        }

    def reset(self, task_config: Optional[Dict[str, Any]] = None, seed=None, **kwargs):
        logger.info("Resetting environment...")

        # logger.info("Closing current opened windows")
        # self.controller.close_all_window()

        if task_config['close_window']:
            logger.info("Closing current opened windows")
            self.controller.close_all_window()

        logger.info("Cleaning up task files...")
        self.controller.clean_up_files()

        # logger.info("launching Solidworks")
        # self.controller.launch_sldworks()

        # logger.info("Activating Solidworks")
        # while not self.controller.activate_window(window_name="SOLIDWORKS"):
        #     time.sleep(5)

        observation = self._get_obs()

        self.task_config = task_config
        return observation

    def step(self, py_code, decision):
        reward = 0.0
        terminated = False
        truncated = False

        done = False
        fail = False

        ###
        if 'DONE' in decision.upper():
            done = True
            terminated=True
        elif 'FAIL' in decision.upper():
            fail = True
            terminated=True
        elif 'CODE' in decision.upper():
            pass
        else:
            logger.error("Invalid decision: %s", decision)
            # exit(0)

        logger.info("Creating code file C:/Users/Docker/Downloads/pycodes.py")
        path = self.controller.create_file(path='C:/Users/Docker/Downloads/pycodes.py', content=py_code)
        if not path:
            exit(0)

        run_code_start_time = datetime.now()
        logger.info("Running code file...")
        terminal_outputs = self.controller.run_codes(path='C:/Users/Docker/Downloads/pycodes.py')
        if not terminal_outputs:
            exit(0)
        # ####################################
        # ### with hint 3d models sldworks ###
        # gen_stl_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.stl')
        # gen_stl_content = self.controller.get_file(file_path=gen_stl_path) if self.controller.get_file(file_path=gen_stl_path) else None
        # if not gen_stl_content:
        #     terminal_outputs["note"] = "Expected output file was not created!"
        # ####################################

        run_code_end_time =  datetime.now()

        observation = self._get_obs()
        observation['terminal'] = terminal_outputs

        return observation, terminated, done, fail, (run_code_end_time-run_code_start_time).total_seconds()

    def evaluate_3d_model_modify(self, example_result_dir):
        gt_stl_3d_model = self.task_config['3d_model_gt_stl']
        gt_stl_modify = self.task_config['modify_gt_stl']
        tau = 1e-3

        gen_stl_path_3d_model = os.path.join('C:/Users/Docker/Downloads/',self.task_config['qid']+'.stl')
        gen_stl_content_3d_model = self.controller.get_file(file_path=gen_stl_path_3d_model) if self.controller.get_file(file_path=gen_stl_path_3d_model) else None
        gen_stl_3d_model = os.path.join(example_result_dir, self.task_config['qid']+'_gen.stl')

        gen_stl_path_modify = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.stl')
        gen_stl_content_modify = self.controller.get_file(file_path=gen_stl_path_modify) if self.controller.get_file(file_path=gen_stl_path_modify) else None
        gen_stl_modify = os.path.join(example_result_dir, self.task_config['id']+'_gen.stl')

        gen_step_path_3d_model = os.path.join('C:/Users/Docker/Downloads/', self.task_config['qid'] + '.step')
        gen_step_content_3d_model = self.controller.get_file(file_path=gen_step_path_3d_model) if self.controller.get_file(file_path=gen_step_path_3d_model) else None
        gen_step_3d_model = os.path.join(example_result_dir, self.task_config['qid']+'_gen.step')


        os.makedirs(os.path.dirname(gen_stl_3d_model), exist_ok=True)
        os.makedirs(os.path.dirname(gen_stl_modify), exist_ok=True)
        os.makedirs(os.path.dirname(gen_step_3d_model), exist_ok=True)

        if gen_step_content_3d_model:
            with open(gen_step_3d_model, 'wb') as f:
                f.write(gen_step_content_3d_model)

        if gen_stl_content_3d_model:
            with open(gen_stl_3d_model, 'wb') as f:
                f.write(gen_stl_content_3d_model)
            cd_3d_model = chamfer_dist(normalize_pc(stl2pc(gt_stl_3d_model, n_points=10000, seed=123)), normalize_pc(stl2pc(gen_stl_3d_model, n_points=10000, seed=123)))
            if cd_3d_model <= tau:
                reward_3d_model = 1.0
            else:
                reward_3d_model = 0.0
        else:
            reward_3d_model = 0.0
            cd_3d_model = -1
            gen_stl_3d_model = None
            gen_step_3d_model = None

        if gen_stl_content_modify:
            with open(gen_stl_modify, 'wb') as f:
                f.write(gen_stl_content_modify)
            cd_modify = chamfer_dist(normalize_pc(stl2pc(gt_stl_modify, n_points=10000, seed=123)), normalize_pc(stl2pc(gen_stl_modify, n_points=10000, seed=123)))
            if cd_modify <= tau:
                reward_modify = 1.0
            else:
                reward_modify = 0.0
        else:
            reward_modify = 0.0
            cd_modify = -1
            gen_stl_modify = None

        return reward_3d_model, cd_3d_model, gen_stl_3d_model, gen_step_3d_model, reward_modify, cd_modify, gen_stl_modify
        

    def evaluate_3d_model(self, example_result_dir):
        gt_stl = self.task_config['gt_stl']
        tau = 1e-3

        gen_stl_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.stl')
        gen_stl_content = self.controller.get_file(file_path=gen_stl_path) if self.controller.get_file(file_path=gen_stl_path) else None
        # gen_stl = self.task_config['gen_stl']
        gen_stl = os.path.join(example_result_dir, self.task_config['id']+'_gen.stl')

        ### gen_step
        gen_step_path = os.path.join('C:/Users/Docker/Downloads/', self.task_config['id'] + '.step')
        gen_step_content = self.controller.get_file(file_path=gen_step_path) if self.controller.get_file(file_path=gen_step_path) else None
        # gen_step = self.task_config['gen_step']
        gen_step = os.path.join(example_result_dir, self.task_config['id']+'_gen.step')


        os.makedirs(os.path.dirname(gen_stl), exist_ok=True)
        os.makedirs(os.path.dirname(gen_step), exist_ok=True)


        # if gen_stl_content and gen_step_content:
        #     with open(gen_stl, 'wb') as f:
        #         f.write(gen_stl_content)

        #     with open(gen_step, 'wb') as f:
        #         f.write(gen_step_content)

        #     cd = chamfer_dist(normalize_pc(stl2pc(gt_stl, n_points=10000, seed=123)), normalize_pc(stl2pc(gen_stl, n_points=10000, seed=123)))
        #     if cd <= tau:
        #         reward = 1.0
        #     else:
        #         reward = 0.0
        #     return reward, cd, gen_stl, gen_step
        #     # return cd, gen_stl, gen_step
        # else:
        #     return 0.0, -1, None, None
        #     # return -1, gen_stl, gen_step

        # TODO: 是否一定要保存step
        if gen_step_content:
            with open(gen_step, 'wb') as f:
                f.write(gen_step_content)

        if gen_stl_content:
            with open(gen_stl, 'wb') as f:
                f.write(gen_stl_content)
            cd = chamfer_dist(normalize_pc(stl2pc(gt_stl, n_points=10000, seed=123)), normalize_pc(stl2pc(gen_stl, n_points=10000, seed=123)))
            if cd <= tau:
                reward = 1.0
            else:
                reward = 0.0
            return reward, cd, gen_stl, gen_step
            # return cd, gen_stl, gen_step
        else:
            return 0.0, -1, None, None
            # return -1, gen_stl, gen_step

    def evaluate_2d_sketch(self, example_result_dir):
        gt_dxf = self.task_config['gt_dxf']
        tau = 1e-30

        gen_dxf_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.dxf')
        gen_dxf_content = self.controller.get_file(file_path=gen_dxf_path) if self.controller.get_file(file_path=gen_dxf_path) else None
        gen_dxf = os.path.join(example_result_dir, self.task_config['id']+'_gen.dxf')

        os.makedirs(os.path.dirname(gen_dxf), exist_ok=True)

        if gen_dxf_content:
            with open(gen_dxf, 'wb') as f:
                f.write(gen_dxf_content)

            cd = chamfer_dist_2d(normalize_pc_2d(dxf2pc(gt_dxf, n_samples=1000)), normalize_pc_2d(dxf2pc(gen_dxf, n_samples=1000)))
            if cd <= tau:
                reward = 1.0
            else:
                reward = 0.0
            return reward, cd, gen_dxf
        else:
            return 0.0, -1, None

    def evaluate_mass_properties(self, example_result_dir):
        gen_json_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.json')
        gen_json = os.path.join(example_result_dir, self.task_config['id']+'_gen.json')
        gen_json_content = self.controller.get_file(file_path=gen_json_path)

        gt_mass_properties = self.task_config['gt']

        if gen_json_content:
            with open(gen_json, 'wb') as f:
                f.write(gen_json_content)

            with open(gen_json, 'r', encoding='utf-8') as f:
                gen_mass_properties = json.load(f)
            
            if check_mass_property_json_res(gt_mass_properties, gen_mass_properties):
                score = 1.0
            else:
                score = 0.0
            return score, 1.0, gen_json, gen_mass_properties, gt_mass_properties
        else:
            return 0.0, 0.0, None, {}, gt_mass_properties

    def evaluate_interference_detection(self, example_result_dir):
        gen_json_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.json')
        gen_json = os.path.join(example_result_dir, self.task_config['id']+'_gen.json')
        gen_json_content = self.controller.get_file(file_path=gen_json_path)

        gt_interference_detection = self.task_config['gt']

        if gen_json_content:
            with open(gen_json, 'wb') as f:
                f.write(gen_json_content)

            with open(gen_json, 'r', encoding='utf-8') as f:
                gen_interference_detection = json.load(f)
            
            if check_interference_detection_json_res(gt_interference_detection, gen_interference_detection):
                score = 1.0
            else:
                score = 0.0
            return score, 1.0, gen_json, gen_interference_detection, gt_interference_detection
        else:
            return 0.0, 0.0, None, {}, gt_interference_detection

    def evaluate_draw(self, example_result_dir):
        gen_pdf_path = os.path.join('C:/Users/Docker/Downloads/',self.task_config['id']+'.pdf')
        gen_pdf = os.path.join(example_result_dir, self.task_config['id']+'_gen.pdf')
        gen_pdf_content = self.controller.get_file(file_path=gen_pdf_path)
        if gen_pdf_content:
            with open(gen_pdf, 'wb') as f:
                f.write(gen_pdf_content)

            terminal_output = self.controller.execute_python_command(command=[
                "C:/Users/Docker/AppData/Local/Programs/Python/Python310/python.exe",
                "C:/Users/Docker/Documents/check_sldworks_drawing.py",
                "--id", self.task_config['id'],
                "--required_views", "*Front", "*Top", "*Right", "*Isometric",
                "--required_dim"
            ])
            logger.info(f"Evaluation terminal output: {terminal_output}")
            res_content = self.controller.get_file(file_path='C:/Users/Docker/Downloads/result.txt')
            score = float(res_content.decode('utf-8').strip())
            return score, 1.0, gen_pdf  # success, code_valid, gen_pdf
        else:
            return 0.0, 0.0, None   # success, code_valid, gen_pdf
    
    def render(self):
        """Returns the current screenshot for rendering."""
        if not self.controller:
            return None
        return self.controller.get_screenshot()



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
            logger.info(f"launch_setup(), payload: {payload}")
            logger.info(f"launch_setup(), response: {response}")
            if response.status_code == 200:
                logger.info("Command executed successfully: %s", response.text)
            else:
                logger.error("Failed to launch application. Status code: %s", response.text)
        except requests.exceptions.RequestException as e:
            logger.error("An error occurred while trying to send the request: %s", e)

    def launch_sldworks(self):
        command = "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"
        self.launch(command=command)
        time.sleep(15)

    def get_screenshot(self):
        attempt_count = 0
        max_attempts = 5
        while attempt_count < max_attempts:
            try:
                response = requests.get(self.http_server + "/screenshot")
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error("Failed to get screenshot. Status code: %d. Retrying...", response.status_code)
            except Exception as e:
                logger.error(f"An error occurred while trying to get the screenshot: {e}")
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
                    logger.error("Failed to get terminal output. Status code: %d", response.status_code)
            except Exception as e:
                logger.error(f"An error occurred while trying to get the terminal output: {e}")
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
                logger.info("Command executed successfully: %s", response.text)
            else:
                logger.error(f"Failed to clear task files. Status code: %s", response.text)
        except requests.exceptions.RequestException as e:
            logger.error("An error occurred while trying to send the request: %s", e)

    def close_all_window(self):
        payload = json.dumps({})
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(self.http_server + "/setup" + "/close_all", headers=headers, data=payload)
            if response.status_code == 200:
                logger.info("Command executed successfully: %s", response.text)
            else:
                logger.error(f"Failed to close all windows. Status code: %s", response.text)
        except requests.exceptions.RequestException as e:
            logger.error("An error occurred while trying to send the request: %s", e)

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
    #             logger.info("Command executed successfully: %s", response.text)
    #             return path
    #         else:
    #             logger.error(f"Failed to create file. Status code: %s", response.text)
    #     except Exception as e:
    #         logger.error(f"An error occurred while trying to create a file: %s", e)
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
                logger.info("Activate Window successfully: %s", response.text)
                return True
            else:
                logger.error(f"Failed to activate window. Status code: %s", response.text)
        except Exception as e:
            logger.error(f"Error activating window: {e}")
        return False


    def execute_python_command(self, command, shell=False):
        payload = json.dumps({"command": command, "shell": shell})
        headers = {"Content-Type": "application/json"}
        attempt_count = 0
        max_attempts = 3
        while attempt_count < max_attempts:
            try:
                response = requests.post(self.http_server + "/execute", headers=headers, data=payload)
                if response.status_code == 200:
                    return response.json()  # 返回包含 output, error, returncode 的字典
                else:
                    logger.error(f"Failed to execute command. Status: {response.status_code}. Retrying...")
            except Exception as e:
                logger.error(f"Error during executint command: {e}")

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
                logger.info(f"GET_FILE, file_path: {file_path}")
                if response.status_code == 200:
                    logger.info("File downloaded successfully")
                    return response.content
                else:
                    logger.error("Failed to get file. Status code: %d", response.status_code)
                    return None
            except Exception as e:
                logger.error(f"Error during getting file: {e}")
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
                logger.error(f"Transfer interupted. Failed to write file {path}!")
                return None
                
        logger.info(f"File {path} transfer success.")
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
            response = requests.post(self.http_server + "/setup/create_file_b64", 
                                     headers=headers, data=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Network request error: {e}")
            return False
