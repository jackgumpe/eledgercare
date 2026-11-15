"""Bind each published reviewer dev result to the same author's rendered input, without rendering/OCR."""
import argparse
import json
import pathlib
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--author', required=True)
p.add_argument('--review', required=True)
p.add_argument('--review-path', required=True)
p.add_argument('--candidate', required=True)
p.add_argument('--output', required=True)
a = p.parse_args()

def read_json(revision, path):
    return json.loads(subprocess.check_output(['git', 'show', f'{revision}:{path}']))

author_path = 'evaluation/manifests/review-correction-verification.json'
author = read_json(a.author, author_path)
review = read_json(a.review, a.review_path)
author_rows = author['executed_dev_diagnostic']['dev_e2_diagnostic_results']
review_rows = review['C_input_contract_dev_controls']

def keyed(rows):
    result = {}
    for row in rows:
        key = row['fixture_page'].replace('.pdf#', '#')
        if key in result:
            raise ValueError(f'Duplicate fixture page: {key}')
        result[key] = row
    return result

aa, rr = keyed(author_rows), keyed(review_rows)
expected = {
    'SYN-WO-01-v1-raster300#p1', 'SYN-WO-01-v2-skew-pos4deg#p1',
    'SYN-WO-02-v1-raster300#p1', 'SYN-WO-02-v2-skew-neg3deg#p1',
    'SYN-INV-01-v1-raster300#p1', 'SYN-INV-01-v2-skew-neg3deg#p1',
    'SYN-MP-01-v1-raster300#p1', 'SYN-MP-01-v2-skew-pos4deg#p1',
}
fields = {
    'input_sha256': ('rendered_input_rgb_sha256', 'rendered_rgb_sha256'),
    'input_pixels': ('rendered_pdfium_300dpi_px', 'rendered_px'),
    'estimated_ccw_angle': ('theta_hat_ccw_deg', 'theta_hat'),
    'applied_ccw_angle': ('applied_ccw_deg', 'phi_applied'),
    'triggered': ('triggered', 'triggered'),
}
rows = []
for key in sorted(aa.keys() & rr.keys()):
    checks = {name: aa[key][left] == rr[key][right] for name, (left, right) in fields.items()}
    rows.append({'fixture_page': key, 'input_sha256': rr[key]['rendered_rgb_sha256'],
                 'input_pixels': rr[key]['rendered_px'], 'equal_fields': checks})
pins_match = author['revisions']['frozen_008_candidate_sha'] == review['pins']['candidate'] == a.candidate
passed = (aa.keys() == rr.keys() == expected and pins_match and review['all_pass']
          and not review['failures'] and all(all(row['equal_fields'].values()) for row in rows))
result = {
    'author_revision': a.author, 'author_path': author_path,
    'review_revision': a.review, 'review_path': a.review_path, 'candidate': a.candidate,
    'candidate_pins_match': pins_match, 'author_pages': sorted(aa), 'review_pages': sorted(rr),
    'expected_dev_pages': sorted(expected), 'per_fixture_comparison': rows,
    'all_eight_fixture_results_bound_and_equal': passed,
    'limits': 'Compares published evidence by exact fixture identifier. CPU execution remains attributed to its actual author/reviewer; no rendering, corpus regeneration or OCR is performed here.'
}
pathlib.Path(a.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'per_fixture_rows': len(rows), 'all_eight_fixture_results_bound_and_equal': passed}))
raise SystemExit(0 if passed else 1)
