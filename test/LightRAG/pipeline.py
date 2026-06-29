import requests
import time
import asyncio
import base64
import numpy as np
import os
import json
from types import SimpleNamespace
from typing import List, Dict, Any

def read_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

async def call_claudeshop_embed(texts, embedding_dim=None, token_tracker=None):
    req_url = ""    # TODO: Fill in your api url
    req_api_key = ""    # TODO: Fill in your api key
    api_model = "text-embedding-3-large"

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {req_api_key}',
        'Content-Type': 'application/json'
    }
    proxies = {
        "http":  "",
        "https": "",
    }

    api_params = {
        "model": api_model,
        "input": texts,
        "encoding_format": "base64",
    }
    if embedding_dim is not None:
        api_params["dimensions"] = embedding_dim

    def _sync_request():
        attempt_count = 0
        max_attempts = 5
        while attempt_count < max_attempts:
            try:
                response = requests.post(req_url, headers=headers, json=api_params, proxies=proxies)
                if response.status_code == 200:
                    return response.json()
                attempt_count += 1
                time.sleep(1)
            except Exception as e:
                attempt_count += 1
                time.sleep(5)
        raise Exception("Embedding API call failed after max attempts")

    response_data = await asyncio.to_thread(_sync_request)

    if token_tracker and "usage" in response_data:
        token_counts = {
            "prompt_tokens": response_data["usage"].get("prompt_tokens", 0),
            "total_tokens": response_data["usage"].get("total_tokens", 0),
        }
        token_tracker.add_usage(token_counts)

    return np.array(
        [
            np.array(dp["embedding"], dtype=np.float32)
            if isinstance(dp["embedding"], list)
            else np.frombuffer(base64.b64decode(dp["embedding"]), dtype=np.float32)
            for dp in response_data["data"]
        ]
    )

async def call_claudeshop_complete(
    messages,
    **kwargs
):
    req_url = ""    # TODO: Fill in your api url
    req_api_key = ""    # TODO: Fill in your api key
    api_model = "gpt-5.4"

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {req_api_key}',
        'Content-Type': 'application/json'
    }
    proxies = {
        "http":  "",
        "https": "",
    }

    payload = {
        "model": api_model,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.1
    }

    def _sync_request():
        attempt_count = 0
        max_attempts = 5
        while attempt_count < max_attempts:
            try:
                response = requests.post(req_url, headers=headers, json=payload, proxies=proxies)
                if response.status_code == 200:
                    return json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))
                
                attempt_count += 1
                time.sleep(1)
            except Exception as e:
                print(e)
                attempt_count += 1
                time.sleep(5)
        raise Exception("LLM API call failed after max attempts")

    return await asyncio.to_thread(_sync_request)


PROMPTS_EXTRACT_SUB_QUERIES = """You are an Autodesk Inventor API expert. 
Task: Breakdown the following high-level instruction into a sequence of atomic API-related search queries.
Rules:
1. Each query should describe a specific Inventor operation (e.g., 'Create a new part document', 'Insert a sketch').
2. Do NOT return the original user instruction.
3. Return ONLY a valid JSON list of strings.

Example Input: "Create a new part document and save it as a STEP."
Example Output: ["Create a new part document", Save document as STEP"]

User Instruction: {user_instruction}
Output (JSON only):"""

PROMPTS_RERANK = """You are an Autodesk Inventor API selector.
Target Task: "{query}"

Candidates from database:
{candidate_texts}

Instructions:
1. Find the candidate that EXACTLY matches the target task.
2. If a candidate is highly relevant and can perform the task, return its ID.
3. If NONE of the candidates are correct or relevant for this specific task, return -1.

Output Rule: Return ONLY the ID number (e.g., 0, 1, 2...) or -1. No prose."""


