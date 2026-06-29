import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import statistics

parser = argparse.ArgumentParser()
parser.add_argument('--test_list_json', type=str, default=None)
parser.add_argument('--domain', type=str, default='test')
parser.add_argument('--result_dir', type=str, default=None)
parser.add_argument('--task_type', type=str, default=None,
                    choices=[
                        '3d_model+drawing',
                        '3d_model+mass_property',
                        'assembly+interference_detection',
                        '3d_model+modify',
                    ])
args = parser.parse_args()


def read_json(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

def write_json(data, save_path):
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=4))

def parse_traj_jsonl(file_path):
    """Parse traj.jsonl, restart ds if init_timestamp found (supports re-runs)."""
    ds = []
    line_list = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_list.append(line)
    for line in line_list:
        data = json.loads(line)
        if 'init_timestamp' in data:
            ds = []
        ds.append(data)
    return ds


def safe_avg(lst):
    return sum(lst) / len(lst) if lst else -1


def safe_median(lst):
    return statistics.median(lst) if lst else -1


def draw_cd_distribution(cd_list, save_fig_dir, suffix='', y_tick_step=10, fig_size=(8, 6)):
    os.makedirs(save_fig_dir, exist_ok=True)

    cd = np.asarray(cd_list, dtype=float)
    total = len(cd)
    if total == 0:
        raise ValueError("cd_list is empty")

    bins = [-np.inf, 0, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100, np.inf]
    labels = [
        "(-∞, 0]", "(0, 1e-5]", "(1e-5, 1e-4]", "(1e-4, 1e-3]",
        "(1e-3, 0.01]", "(0.01, 0.1]", "(0.1, 1]",
        "(1, 10]", "(10, 100]", "(100, +∞)"
    ]

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

    y_tick_step = max(int(y_tick_step), 1)
    y_ticks = np.arange(0, 100 + 1e-9, y_tick_step)

    title_suffix = suffix.replace('_', ' ').strip()

    # Plot 1: interval %
    plt.figure(figsize=fig_size)
    plt.bar(labels, interval_percent)
    plt.xlabel("Chamfer Distance Range")
    plt.ylabel("Percentage (%)")
    plt.title(f"CD Interval Distribution (%) {title_suffix}")
    plt.ylim(0, 100)
    plt.yticks(y_ticks)
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, f"cd_interval_distribution{suffix}.png"), dpi=300)
    plt.close()

    # Plot 2: cumulative %
    plt.figure(figsize=fig_size)
    plt.plot(labels, cum_percent, marker="o")
    plt.xlabel("Chamfer Distance Threshold")
    plt.ylabel("Cumulative Percentage (%)")
    plt.title(f"CD Cumulative Distribution (%) {title_suffix}")
    plt.ylim(0, 100)
    plt.yticks(y_ticks)
    plt.grid(True, which="both", axis="y")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, f"cd_cumulative_distribution{suffix}.png"), dpi=300)
    plt.close()

    # Plot 3: interval count
    plt.figure(figsize=fig_size)
    bars = plt.bar(labels, interval_counts)
    plt.xlabel("Chamfer Distance Range")
    plt.ylabel("Count")
    plt.title(f"CD Interval Distribution (Count) {title_suffix}")
    plt.xticks(rotation=30)
    for b in bars:
        h = b.get_height()
        plt.text(b.get_x() + b.get_width() / 2, h, f"{int(h)}",
                 ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, f"cd_interval_distribution_count{suffix}.png"), dpi=300)
    plt.close()

    return {
        "interval_count":     dict(zip(labels, interval_counts)),
        "interval_percent":   dict(zip(labels, interval_percent.tolist())),
        "cumulative_percent": dict(zip(labels, cum_percent.tolist())),
    }

