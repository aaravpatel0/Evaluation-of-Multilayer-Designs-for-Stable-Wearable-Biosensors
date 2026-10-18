"""Package a completed study in verified, size-limited research archives.

All accepted-case input decks and numerical records are retained. Field arrays
are selected explicitly: the fine nominal filled Uniform assembly, all bare
skin controls, and initial/accepted fields for every corrected assembly case.
Raw correction DAT files support inspection of the field sums. Other assembly
fields remain reproducible from retained decks and source, but are not silently
claimed as bundled.
"""
import hashlib
import itertools
import json
from pathlib import Path
import zipfile

from model import ROOT, PROJECT

OUT = ROOT/'output'
MAX_PAYLOAD_BYTES = 1_800_000_000


def digest(stream):
    result = hashlib.sha256()
    while chunk := stream.read(1024*1024):
        result.update(chunk)
    return result.hexdigest()


def required(path):
    assert path.is_file(), f'Missing required research-package input: {path}'
    return path


def collect(summary):
    records = set()
    fields = set()
    for folder in [PROJECT, PROJECT/'detailed', ROOT]:
        for pattern in ['*.py', '*.md', '*.ps1', 'requirements*.txt']:
            records.update(folder.glob(pattern))
    records.add(required(PROJECT/'detailed/sources/biosensor_original.step'))
    records.add(required(PROJECT/'sources/Avestia_Template.docx'))
    records.update((ROOT/'sources').glob('*'))
    records.update(p for p in (ROOT/'verification').rglob('*') if p.is_file())
    configs = [(1.7, 'Supplied', d, .2, .1) for d in ['Uniform', 'Single', 'Graded']]
    configs += [(1.7, 'Filled', d, s, a) for d, s, a in itertools.product(
        ['Uniform', 'Single', 'Graded'], [.1, .2, .5], [.05, .1, .5])]
    targets = json.loads((OUT/'Refinement_Targets.json').read_text())
    configs += [(1.2, *target) for target in targets]
    assert 4*len(configs) == summary['accepted_assembly_solves']
    for h, geometry, design, skin, adhesive in configs:
        prefix = '' if geometry == 'Supplied' else 'Filled_'
        stem = f'WSL_h{h:g}_{prefix}{design}_S{skin:g}_A{adhesive:g}'
        for suffix in ['responses.json', 'responses.csv', 'diagnostics.json']:
            records.add(required(OUT/f'{stem}_{suffix}'))
        for mode in ['XX', 'YY', 'XY', 'Direct45']:
            directory = ROOT/'runs'/f'{stem}_{mode}'
            for name in ['job.inp', 'input_metadata.json', 'execution.json', 'checks.json', 'solver.log']:
                records.add(required(directory/name))
            for name in ['job.sta', 'job.cvg', 'initial_checks.json', 'residual_refinement_history.json']:
                if (directory/name).is_file():
                    records.add(directory/name)
            for correction in directory.glob('correction_*'):
                if correction.is_dir():
                    for name in ['job.inp', 'input_metadata.json', 'execution.json', 'solver.log']:
                        records.add(required(correction/name))
            if (directory/'residual_refinement_history.json').is_file():
                fields.add(required(directory/'initial_fields.npz'))
                fields.add(required(directory/'fields.npz'))
                for correction in directory.glob('correction_*'):
                    if correction.is_dir():
                        fields.add(required(correction/'job.dat'))
            for attempt in directory.glob('failed_memory_attempt_*'):
                records.update(p for p in attempt.rglob('*') if p.is_file())
            if h == 1.2 and geometry == 'Filled' and design == 'Uniform' and skin == .2 and adhesive == .1:
                fields.add(required(directory/'fields.npz'))
    for geometry in ['Supplied', 'Filled']:
        for h in [1.7, 1.2]:
            base = PROJECT/'detailed/meshes' if geometry == 'Supplied' else ROOT/'meshes/filled'
            fields.add(required(base/f'h{h:g}/mesh.npz'))
            fields.add(required(ROOT/'meshes'/f'bare_{geometry}_h{h:g}.npz'))
            for mode in ['XX', 'YY', 'XY']:
                directory = ROOT/'references'/f'{geometry}_h{h:g}_{mode}'
                fields.add(required(directory/'fields.npz'))
                for name in ['job.inp', 'input_metadata.json', 'execution.json', 'checks.json', 'solver.log']:
                    records.add(required(directory/name))
    for name in ['Final_Study_Summary.json', 'Tradeoff_Summary_Medium.json',
                 'All_Directional_Responses.csv', 'Refinement_Targets.json',
                 'Biosensor_Advanced_Proceeding.docx', 'Biosensor_Advanced_Proceeding.pdf',
                 'Manuscript_Statistics.json', 'Advanced_Manuscript_Text.txt']:
        records.add(required(OUT/name))
    records.update(p for p in (OUT/'figures').iterdir() if p.is_file())
    return dict(records=sorted(p for p in records if p.is_file()), selected_fields=sorted(fields))