class APIRetrievalPipeline:
    def __init__(self, api_library: List[Dict[str, Any]], cache_path: str = "api_index_cache.npy"):
        self.api_library = api_library
        self.api_embeddings = [] 
        self.cache_path = cache_path

    async def build_index(self, batch_size: int = 20, max_workers: int = 3):
        # 1. Loading cache
        if os.path.exists(self.cache_path):
            print(f"Found local cache {self.cache_path}, loading...")
            loaded_data = np.load(self.cache_path)

            if len(loaded_data) == len(self.api_library):
                self.api_embeddings = loaded_data
                self.library_norms = np.linalg.norm(self.api_embeddings, axis=1)

                print(f"Load cache success! Skip API calling.")
                return
            else:
                print("Cache size mismatch with API. Rebuilding...")

        # 2. Preparing data batches
        descriptions = [api["description"] for api in self.api_library]
        total_count = len(descriptions)
        print(f"Initializing vector index for {total_count} data entries...")

        sem = asyncio.Semaphore(max_workers)
        async def _fetch_batch(start_idx):
            async with sem:
                end_idx = min(start_idx + batch_size, total_count)
                batch_texts = descriptions[start_idx:end_idx]
                print(f"Processing batch: {start_idx} to {end_idx}...")
                
                try:
                    vecs = await call_claudeshop_embed(texts=batch_texts)
                    return vecs
                except Exception as e:
                    print(f"Batch {start_idx} Failed: {e}")
                    return None

        tasks = [
            _fetch_batch(i) 
            for i in range(0, total_count, batch_size)
        ]
        results = await asyncio.gather(*tasks)
        
        valid_results = [res for res in results if res is not None]
        if len(valid_results) != len(tasks):
            raise Exception("Some data retrieval failed; please check your network connection or API limits and try again.")

        self.api_embeddings = np.vstack(valid_results)

        self.library_norms = np.linalg.norm(self.api_embeddings, axis=1)

        # Saving to local cache
        np.save(self.cache_path, self.api_embeddings)
        print(f"Index built successfully and saved to {self.cache_path}。")


    async def _extract_sub_queries(self, user_instruction: str) -> List[str]:
        prompt = PROMPTS_EXTRACT_SUB_QUERIES.format(user_instruction=user_instruction)

        response = await call_claudeshop_complete(
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            return json.loads(content)
        except:
            return None

    def _cosine_similarity(self, v1, v2):
        # $$\text{similarity} = \frac{A \cdot B}{\|A\| \|B\|}$$
        dot_val = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0: return 0
        return dot_val / (norm_v1 * norm_v2)

    async def _rerank_candidates(self, query: str, candidates: List[Dict]) -> Dict:
        """Referencing LightRAG's reranking logic, utilize the LLM to select the best-matching JSON."""
        if not candidates: return None
        
        candidate_texts = []
        for i, cand in enumerate(candidates):
            candidate_texts.append(f"ID: {i}\nName: {cand['name']}\nDesc: {cand['description']}")

        prompt = PROMPTS_RERANK.format(query=query, candidate_texts=chr(10).join(candidate_texts))
        response = await call_claudeshop_complete(
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            best_id = int(response.choices[0].message.content.strip())
            if best_id != -1:
                return candidates[best_id]
            else:
                return None
        except:
            return None


    async def _process_single_query(self, query: str, sem: asyncio.Semaphore) -> Dict:
        """Embedding -> Calculating cosine similarity -> LLM reranking"""
        async with sem:
            try:
                # Vector Retrieval (Coarse Reranking)
                query_vec = await call_claudeshop_embed(texts=[query])
                
                vec = query_vec[0] 
                dot_products = np.dot(self.api_embeddings, vec)
                query_norm = np.linalg.norm(vec)
                similarities = dot_products / (self.library_norms * query_norm + 1e-9)

                # Top 10
                top_indices = np.argsort(similarities)[-10:][::-1]
                candidates = [self.api_library[i] for i in top_indices]

                # Rerank (Fine Reranking)
                best_match = await self._rerank_candidates(query, candidates)
                return best_match
                
            except Exception as e:
                print(f"Processing query '{query}' Failed: {e}")
                return None
    
    async def search(self, user_instruction: str, final_results: List[Dict], max_concurrent: int = 5) -> List[Dict]:
        """Main Pipeline"""
        sub_queries = await self._extract_sub_queries(user_instruction)
        if not sub_queries:
            print("No Sub_queries!!!")
            return final_results
            
        print(f'Sub_queries: {sub_queries}')

        sem = asyncio.Semaphore(max_concurrent)
        tasks = [
            self._process_single_query(query, sem) 
            for query in sub_queries
        ]

        parallel_results = await asyncio.gather(*tasks)

        for best_match in parallel_results:
            if best_match and best_match not in final_results:
                final_results.append(best_match)

        return final_results


async def process_single_task(task, pipeline, outer_sem):
    async with outer_sem:
        task_id = task['id']
        save_path = os.path.join(retrieval_results_save_dir, task_id+'.json')
        if os.path.exists(save_path):
            if read_json(save_path):
                return
        
        user_instruction = task['instruction']

        results = await pipeline.search(user_instruction, expected_interfaces, max_concurrent=10)
        write_json(save_path, results)
        return


async def main():
    with open(api_lib_path, 'r') as f:
        my_lib = json.load(f)
    
    pipeline = APIRetrievalPipeline(
        api_library=my_lib,
        cache_path = save_api_index_path
    )
    
    await pipeline.build_index(batch_size=100, max_workers=30)
    print('Total:', len(task_id_list))
    task_list = []
    for id in task_id_list:
        save_path = os.path.join(retrieval_results_save_dir, id+'.json')
        if os.path.exists(save_path):
            continue
        task_config = read_json(os.path.join(task_config_dir, id.split('_')[0]+'.json'))
        new_task_config = {
            "id": id,
            "instruction": task_config['instruction']
        }
        task_list.append(new_task_config)

    print('Remain:', len(task_list))
    outer_sem = asyncio.Semaphore(3)

    tasks = [
        process_single_task(task, pipeline, outer_sem) for task in task_list
    ]
    await asyncio.gather(*tasks)
    print('All Done!')

if __name__ == "__main__":
    # TODO: convert the following to absolute paths
    task_id_list = read_json('benchmarks/comcadbench/3d_model_test_list_100.json')['test']
    task_config_dir = "examples/Text2CAD/examples/test"
    retrieval_results_save_dir = "LightRAG/retrieval_results/3d_model/inventor"
    os.makedirs(retrieval_results_save_dir, exist_ok=True)
    expected_interfaces = read_json('LightRAG/expected_interfaces/3d_model_inventor_expected_api_list.json')
    api_lib_path = 'LightRAG/crawl_api_list/Inventor_related_Objects_api_list.json'
    save_api_index_path = 'inventor_interfaces_api_list.npy'
    
    asyncio.run(main())