def draw_score_combination(combo_counts, total, save_fig_dir, task_type, fig_size=(8, 5)):
    os.makedirs(save_fig_dir, exist_ok=True)

    task_labels = {
        '3d_model+drawing':                ('3D Model', 'Drawing'),
        '3d_model+mass_property':          ('3D Model', 'Mass Property'),
        'assembly+interference_detection': ('Assembly', 'Interference Det.'),
        '3d_model+modify':                 ('3D Model', 'Modify'),
    }
    t1, t2 = task_labels.get(task_type, ('Task 1', 'Task 2'))

    labels   = ['Both\nSuccess', f'Only {t1}\nSuccess', f'Only {t2}\nSuccess', 'Both\nFail']
    keys     = ['both_success', 'only_first', 'only_second', 'both_fail']
    counts   = [combo_counts[k] for k in keys]
    percents = [c / total * 100 for c in counts]
    colors   = ['#4CAF50', '#FF9800', '#2196F3', '#F44336']

    plt.figure(figsize=fig_size)
    bars = plt.bar(labels, percents, color=colors)
    for b, cnt in zip(bars, counts):
        h = b.get_height()
        plt.text(b.get_x() + b.get_width() / 2, h + 0.5,
                 f"{cnt}\n({h:.1f}%)", ha="center", va="bottom", fontsize=9)
    plt.ylabel("Percentage (%)")
    plt.title(f"Score Combination Distribution — {task_type}")
    plt.ylim(0, 110)
    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, "score_combination.png"), dpi=300)
    plt.close()

def draw_code_valid_combination(combo_counts, total, save_fig_dir, task_type, fig_size=(8, 5)):
    os.makedirs(save_fig_dir, exist_ok=True)

    labels   = ['Both Valid', 'Only 1st Valid', 'Only 2nd Valid', 'Both Invalid']
    keys     = ['both_valid', 'only_first_valid', 'only_second_valid', 'both_invalid']
    counts   = [combo_counts[k] for k in keys]
    percents = [c / total * 100 for c in counts]
    colors   = ['#4CAF50', '#FF9800', '#2196F3', '#F44336']

    plt.figure(figsize=fig_size)
    bars = plt.bar(labels, percents, color=colors)
    for b, cnt in zip(bars, counts):
        h = b.get_height()
        plt.text(b.get_x() + b.get_width() / 2, h + 0.5,
                 f"{cnt}\n({h:.1f}%)", ha="center", va="bottom", fontsize=9)
    plt.ylabel("Percentage (%)")
    plt.title(f"Code Valid Combination Distribution — {task_type}")
    plt.ylim(0, 110)
    plt.tight_layout()
    plt.savefig(os.path.join(save_fig_dir, "code_valid_combination.png"), dpi=300)
    plt.close()

