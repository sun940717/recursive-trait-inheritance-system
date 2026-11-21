#!/usr/bin/env python3
r"""RTIS v1 X3: frozen generator, descriptive multigeneration experiment.

PowerShell:
  cd D:\ai-research-lab\RTIS\current_2026-11\experiments
  D:\rtis_env\Scripts\python.exe x3_generations_v1.py --trial
  D:\rtis_env\Scripts\python.exe x3_generations_v1.py --workers 6

Trial: population seed 1, 3 generations, results/x3_trial/ (not formal data).
Formal: seeds 1-20, 10 generations, results/. Requires successful matching trial.
Each population has 30 individuals, initially five of each of six forms.
No mutation, selection, retries, replacement, or genome repairs. G5 is the mean
of child-specific retention ratios relative to the two immediate parents.
Every exception cancels X3. Incomplete generations have blank mean metrics;
their pass rate is explicitly a partial count divided by 30, not a result.
Existing runs are never overwritten or resumed by regeneration.
--child-timeout defaults to 600 seconds: an operational watchdog, not a metric.
On timeout/worker death, the last durable 'started' event identifies the child.
An interrupted/failed trial cannot authorize a formal run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
import traceback

# Spawn inherits these limits. Avoid six workers each creating many BLAS threads.
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_key] = '1'
os.environ['MPLBACKEND'] = 'Agg'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
STEM = 'x3_generations_v1'
FROZEN = 'bb54458008ff10be'
FIELDS = ['population', 'generation', 'pass_rate', 'mean_parts', 'g5',
          'errors', 'seconds', 'completed_children', 'status']


def dump(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def rng(population, generation, child, purpose):
    return np.random.default_rng(np.random.SeedSequence(
        [20261116, 900 + population, generation, child, purpose]))


def append_event(handle, event):
    handle.write(json.dumps(event, ensure_ascii=False, default=float) + '\n')
    handle.flush()
    os.fsync(handle.fileno())


def population_worker(seed, generations, folder):
    import run_v1 as R
    folder = Path(folder)
    # Each worker writes its own durable events, never a shared CSV.
    with (folder / f'population_{seed:02d}.jsonl').open('x', encoding='utf-8') as log:
        forms = R.lab.all_forms(ontology_tags=True)
        previous = [forms[name] for name in R.FORMS for _ in range(5)]
        cfg = R.sk.SkeletonInheritanceConfig(micro_budget=0)
        for generation in range(1, generations + 1):
            current = []
            for individual in range(1, 31):
                t0 = time.perf_counter()
                event = dict(population=seed, generation=generation, individual=individual)
                append_event(log, dict(event, status='started'))
                stage = 'select_parents'
                try:
                    choose = rng(seed, generation, individual, 0)
                    a, b = map(int, choose.choice(30, 2, replace=False))
                    direction = int(choose.integers(0, 2))
                    if direction:
                        a, b = b, a
                    event.update(parent_a_index=a, parent_b_index=b, direction=direction)
                    stage = 'with_ancestry'
                    ga = R.sk.with_ancestry(previous[a], 1.0)
                    gb = R.sk.with_ancestry(previous[b], 0.0)
                    stage = 'soft_match'
                    pairs, decisions = R.soft.soft_match(ga, gb, rng(seed, generation, individual, 1), 'soft')
                    stage = 'fuse'
                    child, ancestry = R.lab.fuse(ga, gb, rng(seed, generation, individual, 2),
                                                cfg, R.lab.ADOPTED, pairs=pairs, exclude=set(), attr=None)
                    stage = 'build_sdf_creature'
                    mesh, face_piece, _ = R.sk.build_sdf_creature(child, 0.03)
                    stage = 'measure_child'
                    fields, _ = R.M.measure_child(child, ancestry, ga, gb, mesh, face_piece, 0.03)
                    retention = fields['sources_kept'] / fields['sources_total']
                    event.update(status='ok', pass_geo=int(fields['pass_geo']), parts=fields['parts'],
                                 g5=retention, sources_kept=fields['sources_kept'],
                                 sources_total=fields['sources_total'], k_matched=len(pairs)-1)
                    # Keep every child, including geometrically unqualified ones.
                    current.append(child)
                    del mesh, face_piece
                except Exception as exc:
                    event.update(status='error', pass_geo=0, stage=stage,
                                 error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
                event['seconds'] = time.perf_counter() - t0
                append_event(log, event)
                if event['status'] == 'error':
                    return
            previous = current


def events_in(folder):
    events = []
    for path in sorted(folder.glob('population_*.jsonl')):
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # A crash may leave an incomplete final line; the prior start survives.
                continue
    return events


def summarize(events):
    groups = {}
    for e in events:
        if e['status'] in ('ok', 'error'):
            groups.setdefault((e['population'], e['generation']), []).append(e)
    rows = []
    for (p, g), group in sorted(groups.items()):
        ids = [e['individual'] for e in group]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f'Duplicate child record: {p}, {g}')
        complete = len(group) == 30 and all(e['status'] == 'ok' for e in group)
        rows.append(dict(population=p, generation=g,
                         pass_rate=sum(e['pass_geo'] for e in group)/30,
                         mean_parts=float(np.mean([e['parts'] for e in group])) if complete else '',
                         g5=float(np.mean([e['g5'] for e in group])) if complete else '',
                         errors=sum(e['status'] == 'error' for e in group),
                         seconds=sum(e['seconds'] for e in group), completed_children=len(group),
                         status='complete' if complete else 'incomplete'))
    return rows


def write_outputs(out, folder, manifest):
    import matplotlib.pyplot as plt
    events = events_in(folder)
    rows = summarize(events)
    with (out / (STEM + '.csv')).open('w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    successful = manifest['status'] == 'complete'
    lines = ['# RTIS v1 X3 多代（只描述）', '',
             '模式：' + ('試跑（不納入正式結果）' if manifest['trial'] else '正式'),
             '', '狀態：' + manifest['status'], '',
             'X3 已完成。' if successful else 'X3 沒有做完；不以部分資料冒充正式 20 族群結果。',
             '', '不做檢定。G5 是各子代相對於直接雙親的保留比例之平均，不是對初始六形體的累積保留。',
             '合格率分母固定 30；錯誤算不合格。不完整代的其他均值留白，不進中位數與範圍。',
             'seconds 是該族群該代已嘗試子代的耗時總和（非 X4 生成效能測試）。', '',
             '| 代 | 完整族群數 | 合格率中位數 %（最小–最大） | 平均部位數中位數（最小–最大） | G5 中位數 %（最小–最大） |',
             '|---|---:|---|---|---|']
    complete = [r for r in rows if r['status'] == 'complete']
    for g in range(1, manifest['generations']+1):
        group = [r for r in complete if r['generation'] == g]
        stats = []
        for metric, scale in [('pass_rate',100), ('mean_parts',1), ('g5',100)]:
            x = [r[metric]*scale for r in group]
            stats.append(f'{np.median(x):.3f}（{min(x):.3f}–{max(x):.3f}）' if x else '—')
        lines.append(f'| {g} | {len(group)} | ' + ' | '.join(stats) + ' |')
    errors = [e for e in events if e['status'] == 'error']
    if manifest.get('reason'):
        lines += ['', '停止原因：' + manifest['reason']]
    for e in errors:
        lines += ['', f"族群 {e['population']}，第 {e['generation']} 代，個體 {e['individual']}，步驟 {e.get('stage', 'unknown')}：", '', '```text', e.get('traceback', e['error']), '```']
    fig, axes = plt.subplots(3, 1, figsize=(9, 10), sharex=True)
    for ax, metric, scale, label in zip(axes, ['pass_rate','mean_parts','g5'],[100,1,100],
                                       ['Geometry pass (%)','Mean parts','G5 retention (%)']):
        for p in manifest['seeds']:
            group = [r for r in complete if r['population'] == p]
            ax.plot([r['generation'] for r in group], [r[metric]*scale for r in group],
                    color='#597ca1', alpha=.25, linewidth=1)
        xs = sorted({r['generation'] for r in complete})
        ax.plot(xs, [np.median([r[metric]*scale for r in complete if r['generation']==g]) for g in xs],
                color='#16395e', linewidth=2.8, marker='o', label='Median of completed populations')
        ax.set_ylabel(label)
        ax.grid(alpha=.2)
        if metric != 'mean_parts':
            ax.set_ylim(0,100)
    axes[-1].set_xlabel('Generation')
    axes[-1].set_xticks(range(1,manifest['generations']+1))
    axes[0].legend()
    fig.suptitle('RTIS X3: ' + ('TRIAL' if manifest['trial'] else 'FORMAL') + ' / ' + manifest['status'])
    fig.tight_layout()
    fig.savefig(out / (STEM + '.png'), dpi=160)
    plt.close(fig)
    lines += ['', f'![X3 descriptive trajectories]({STEM}.png)', '',
              '淡線為各族群、粗線為完整族群的中位數；取消時僅為部分試跑診斷。', '',
              '環境、亂數鍵、程式雜湊及停止原因見 manifest；逐子代紀錄見 '+folder.name+'。']
    (out / (STEM + '.md')).write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--trial', action='store_true')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--child-timeout', type=float, default=600)
    args = ap.parse_args(argv)
    if args.workers < 1 or args.child_timeout <= 0:
        ap.error('workers and child-timeout must be positive')
    import run_v1 as R
    hashes = R.file_hashes()
    if R.combined_hash(hashes) != FROZEN:
        ap.error('Frozen code hash mismatch; no experiment started')
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out = HERE/'results'/('x3_trial' if args.trial else '')
    out.mkdir(parents=True, exist_ok=True)
    man_path = out/(STEM+'_manifest.json')
    folder = out/(STEM+'_children')
    if man_path.exists() or folder.exists() or (out/(STEM+'.csv')).exists():
        ap.error('Existing X3 run preserved; refusing to overwrite or repeat children')
    if not args.trial:
        trial_path = HERE/'results'/'x3_trial'/(STEM+'_manifest.json')
        trial = json.loads(trial_path.read_text(encoding='utf-8')) if trial_path.exists() else {}
        if not (trial.get('status') == 'complete' and trial.get('code_hash') == FROZEN
                and trial.get('script_sha256') == script_hash):
            ap.error('A successful --trial with this exact script and frozen code is required')
    import scipy, skimage
    manifest = dict(trial=args.trial, status='running', seeds=[1] if args.trial else list(range(1,21)),
                    generations=3 if args.trial else 10, size=30, workers=args.workers,
                    code_hash=FROZEN, file_sha256=hashes, script_sha256=script_hash,
                    python=platform.python_version(), platform=platform.platform(), numpy=np.__version__,
                    scipy=scipy.__version__, scikit_image=skimage.__version__, voxel=.03,
                    child_timeout_seconds=args.child_timeout, individual_numbers='1-30',
                    rng='SeedSequence([20261116,900+population_seed,generation,individual,purpose]); 0 parents/direction, 1 matching, 2 inheritance')
    folder.mkdir()
    dump(man_path, manifest)
    ctx = mp.get_context('spawn')
    pending = list(manifest['seeds'])
    running = {}
    reason = None
    start = time.perf_counter()
    try:
        while pending or running:
            while pending and len(running) < args.workers:
                seed = pending.pop(0)
                proc = ctx.Process(target=population_worker, args=(seed,manifest['generations'],str(folder)))
                proc.start()
                running[seed] = (proc,time.time())
            events = events_in(folder)
            errors = [e for e in events if e['status']=='error']
            if errors:
                e = errors[0]
                reason = f"族群 {e['population']} 代 {e['generation']} 個體 {e['individual']}：{e['error']}"
                break
            for seed,(proc,launched) in list(running.items()):
                path = folder/f'population_{seed:02d}.jsonl'
                last = path.stat().st_mtime if path.exists() else launched
                if not proc.is_alive():
                    proc.join()
                    done = [e for e in events_in(folder) if e['population']==seed and e['status']=='ok']
                    if proc.exitcode != 0 or len(done) != manifest['generations']*30:
                        reason = f'WorkerExit: population={seed}, exitcode={proc.exitcode}, completed={len(done)}'
                        break
                    print(f'Population {seed} complete ({len(done)} children)', flush=True)
                    del running[seed]
                elif time.time()-last > args.child_timeout:
                    reason = f'WatchdogTimeout: population={seed}, no child completion for {args.child_timeout} seconds'
                    break
            if reason:
                break
            time.sleep(.5)
    except BaseException as exc:
        reason = f'{type(exc).__name__}: {exc}'
    finally:
        for proc,_ in running.values():
            if proc.is_alive():
                proc.terminate()
            proc.join(timeout=10)
            if proc.is_alive():
                proc.kill()
                proc.join()
        # Record any started child interrupted by cancellation, timeout or worker death.
        events = events_in(folder)
        for seed in manifest['seeds']:
            own = [e for e in events if e['population']==seed]
            if own and own[-1]['status']=='started':
                e = dict(own[-1], status='error', pass_geo=0, seconds=0,
                         stage='worker interrupted; see last completed child',
                         error=reason or 'Worker terminated unexpectedly')
                with (folder/f'population_{seed:02d}.jsonl').open('a',encoding='utf-8') as fh:
                    fh.write('\n')  # separate a possible torn final JSON line
                    append_event(fh,e)
        if R.combined_hash(R.file_hashes()) != FROZEN:
            reason = 'Frozen code changed during execution; results invalid'
        manifest.update(status='cancelled' if reason else 'complete', reason=reason,
                        wall_seconds=time.perf_counter()-start)
        dump(man_path,manifest)
        rows = write_outputs(out,folder,manifest)
        print(f"{manifest['status']}: {len(rows)} population-generation rows -> {out}",flush=True)
    return 1 if reason else 0


if __name__ == '__main__':
    mp.freeze_support()
    raise SystemExit(main())
