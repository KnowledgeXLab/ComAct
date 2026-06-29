import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import statistics

parser = argparse.ArgumentParser()
parser.add_argument('--test_list_json', type=str, default='Text2CAD_test_list_100.json')
parser.add_argument('--domain', type=str, default='test')
parser.add_argument('--result_dir', type=str, default=None)
args = parser.parse_args()

def draw_cd_distribution(cd_list, save_fig_dir, y_tick_step=10, fig_size=(8, 6)):
    os.makedirs(save_fig_dir, exist_ok=True)

    cd = np.asarray(cd_list, dtype=float)
    total = len(cd)
    if total == 0:
        raise ValueError("cd_list is empty")

    bins = [-np.inf, 0, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100, np.inf]
    labels = [
        "(-∞, 0]",
        "(0, 1e-5]",
        "(1e-5, 1e-4]",
        "(1e-4, 1e-3]",
        "(1e-3, 0.01]",
        "(0.01, 0.1]",
        "(0.1, 1]",
        "(1, 10]",
        "(10, 100]",
        "(100, +∞)"
    ]

    # ====== interval counts (left-open, right-closed) ======
    interval_counts = []
    for i in range(len(bins) - 1):
        left, right = bins[i], bins[i + 1]
        if left == -np.inf:
            cnt = np.sum(cd <= right)
        else:
            cnt = np.sum((cd > left) & (cd <= right))
        interval_counts.append(int(cnt))

    interval_percent = np.array(interval_counts, dtype=float) / total * 100.0
    cum_percent = np.cumsum(interval_percent)

    # y ticks
    y_tick_step = int(y_tick_step)
    if y_tick_step <= 0:
        y_tick_step = 10
    y_ticks = np.arange(0, 100 + 1e-9, y_tick_step)

    # ====== Plot 1: interval distribution (%) ======
    plt.figure(figsize=fig_size)
    plt.bar(labels, interval_percent)
    plt.xlabel("Chamfer Distance Range")
    plt.ylabel("Percentage (%)")
    plt.title("CD Interval Distribution (%)")
    plt.ylim(0, 100)
    plt.yticks(y_ticks)
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, "cd_interval_distribution.png"), dpi=300)
    plt.close()

    # ====== Plot 2: cumulative distribution (%) ======
    plt.figure(figsize=fig_size)
    plt.plot(labels, cum_percent, marker="o")
    plt.xlabel("Chamfer Distance Threshold")
    plt.ylabel("Cumulative Percentage (%)")
    plt.title("CD Cumulative Distribution (%)")
    plt.ylim(0, 100)
    plt.yticks(y_ticks)
    plt.grid(True, which="both", axis="y")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, "cd_cumulative_distribution.png"), dpi=300)
    plt.close()

    # ====== Plot 3: interval distribution (count) ======
    plt.figure(figsize=fig_size)
    bars = plt.bar(labels, interval_counts)
    plt.xlabel("Chamfer Distance Range")
    plt.ylabel("Count")
    plt.title("CD Interval Distribution (Count)")
    plt.xticks(rotation=30)

    for b in bars:
        h = b.get_height()
        plt.text(
            b.get_x() + b.get_width() / 2,
            h,
            f"{int(h)}",
            ha="center",
            va="bottom",
            fontsize=9
        )

    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, "cd_interval_distribution_count.png"), dpi=300)
    plt.close()

    return {
        "interval_count": dict(zip(labels, interval_counts)),
        "interval_percent": dict(zip(labels, interval_percent.tolist())),
        "cumulative_percent": dict(zip(labels, cum_percent.tolist())),
    }


def read_json(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

def write_json(data, save_path):
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=4))

def parse_traj_jsonl(file_path):
    ds = []
    line_list = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_list.append(line)
    
    for i in range(len(line_list)):
        line = line_list[i]
        data = json.loads(line)
        if 'init_timestamp' in data:
            ds = []
        ds.append(data)
    return ds

save_data = {
    'avg_score': 0,
    'avg_cd': 0,
    'avg_steps': 0,
    'done_percent': 0,
    'fail_percent': 0,
    'done_but_invalid_percent': 0,
    'invalid_cd_percent': 0,
    'avg_time': 0,
    'total_time': 0,
    'avg_completion_tokens': 0,
    'total_completion_tokens': 0,
    'avg_prompt_tokens': 0,
    'total_prompt_tokens': 0,
    'scores': [],
    'steps': [],
    'cds': [],
    'time_list': [],
    'completion_tokens_list': [],
    'prompt_tokens_list': []

}