if __name__ == '__main__':
    task_type = args.task_type

    TASK_KEY_MAP = {
        '3d_model+drawing': {
            'dual_cd':    False,
            'score1_key': 'Score_3d_model',
            'score2_key': 'Score_drawing',
            'cd_key':     'CD',
            'valid2_key': 'code_valid_drawing',
        },
        '3d_model+mass_property': {
            'dual_cd':    False,
            'score1_key': 'Score_3d_model',
            'score2_key': 'Score_mass_property',
            'cd_key':     'CD',
            'valid2_key': 'code_valid_mass_property',
        },
        'assembly+interference_detection': {
            'dual_cd':    False,
            'score1_key': 'Score_assembly',
            'score2_key': 'Score_interference_detection',
            'cd_key':     'CD',
            'valid2_key': 'code_valid_interference_detection',
        },
        '3d_model+modify': {
            'dual_cd':    True,
            'score1_key': 'Score_3d_model',
            'score2_key': 'Score_modify',
            'cd1_key':    'CD_3d_model',
            'cd2_key':    'CD_modify',
        },
    }
    km = TASK_KEY_MAP[task_type]
    is_dual_cd = km['dual_cd']

    # accumulators 
    scores_1, scores_2, scores_joint = [], [], []

    # single CD task
    cds           = []
    invalid_cd_num = 0

    # dual CD task（3d_model+modify）
    cds_1, cds_2               = [], []
    invalid_cd1_num, invalid_cd2_num = 0, 0

    steps_list             = []
    time_list              = []
    completion_tokens_list = []
    prompt_tokens_list     = []
    id_list                = []

    score_combo      = {'both_success': 0, 'only_first': 0, 'only_second': 0, 'both_fail': 0}
    code_valid_combo = {'both_valid': 0, 'only_first_valid': 0,
                        'only_second_valid': 0, 'both_invalid': 0}

    done_count = 0
    fail_count = 0
    total      = 0

    # iterate test list
    test_list = read_json(args.test_list_json)[args.domain]

    for uid in test_list:
        traj_path = os.path.join(args.result_dir, uid, 'traj.jsonl')
        if not os.path.exists(traj_path):
            print(f'[MISSING] {traj_path}')
            continue
        try:
            traj_data = parse_traj_jsonl(traj_path)
        except Exception as e:
            print(f'[PARSE ERROR] {uid}: {e}')
            continue

        eval_data = traj_data[-1]
        if 'result' not in eval_data:
            print(f'[NO RESULT] {uid}')
            continue

        res = eval_data['result']

        # scores
        s1 = res.get(km['score1_key'], 0)
        s2 = res.get(km['score2_key'], 0)
        s_joint_scalar = 1.0 if (s1 > 0 and s2 > 0) else 0.0

        scores_1.append(s1)
        scores_2.append(s2)
        scores_joint.append(s_joint_scalar)

        if s1 > 0 and s2 > 0:
            score_combo['both_success'] += 1
        elif s1 > 0 and s2 <= 0:
            score_combo['only_first'] += 1
        elif s1 <= 0 and s2 > 0:
            score_combo['only_second'] += 1
        else:
            score_combo['both_fail'] += 1

        # CD & code-valid
        if not is_dual_cd:
            # single CD task
            cd = res.get(km['cd_key'], -1)
            task1_valid = (cd != -1)
            if cd == -1:
                invalid_cd_num += 1
                cds.append('NA')
            else:
                cds.append(cd)
            task2_valid = bool(res.get(km['valid2_key'], False))

        else:
            # 3d_model+modify
            cd1 = res.get(km['cd1_key'], -1)
            cd2 = res.get(km['cd2_key'], -1)
            task1_valid = (cd1 != -1)
            task2_valid = (cd2 != -1)

            if cd1 == -1:
                invalid_cd1_num += 1
                cds_1.append('NA')
            else:
                cds_1.append(cd1)

            if cd2 == -1:
                invalid_cd2_num += 1
                cds_2.append('NA')
            else:
                cds_2.append(cd2)

        # code-valid combination
        if task1_valid and task2_valid:
            code_valid_combo['both_valid'] += 1
        elif task1_valid and not task2_valid:
            code_valid_combo['only_first_valid'] += 1
        elif not task1_valid and task2_valid:
            code_valid_combo['only_second_valid'] += 1
        else:
            code_valid_combo['both_invalid'] += 1

        # steps / done / fail
        steps_data = traj_data[1:-1]
        if len(steps_data) <= 0:
            print(f'[NO STEPS] {uid}')
            continue

        if steps_data[-1]['action']['done']:
            done_count += 1
        if steps_data[-1]['action']['fail']:
            fail_count += 1

        steps_total = eval_data['Steps']['steps_total']
        steps_list.append(steps_total)

        # time / tokens
        time_list.append(eval_data['Time']['traj_elapsed_time'])
        completion_tokens_list.append(eval_data['Context_length']['completion_tokens_total'])
        prompt_tokens_list.append(eval_data['Context_length']['prompt_tokens_total'])

        id_list.append(uid)
        total += 1

    # derived stats
    if not is_dual_cd:
        processed_cds = [c for c in cds if c != 'NA']
    else:
        processed_cds_1 = [c for c in cds_1 if c != 'NA']
        processed_cds_2 = [c for c in cds_2 if c != 'NA']

    # build save_data
    save_data = {
        'task_type': task_type,
        'total':     total,

        'joint_success_rate':  safe_avg(scores_joint),
        'score1_success_rate': sum(1 for s in scores_1 if s > 0) / total if total else 0,
        'score2_success_rate': sum(1 for s in scores_2 if s > 0) / total if total else 0,
        'avg_score1':          safe_avg(scores_1),
        'avg_score2':          safe_avg(scores_2),

        'score_combination': {
            k: {'count': v, 'percent': v / total if total else 0}
            for k, v in score_combo.items()
        },

        'code_valid_combination': {
            k: {'count': v, 'percent': v / total if total else 0}
            for k, v in code_valid_combo.items()
        },

        'avg_steps':    safe_avg(steps_list),
        'done_percent': done_count / total if total else 0,
        'fail_percent': fail_count / total if total else 0,

        'avg_time':                safe_avg(time_list),
        'avg_completion_tokens':   safe_avg(completion_tokens_list),
        'avg_prompt_tokens':       safe_avg(prompt_tokens_list),
        'total_completion_tokens': sum(completion_tokens_list),
        'total_prompt_tokens':     sum(prompt_tokens_list),

        'id_list':                 id_list,
        'scores_1':                scores_1,
        'scores_2':                scores_2,
        'scores_joint':            scores_joint,
        'steps':                   steps_list,
        'time_list':               time_list,
        'completion_tokens_list':  completion_tokens_list,
        'prompt_tokens_list':      prompt_tokens_list,
    }

    if not is_dual_cd:
        save_data.update({
            'invalid_cd_percent': invalid_cd_num / total if total else 0,
            'valid_cd_percent':   1 - (invalid_cd_num / total if total else 0),
            'avg_cd':             safe_avg(processed_cds),
            'median_cd':          safe_median(processed_cds),
            'cds':                cds,
        })
    else:
        save_data.update({
            'invalid_cd1_percent': invalid_cd1_num / total if total else 0,
            'valid_cd1_percent':   1 - (invalid_cd1_num / total if total else 0),
            'avg_cd1':             safe_avg(processed_cds_1),
            'median_cd1':          safe_median(processed_cds_1),
            'cds_3d_model':        cds_1,
            'invalid_cd2_percent': invalid_cd2_num / total if total else 0,
            'valid_cd2_percent':   1 - (invalid_cd2_num / total if total else 0),
            'avg_cd2':             safe_avg(processed_cds_2),
            'median_cd2':          safe_median(processed_cds_2),
            'cds_modify':          cds_2,
        })

    print('======= Multi-Task Results =======')
    print(f'Task Type : {task_type}')
    print(f'Total     : {total}')
    print('Success Rate(both): {}; Valid Rate(both): {}'.format(
        save_data['joint_success_rate'],
        save_data['code_valid_combination']['both_valid']['percent']))
    print()
    print('[Score]')
    print(f'  Joint Success Rate  : {save_data["joint_success_rate"]:.4f}')
    print(f'  Task-1 Success Rate : {save_data["score1_success_rate"]:.4f}')
    print(f'  Task-2 Success Rate : {save_data["score2_success_rate"]:.4f}')
    for k, v in save_data['score_combination'].items():
        print(f'  {k:20s}: {v["count"]:4d}  ({v["percent"]*100:.1f}%)')
    print()
    print('[Code Valid Combinations]')
    for k, v in save_data['code_valid_combination'].items():
        print(f'  {k:25s}: {v["count"]:4d}  ({v["percent"]*100:.1f}%)')
    print()
    if not is_dual_cd:
        print('[CD]')
        print(f'  Valid Rate : {save_data["valid_cd_percent"]:.4f}')
        print(f'  Avg CD     : {save_data["avg_cd"]}')
        print(f'  Median CD  : {save_data["median_cd"]}')
    else:
        print('[CD — 3D Model]')
        print(f'  Valid Rate : {save_data["valid_cd1_percent"]:.4f}')
        print(f'  Avg CD     : {save_data["avg_cd1"]}')
        print(f'  Median CD  : {save_data["median_cd1"]}')
        print('[CD — Modify]')
        print(f'  Valid Rate : {save_data["valid_cd2_percent"]:.4f}')
        print(f'  Avg CD     : {save_data["avg_cd2"]}')
        print(f'  Median CD  : {save_data["median_cd2"]}')
    print('==================================')

    # save JSON
    out_json = os.path.join(args.result_dir, 'result_metadata_multi_tasks.json')
    write_json(save_data, out_json)
    print(f'\nSaved: {out_json}')

    # plots
    draw_score_combination(score_combo, total, args.result_dir, task_type)
    draw_code_valid_combination(code_valid_combo, total, args.result_dir, task_type)

    if not is_dual_cd:
        if processed_cds:
            draw_cd_distribution(processed_cds, args.result_dir)
    else:
        if processed_cds_1:
            draw_cd_distribution(processed_cds_1, args.result_dir, suffix='_3d_model')
        if processed_cds_2:
            draw_cd_distribution(processed_cds_2, args.result_dir, suffix='_modify')