def shards(paths):
    current, size = [], 0
    for path in paths:
        length = path.stat().st_size
        assert length < MAX_PAYLOAD_BYTES, f'Single file exceeds archive policy: {path}'
        if current and size+length > MAX_PAYLOAD_BYTES:
            yield current
            current, size = [], 0
        current.append(path)
        size += length
    if current:
        yield current


def main():
    import fitz
    summary = json.loads(required(OUT/'Final_Study_Summary.json').read_text())
    assert summary['material_configurations'] == 27 and summary['directional_responses'] == 972
    assert summary['maximum_free_DOF_force_residual'] < 1e-5
    with fitz.open(required(OUT/'Biosensor_Advanced_Proceeding.pdf')) as pdf:
        assert 6 <= len(pdf) <= 8
        assert 'Abstract' in pdf[0].get_text()
    groups = collect(summary)
    index = dict(scope='Completed computational mechanical study; original properties remain explicit surrogates',
                 selected_field_scope='Fine nominal Filled Uniform XX, YY, XY, Direct45; all12 matched bare-skin references; four full and four bare meshes; initial and accepted NPZ fields plus raw correction DAT for every corrected assembly case',
                 omitted_fields='Other assembly NPZ arrays and base DAT/FRD outputs are not included. All case decks and numerical records are retained for reruns.',
                 archives=[])
    for kind, paths in groups.items():
        for number, batch in enumerate(shards(paths), 1):
            manifest = {}
            for path in batch:
                with path.open('rb') as stream:
                    manifest[path.relative_to(PROJECT).as_posix()] = dict(bytes=path.stat().st_size, sha256=digest(stream))
            archive = OUT/f'Biosensor_Advanced_{kind}_{number:02d}.zip'
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=4) as package:
                for path in batch:
                    package.write(path, path.relative_to(PROJECT).as_posix(),
                                  compress_type=zipfile.ZIP_STORED if path.suffix == '.npz' else zipfile.ZIP_DEFLATED)
                package.writestr('ARCHIVE_MANIFEST.json', json.dumps(manifest, indent=2))
            assert archive.stat().st_size < 2_000_000_000
            with zipfile.ZipFile(archive) as package:
                assert set(package.namelist()) == set(manifest)|{'ARCHIVE_MANIFEST.json'}
                for name, evidence in manifest.items():
                    assert package.getinfo(name).file_size == evidence['bytes']
                    with package.open(name) as stream:
                        assert digest(stream) == evidence['sha256'], name
            with archive.open('rb') as stream:
                archive_hash = digest(stream)
            index['archives'].append(dict(name=archive.name, bytes=archive.stat().st_size,
                                          sha256=archive_hash, files=len(batch), kind=kind))
            print('VERIFIED ARCHIVE', archive.name, archive.stat().st_size, flush=True)
    (OUT/'Research_Package_Index.json').write_text(json.dumps(index, indent=2))


if __name__ == '__main__':
    main()