if __name__ == '__main__':
    scores = []
    cds = []
    steps = []
    traj_time_list = []
    completion_tokens_list = []
    prompt_tokens_list = []
    id_list = []

    done_count = 0
    fail_count = 0
    done_but_invalid_count = 0
    invalid_cd_num = 0

    total = 0
    not_success_id_list = []
    test_list = read_json(args.test_list_json)[args.domain]
    for id in test_list:
        traj_path = os.path.join(args.result_dir, id, 'traj.jsonl')
        if not os.path.exists(traj_path):
            print(traj_path)
            continue
        try:
            traj_data = parse_traj_jsonl(traj_path)
        except Exception as e:
            print(e)
            continue

        eval_data = traj_data[-1]
        if 'result' not in eval_data:
            print(f'No Valid eval data: {id}')
            continue

        score = eval_data['result']['Score']
        if score <= 0 :
            not_success_id_list.append(id)
        cd = eval_data['result']['CD']

        steps_data = traj_data[1:-1]
        if len(steps_data) <= 0:
            print(f'No Valid Steps data: {id}')
            continue
        if steps_data[-1]['action']['done']:
            done_count += 1
            if cd == -1:
                done_but_invalid_count += 1
        if steps_data[-1]['action']['fail']:
            fail_count += 1

        id_list.append(id)

        total += 1
        scores.append(score)
        cds.append(cd)

        steps_total = eval_data['Steps']['steps_total']
        steps.append(steps_total)

        if (not steps_data[-1]['action']['done']) and steps_total < 6:
            print(id,steps_total)

        traj_time_list.append(eval_data['Time']['traj_elapsed_time'])
        completion_tokens_list.append(eval_data['Context_length']['completion_tokens_total'])
        prompt_tokens_list.append(eval_data['Context_length']['prompt_tokens_total'])

        if cd == -1:
            invalid_cd_num += 1

            cds[-1] = 'NA'

        valid_cds = []
        if cd != -1:
            valid_cds.append(cd)

    id_cd_list = []
    for idx in range(len(id_list)):
        id_cd_list.append(f'{id_list[idx]}: {cds[idx]}')

    processed_cds = []
    for cd_item in cds:
        if cd_item == 'NA':
            continue
        processed_cds.append(cd_item)

    save_data = {
        'total': total,
        'avg_score': sum(scores)/len(scores),
        'invalid_cd_percent': invalid_cd_num/total,
        'avg_cd': sum(processed_cds)/len(processed_cds) if len(processed_cds) > 0 else -1,
        'median_cd': statistics.median(processed_cds) if len(processed_cds) > 0 else -1,
        'avg_steps': sum(steps)/len(steps),
        'done_percent': done_count/total,
        'fail_percent': fail_count/total,
        'done_but_invalid_percent': done_but_invalid_count/total,
        'avg_time': sum(traj_time_list)/len(traj_time_list),
        'avg_completion_tokens': sum(completion_tokens_list)/len(completion_tokens_list),
        'avg_prompt_tokens': sum(prompt_tokens_list)/len(prompt_tokens_list),
        'id_cd_list': id_cd_list,
        'id_list': id_list,
        'scores': scores,
        'steps': steps,
        'cds': cds,
        'time_list': traj_time_list,
        'completion_tokens_list': completion_tokens_list,
        'prompt_tokens_list': prompt_tokens_list

    }

    print('======= Results =======')
    print('Total: {}\nAvg Score: {}; Valid Rate: {}\nAvg CD: {}; Median CD: {}'.format(save_data['total'], save_data['avg_score'], 1-save_data['invalid_cd_percent'], save_data['avg_cd'], save_data['median_cd']))
    print('========================')
    with open(os.path.join(args.result_dir,'result_metadata.json'),'w',encoding='utf-8') as f:
        f.write(json.dumps(save_data, indent=4))

    if len(processed_cds) > 0:
        draw_cd_distribution(processed_cds,args.result_dir)
