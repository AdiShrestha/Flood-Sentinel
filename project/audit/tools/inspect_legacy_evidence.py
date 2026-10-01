"""Independent inspection of legacy artifacts, not a research performance run."""
import argparse
import json
from pathlib import Path
import platform
import sys
import importlib.metadata

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
import torch


def require_same_dates(left, right):
    """Forensic formula comparisons require exact one-to-one date alignment."""
    a=pd.to_datetime(left['date'],utc=True); b=pd.to_datetime(right['date'],utc=True)
    if a.isna().any() or b.isna().any() or a.duplicated().any() or b.duplicated().any():
        raise ValueError('Invalid/duplicate forensic dates; positional matching would be misleading.')
    if not a.is_monotonic_increasing or not b.is_monotonic_increasing or not np.array_equal(a.to_numpy(),b.to_numpy()):
        raise ValueError('Forensic date vectors differ; formula equality is not established.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--legacy', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); c = a.legacy / 'project/chunks'
    panel = json.loads((c / 'chunk02/full_panel.json').read_text())['gauges']
    nwm_checks, snow_checks, quality = [], [], []
    for g in panel:
        gid = g['site_no']
        obs = pd.read_parquet(c / f'chunk02/data/usgs/{gid}/daily_streamflow.parquet')
        nwm = pd.read_parquet(c / f'chunk02/data/nwm_retro/{gid}/nwm_retro_daily.parquet')
        require_same_dates(obs,nwm)
        q = obs['discharge_cfs'].to_numpy(dtype=float) * 0.0283168
        expected = np.maximum(0, q) if g.get('in_pilot_panel') else np.maximum(.01, q * .95 + .05 * np.sin(np.linspace(0, 100, len(q))))
        x = nwm['nwm_discharge_cms'].to_numpy(dtype=float)
        good = np.isfinite(x) & np.isfinite(expected)
        error = np.abs(x[good] - np.round(expected[good], 4))
        nwm_checks.append({'site_no': gid, 'pilot': bool(g.get('in_pilot_panel')),
                           'finite_pairs': int(good.sum()), 'max_error_to_legacy_usgs_formula': float(error.max()) if len(error) else None,
                           'fraction_exact_to_rounded_formula': float(np.mean(error == 0)) if len(error) else None})
        met = pd.read_parquet(c / f'chunk02/data/gridmet/{gid}/gridmet_daily.parquet')
        quality.append({'site_no': gid, 'discharge_missing_fraction': float(obs['discharge_cfs'].isna().mean()),
                        'stage_missing_fraction': float(obs['gage_height_ft'].isna().mean()),
                        'tmin_min': float(met['tmin_c'].min()), 'tmax_max': float(met['tmax_c'].max())})
        if not g.get('in_pilot_panel') and g.get('snow_influenced'):
            met = met[(met['date'] >= '2003-10-01') & (met['date'] <= '2023-12-31')]
            state, generated = 0., []
            for row in met.itertuples():
                pr = row.precipitation_mm if np.isfinite(row.precipitation_mm) else 0.
                lo = row.tmin_c if np.isfinite(row.tmin_c) else 0.
                hi = row.tmax_c if np.isfinite(row.tmax_c) else 0.
                temp = (lo + hi) / 2
                state = state + pr if temp <= 0 else max(0., state - 2.5 * temp)
                generated.append(round(state, 2))
            snow_table = pd.read_parquet(c / f'chunk02/data/snodas/{gid}/snodas_daily.parquet')
            require_same_dates(met,snow_table)
            swe = snow_table['swe_mm'].to_numpy()
            snow_checks.append({'site_no': gid, 'rows': len(swe), 'max_error_to_degree_day_formula': float(np.max(np.abs(swe - generated)))})
    ev = pd.read_parquet(c / 'chunk07/data/evaluation_event_matrix.parquet')
    test = ev[ev['split'] == 'test']
    windows = pd.read_parquet(c / 'chunk07/data/evaluation_window_matrix.parquet')
    gaps = pd.to_datetime(windows['end_date']).groupby(windows['gauge_id']).diff().dt.total_seconds().dropna() / 86400
    metrics = {}
    for col in ['score_a_cal_iqr_max7d', 'score_b_cal_iqr_max7d', 'score_c_cal_iqr_max7d',
                'score_nwm_cal_iqr_max7d', 'score_persist_cal_iqr_max7d', 'score_ea_lstm_prob']:
        metrics[col] = {'auroc': float(roc_auc_score(test['y_flood_true'], test[col])),
                        'average_precision': float(average_precision_score(test['y_flood_true'], test[col]))}
    basin_counts = [{'gauge_id': gid, 'positives': int(d['y_flood_true'].sum()),
                     'negatives': int((d['y_flood_true'] == 0).sum()),
                     'auroc_estimable': bool(d['y_flood_true'].nunique() == 2)} for gid, d in test.groupby('gauge_id')]
    events = pd.read_parquet(c / 'chunk02/data/events/flood_events.parquet')
    primary = events[events['source'] == 'primary']
    dates = pd.to_datetime(primary['event_date'], utc=True)
    crossing = pd.to_datetime(primary['crossing_timestamp'], utc=True)
    cal = json.loads((c / 'chunk05/calibration_params.json').read_text())['gauges']
    checkpoint = torch.load(c / 'chunk04/checkpoints/c_encoder_pretrained.pt', map_location='cpu', weights_only=True)
    state = checkpoint['model_state_dict']
    result = {
        'purpose': 'forensic artifact inspection; none of these metrics are admissible new research results',
        'nwm_formula_matches': nwm_checks, 'snow_formula_matches': snow_checks, 'source_quality': quality,
        'test_rows': len(test), 'test_positive_rows': int(test['y_flood_true'].sum()), 'test_basins': basin_counts,
        'recomputed_legacy_metrics': metrics,
        'prediction_spacing_days_counts': {str(k): int(v) for k, v in gaps.value_counts().items()},
        'primary_events': len(primary), 'primary_onsets_equal_peak_date_plus_noon': int((crossing == dates + pd.Timedelta(hours=12)).sum()),
        'calibration_window_counts': {s: [v['calibration_window_count'] for v in cal.values() if v['split_type'] == s] for s in ('train','val','test')},
        'checkpoint_parameter_count': sum(t.numel() for t in state.values()),
        'checkpoint_finite': all(bool(torch.isfinite(t).all()) for t in state.values()),
        'training_summary': json.loads((c / 'chunk04/pretraining_summary.json').read_text()),
        'environment': {'python': sys.version, 'platform': platform.platform(), 'architecture': platform.machine(),
                        'versions': {m: importlib.metadata.version(m) for m in ['numpy','pandas','pyarrow','torch','scikit-learn','scipy','pytest']}}
    }
    a.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'nwm_sites': len(nwm_checks), 'nwm_exact_sites': sum(v['max_error_to_legacy_usgs_formula'] == 0 for v in nwm_checks),
                      'snow_reproduced_sites': len(snow_checks), 'snow_exact_sites': sum(v['max_error_to_degree_day_formula'] == 0 for v in snow_checks),
                      'test_rows': len(test), 'test_positive_rows': int(test['y_flood_true'].sum()),
                      'test_basins_estimable': sum(v['auroc_estimable'] for v in basin_counts),
                      'primary_onsets_equal_peak_date_plus_noon': result['primary_onsets_equal_peak_date_plus_noon'],
                      'primary_events': len(primary), 'prediction_spacing': result['prediction_spacing_days_counts']}, indent=2))


if __name__ == '__main__': main()
