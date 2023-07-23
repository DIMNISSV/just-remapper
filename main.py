import json
import multiprocessing
from pathlib import Path

import PySimpleGUI as sg

from utils import convert, set_ffmpeg_params, JCException

HEADINGS = {'name': 'Название', 'files': 'Файл(ы)', 'stream_type': 'Тип дорожки',
            'number': 'Номер дорожки', 'language': 'Язык',
            'additional_params': 'Дополнительные аргументы'}
OUT_TOOLTIP = '''\
{i} - номер файла
{i+1} - номер файла + 1
{i_max} - количество файлов
{i_max+1} - количество файлов +1
{stem} - имя входного файла первой дорожки\
'''
FILE_TYPES = (('MP4', '*.mp4'),
              ('MKV', '*.mkv'),
              ('WEBP', '*.webp'),
              ('MOV', '*.mov'),
              ('AVI', '*.avi'),
              ('Другой', '*'))

sg.theme('DarkAmber')
tracks = []
main_layout = [
    [sg.Text('JustConverter'), sg.Button('Восстановить параметры', key='load_parameters')],
    *[[sg.Text(v), sg.InputText(key=k, expand_x=True), sg.FilesBrowse() if k == 'files' else []]
      for k, v in HEADINGS.items()],
    [sg.Button('Создать дорожку', key='create_track', expand_x=True),
     sg.Button('Обновить дорожку', key='update_track', expand_x=True, ),
     sg.Button('Удалить дорожки', key='delete_track', expand_x=True),
     sg.Button('Поднять дорожки', key='up_track', expand_x=True),
     sg.Button('Опустить дорожки', key='down_track', expand_x=True)],
    [sg.Table(tracks, list(HEADINGS.values()), key='tracks', expand_x=True, enable_events=True)],
    [sg.Checkbox('Заменить файл', key='replace'),
     sg.Checkbox('Копировать кодек', key='codec_copy', default=True),
     sg.Checkbox('Скрыть вывод в консоль', key='hide_logs')],
    [sg.Text('Параметры ffmpeg'), sg.InputText(key='ffmpeg_params', expand_x=True)],
    [sg.Text('Выходной файл или маска', tooltip=OUT_TOOLTIP),
     sg.InputText(key='output', expand_x=True), sg.FileSaveAs(file_types=FILE_TYPES)],
    [sg.Button('Начать конвертацию', key='convert', expand_x=True)]
]


def error_window(msg):
    error_layout = [[sg.Text(msg)],
                    [sg.Button('Закрыть', key='close', expand_x=True)]]
    window = sg.Window('JustConverter. Произошла ошибка', error_layout)
    while True:
        event, values = window.read()
        if not event or event == 'close':
            break
    window.close()


def convert_window(*args, **kwargs):
    convert_layout = [
        [sg.Text('Идёт конвертация...')],
        [sg.Button('Прервать', key='stop')]
    ]
    window = sg.Window('JustConverter | Конвертация', convert_layout)
    proc = multiprocessing.Process(target=convert, args=args, kwargs=kwargs)
    proc.start()
    while True:
        event, values = window.read(1000)
        if not event:
            break
        elif event == 'stop':
            proc.terminate()
            break
        elif event == '__TIMEOUT__':
            if not proc.is_alive():
                break
    window.close()


def main_window():
    global tracks
    parameters_path = Path('parameters.json')
    updating_track = False
    window = sg.Window('JustConverter', main_layout)
    while True:
        event, values = window.read()
        if not event:
            break
        elif event == 'load_parameters':
            if not parameters_path.exists():
                error_window('Параметры не сохранены!')
                continue
            try:
                with open(parameters_path) as f:
                    parameters = json.load(f)
            except json.JSONDecodeError as e:
                error_window(e)
                continue
            for k, v in parameters.items():
                window[k].update(v)
                if k == 'tracks':
                    tracks = v
        elif event == 'create_track':
            data = [values[k] for k in HEADINGS.keys()]
            if '' in data[1:-2]:
                error_window('Все поля обязательны к заполнению!')
                continue
            tracks.append(data)
            window['tracks'].update(tracks)
        elif event == 'delete_track':
            for i in values['tracks']:
                tracks.pop(i)
            window['tracks'].update(tracks)
        elif event == 'update_track':
            if not values['tracks']:
                error_window('Не выбрана ни одна дорожка!')
                continue
            for i, k in enumerate(HEADINGS.keys()):
                if updating_track:
                    tracks[values['tracks'][0]][i] = values[k]
                    window['tracks'].update(tracks)
                else:
                    window[k].update(tracks[values['tracks'][0]][i])
            updating_track = False if updating_track else True
        elif event in {'up_track', 'down_track'}:
            i = values['tracks'][0]
            to = -1 if event == 'up_track' else 1
            tracks.insert(i + to, tracks.pop(i))
            window['tracks'].update(tracks)
        elif event == 'convert':
            if not tracks:
                error_window('Нет ни одной дорожки!')
                continue
            try:
                with open(parameters_path, 'w') as f:
                    parameters = {k: values[k] for k in
                                  {'ffmpeg_params', 'output'}}
                    parameters['tracks'] = tracks
                    json.dump(parameters, f)
            except JCException as e:
                error_window(e)
                continue

            values['ffmpeg_params'] = set_ffmpeg_params(values)
            convert_window(
                tracks, HEADINGS,
                str(values['ffmpeg_params']),
                str(values['output']))
    window.close()


if __name__ == '__main__':
    main_window()
