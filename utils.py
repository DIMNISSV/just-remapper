from copy import deepcopy
from os import system
from pathlib import Path

ffmpeg = 'ffmpeg -hwaccel cuda'


class JCException(Exception):
    pass


def set_ffmpeg_params(values):
    ffmpeg_params = values['ffmpeg_params'] if values['ffmpeg_params'] and not values['codec_copy'] else '-c copy'
    ffmpeg_params += ' -y' if values['replace'] else ' -n'
    ffmpeg_params += ' -v error' if values['hide_logs'] else ''
    return ffmpeg_params


def q(s):
    return f'"{s}"' if ' ' in str(s) else str(s)


def get_paths(path, pattern=None):
    path = Path(path)
    try:
        if pattern:
            return path.glob(pattern)
        else:
            return path.parent.glob(path.name)
    except (ValueError, NotImplementedError) as e:
        raise JCException('Не удалось найти файлы по пути:\n'
                          f'{path / pattern}\n'
                          f'{e}')


def convert_file(tracks: list[dict], ffmpeg_params: str, output: Path):
    inputs = []
    maps = []
    metadata = ['-map_metadata -1']

    for i, track in enumerate(tracks):
        if track['additional_params']:
            inputs.append(track['additional_params'])
        inputs.append(f"-i {q(track['file'])}")
        maps.append(f"-map {i}:{track['stream_type']}:{track['number']}")
        metadata.append(f'-metadata:s:{i} title="{track["name"]}"')
        metadata.append(f'-metadata:s:{i} language={track["language"][:3]}')
    cmd = ' '.join([ffmpeg, *inputs, *maps, *metadata, ffmpeg_params, q(output)])
    print(cmd)
    system(cmd)


def convert_files(tracks: list[dict], ffmpeg_params: str, output: str):
    for file_i in range(len(tracks[0]['files'])):
        file_tracks = dict()
        for track in tracks:
            track['file'] = track['files'][file_i]
            file_tracks = track

        file_path = Path(file_tracks['file'])
        files_count = len(file_tracks['files'])
        file_output = Path(output.format_map({
            'i': file_i,
            'i+1': file_i + 1,
            'max_i': files_count,
            'max_i+1': files_count + 1,
            'stem': file_path.stem
        }))
        convert_file(tracks, ffmpeg_params, file_output)


def convert(tracks: list[list], headings: dict, ffmpeg_params: str, output: str):
    tracks: list = deepcopy(tracks)
    for i, track in enumerate(tracks):
        track = {k: track[j] for j, k in enumerate(headings.keys())}
        track['files'] = track['files'].split(';')
        tracks[i] = track
    convert_files(tracks, ffmpeg_params, output)
